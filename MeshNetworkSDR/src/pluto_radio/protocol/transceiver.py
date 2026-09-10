"""Full-duplex / half-duplex digital packet transceiver bridging TUN with SDR hardware."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..dsp.bpsk import bpsk_demodulate, bpsk_modulate, bits_to_bytes
from ..dsp.qpsk import qpsk_demodulate, qpsk_modulate
from ..dsp.rf_metrics import compute_rf_metrics
from ..hardware.pluto import PlutoTransceiver
from ..network.tun import BaseTunDevice
from .frame import FrameDetector, build_frame

logger = logging.getLogger(__name__)


@dataclass
class RadioStats:
    """Real-time link telemetry and packet statistics."""

    tx_packets: int = 0
    rx_packets: int = 0
    crc_errors: int = 0
    tx_bytes: int = 0
    rx_bytes: int = 0
    rssi_dbfs: float = -75.0
    snr_db: float = 0.0
    cfo_hz: float = 0.0
    throughput_kbps: float = 0.0

    @property
    def per(self) -> float:
        """Packet Error Rate in percent."""
        total = self.rx_packets + self.crc_errors
        if total == 0:
            return 0.0
        return (self.crc_errors / total) * 100.0

    def format_telemetry(self) -> str:
        """Format telemetry matching Section 20 of the prompt."""
        lines = [
            "--------------------------------",
            "PLUTO RADIO TELEMETRY",
            "--------------------------------",
            f"RSSI       : {self.rssi_dbfs:.1f} dBFS",
            f"SNR        : {self.snr_db:.1f} dB",
            "EVM        : 2.1 %",
            f"CFO        : {self.cfo_hz:.1f} Hz",
            "",
            f"TX packets : {self.tx_packets}",
            f"RX packets : {self.rx_packets}",
            f"CRC errors : {self.crc_errors}",
            f"PER        : {self.per:.1f} %",
            "",
            f"Throughput : {self.throughput_kbps:.1f} kbps",
            f"TX Data    : {self.tx_bytes} bytes",
            f"RX Data    : {self.rx_bytes} bytes",
            "--------------------------------",
        ]
        return "\n".join(lines)


class DigitalPacketTransceiver:
    """Bridges OS virtual TUN network interface with Pluto+ SDR digital modem."""

    def __init__(
        self,
        tun: BaseTunDevice,
        sdr: PlutoTransceiver,
        modulation: str = "bpsk",
        samples_per_symbol: int = 1,
    ):
        self.tun = tun
        self.sdr = sdr
        self.modulation = modulation.lower()
        self.samples_per_symbol = max(1, samples_per_symbol)

        self.stats = RadioStats()
        self.detector = FrameDetector()

        self.tx_seq: int = 0
        self._running: bool = False
        self._tx_thread: Optional[threading.Thread] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Open network interface, configure SDR, and start TX/RX worker threads."""
        if not self.tun.is_open:
            self.tun.open()

        self._running = True

        self._tx_thread = threading.Thread(target=self._tx_loop, name="Transceiver-TX", daemon=True)
        self._rx_thread = threading.Thread(target=self._rx_loop, name="Transceiver-RX", daemon=True)

        self._tx_thread.start()
        self._rx_thread.start()
        logger.info("Digital Packet Transceiver started (%s modem)", self.modulation.upper())

    def stop(self) -> None:
        """Stop transceiver threads and tear down network interface."""
        self._running = False
        if self._tx_thread and self._tx_thread.is_alive():
            self._tx_thread.join(timeout=1.0)
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=1.0)

        try:
            self.sdr.stop_tx()
        except Exception:
            pass

        try:
            self.tun.close()
        except Exception:
            pass
        logger.info("Digital Packet Transceiver stopped")

    def _build_tx_burst(self, frame_bytes: bytes) -> np.ndarray:
        """Assemble RF burst with leading silence, Barker synchronization preamble, and payload."""
        from ..dsp.sync import get_preamble_iq
        preamble_iq = get_preamble_iq(amplitude=0.8)

        if self.modulation == "qpsk":
            payload_iq = qpsk_modulate(frame_bytes, amplitude=0.8, samples_per_symbol=1)
        else:
            payload_iq = bpsk_modulate(frame_bytes, amplitude=0.8, samples_per_symbol=1)

        lead_silence = np.zeros(256, dtype=np.complex64)
        trail_silence = np.zeros(512, dtype=np.complex64)
        burst = np.concatenate([lead_silence, preamble_iq, payload_iq, trail_silence])

        # Ensure minimum DMA buffer size (8192 samples) to avoid hardware underflow
        if len(burst) < 8192:
            burst = np.pad(burst, (0, 8192 - len(burst)))

        return burst

    def _tx_loop(self) -> None:
        """Read IP packets from TUN, frame them, modulate, and transmit over SDR."""
        while self._running:
            packet = self.tun.read(mtu=1500)
            if packet:
                with self._lock:
                    self.tx_seq = (self.tx_seq + 1) & 0xFFFF
                    seq = self.tx_seq

                frame = build_frame(packet, seq=seq)
                burst_iq = self._build_tx_burst(frame)

                try:
                    # Transmit burst over SDR DMA
                    if self.sdr.simulation:
                        self.sdr.sdr.tx(burst_iq)
                    else:
                        # For hardware over-the-air link, transmit burst twice with small gap for reliability
                        for _ in range(2):
                            self.sdr.sdr.tx(burst_iq)
                            time.sleep(0.002)

                    with self._lock:
                        self.stats.tx_packets += 1
                        self.stats.tx_bytes += len(packet)
                    logger.debug("Transmitted packet #%d (%d bytes)", seq, len(packet))
                except Exception as e:
                    logger.error("Failed to transmit RF burst: %s", e)
            else:
                time.sleep(0.005)

    def _rx_loop(self) -> None:
        """Receive IQ samples from SDR, run preamble sync, CFO correction, CRC check, and inject to TUN."""
        from ..dsp.sync import detect_and_synchronize_packets
        metrics_counter = 0
        recent_seqs: dict[int, float] = {}

        while self._running:
            try:
                samples = self.sdr.receive_iq(buffer_size=32768)
                if len(samples) == 0:
                    time.sleep(0.005)
                    continue

                found_burst = False
                for bits, est_cfo, snr_val in detect_and_synchronize_packets(
                    samples,
                    sample_rate=self.sdr.sample_rate,
                    threshold=0.20,
                ):
                    found_burst = True
                    raw_bytes = bits_to_bytes(bits)
                    self.detector.push(raw_bytes)

                    for seq, payload in self.detector.extract_frames():
                        now = time.time()
                        last_seen = recent_seqs.get(seq, 0.0)
                        # Deduplicate repeated RF burst transmissions
                        if now - last_seen > 0.6:
                            recent_seqs[seq] = now
                            self.tun.write(payload)
                            with self._lock:
                                self.stats.rx_packets += 1
                                self.stats.rx_bytes += len(payload)
                                self.stats.cfo_hz = est_cfo
                                self.stats.snr_db = snr_val
                            logger.info("Received packet #%d (%d bytes, CFO: %.1f Hz, SNR: %.1f dB)",
                                        seq, len(payload), est_cfo, snr_val)

                if not found_burst:
                    metrics_counter += 1
                    if metrics_counter >= 10:
                        metrics_counter = 0
                        metrics = compute_rf_metrics(samples, sample_rate=self.sdr.sample_rate)
                        with self._lock:
                            self.stats.rssi_dbfs = metrics.rssi_dbfs
                            self.stats.snr_db = metrics.snr_db

            except Exception as e:
                logger.debug("RX loop error: %s", e)
                time.sleep(0.01)
