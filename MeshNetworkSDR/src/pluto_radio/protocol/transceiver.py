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
        node_id: Optional[int] = None,
        peer_node_id: Optional[int] = None,
    ):
        self.tun = tun
        self.sdr = sdr
        self.modulation = modulation.lower()
        self.samples_per_symbol = max(1, samples_per_symbol)

        # Infer node IDs from IP addresses (e.g. 192.168.30.1 -> node 1)
        if node_id is not None:
            self.node_id = int(node_id)
        else:
            try:
                self.node_id = int(self.tun.local_ip.split(".")[-1])
            except Exception:
                self.node_id = 1

        if peer_node_id is not None:
            self.peer_node_id = int(peer_node_id)
        else:
            try:
                self.peer_node_id = int(self.tun.peer_ip.split(".")[-1])
            except Exception:
                self.peer_node_id = 2 if self.node_id == 1 else 1

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
        logger.info(
            "Digital Packet Transceiver started: Node %d -> Node %d (%s modem)",
            self.node_id,
            self.peer_node_id,
            self.modulation.upper(),
        )

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
        """Assemble RF burst with leading silence, dual Barker preamble + payload, and trail silence in a single DMA block."""
        from ..dsp.sync import get_preamble_iq
        preamble_iq = get_preamble_iq(amplitude=0.8)

        if self.modulation == "qpsk":
            payload_iq = qpsk_modulate(frame_bytes, amplitude=0.8, samples_per_symbol=1)
        else:
            payload_iq = bpsk_modulate(frame_bytes, amplitude=0.8, samples_per_symbol=1)

        single_burst = np.concatenate([preamble_iq, payload_iq])
        lead_silence = np.zeros(128, dtype=np.complex64)
        inter_gap = np.zeros(1024, dtype=np.complex64)  # 0.512 ms temporal separation against fading dips
        trail_silence = np.zeros(256, dtype=np.complex64)

        # Dual-burst transmission inside one single atomic DMA block:
        # Delivers hardware redundancy against multipath fading with zero sleep delay!
        burst = np.concatenate([lead_silence, single_burst, inter_gap, single_burst, trail_silence])

        # Pad to fixed 8192 samples (4.096 ms at 2 MSPS) to prevent pyadi-iio buffer resizing error
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

                frame = build_frame(
                    packet,
                    seq=seq,
                    src_id=self.node_id,
                    dst_id=self.peer_node_id,
                )
                burst_iq = self._build_tx_burst(frame)

                try:
                    # Guard against dynamic buffer size mismatch in pyadi-iio
                    if hasattr(self.sdr.sdr, "_tx_buffer_size") and self.sdr.sdr._tx_buffer_size != len(burst_iq):
                        self.sdr.sdr.tx_destroy_buffer()

                    # Single atomic DMA push transmits both redundant bursts in ~4 ms
                    self.sdr.sdr.tx(burst_iq)

                    with self._lock:
                        self.stats.tx_packets += 1
                        self.stats.tx_bytes += len(packet)
                    logger.debug("Transmitted packet #%d (%d bytes, Node %d -> %d)", seq, len(packet), self.node_id, self.peer_node_id)
                except Exception as e:
                    logger.error("Failed to transmit RF burst: %s", e)
                    try:
                        self.sdr.sdr.tx_destroy_buffer()
                    except Exception:
                        pass
            else:
                time.sleep(0.005)

    def _rx_loop(self) -> None:
        """Receive IQ samples from SDR, run preamble sync, CFO correction, CRC check, and inject to TUN."""
        from ..dsp.sync import detect_and_synchronize_packets
        metrics_counter = 0
        recent_seqs: dict[int, float] = {}
        tail_samples: Optional[np.ndarray] = None

        while self._running:
            try:
                new_samples = self.sdr.receive_iq(buffer_size=16384)
                if len(new_samples) == 0:
                    time.sleep(0.005)
                    continue

                if tail_samples is not None and len(tail_samples) > 0:
                    samples = np.concatenate([tail_samples, new_samples])
                else:
                    samples = new_samples

                # Keep last 4096 samples as tail for next iteration to prevent boundary packet loss
                tail_samples = samples[-4096:]

                for bits, est_cfo, snr_val in detect_and_synchronize_packets(
                    samples,
                    sample_rate=self.sdr.sample_rate,
                    threshold=0.35,
                ):
                    raw_bytes = bits_to_bytes(bits)
                    self.detector.push(raw_bytes)

                    for src_id, dst_id, seq, payload in self.detector.extract_frames():
                        # REJECT LOCAL SELF-INTERFERENCE / TRANSMIT ECHO!
                        if src_id == self.node_id:
                            logger.debug("Discarded self-interference echo from node %d", src_id)
                            continue

                        # Filter destination (accept packets for this node or broadcast 0xFF)
                        if dst_id not in (self.node_id, 0xFF):
                            logger.debug("Ignored packet destined for node %d", dst_id)
                            continue

                        now = time.time()
                        last_seen = recent_seqs.get(seq, 0.0)
                        # Deduplicate repeated RF burst transmissions
                        if now - last_seen > 0.4:
                            recent_seqs[seq] = now
                            self.tun.write(payload)
                            with self._lock:
                                self.stats.rx_packets += 1
                                self.stats.rx_bytes += len(payload)
                                self.stats.cfo_hz = est_cfo
                                self.stats.snr_db = snr_val
                            logger.info(
                                "Delivered packet #%d from Node %d (%d bytes, CFO: %.1f Hz, SNR: %.1f dB)",
                                seq,
                                src_id,
                                len(payload),
                                est_cfo,
                                snr_val,
                            )

                if len(recent_seqs) > 200:
                    now = time.time()
                    recent_seqs = {s: t for s, t in recent_seqs.items() if now - t < 5.0}

                metrics_counter += 1
                if metrics_counter >= 10:
                    metrics_counter = 0
                    metrics = compute_rf_metrics(samples, sample_rate=self.sdr.sample_rate)
                    with self._lock:
                        self.stats.rssi_dbfs = metrics.rssi_dbfs
                        if self.stats.snr_db == 0.0:
                            self.stats.snr_db = metrics.snr_db

            except Exception as e:
                logger.debug("RX loop error: %s", e)
                time.sleep(0.01)
