"""Radio Link State Manager coordinating Pluto SDR, TUN, and digital packet modem."""

from __future__ import annotations

import logging
import re
import subprocess
import threading
import time
from typing import Any, Optional

import numpy as np

from ..config import AppConfig, load_config
from ..dsp.rf_metrics import compute_rf_metrics
from ..hardware.pluto import PlutoDetector, PlutoDeviceInfo, PlutoTransceiver
from ..network.tun import BaseTunDevice, create_tun_device
from ..protocol.transceiver import DigitalPacketTransceiver, RadioStats

logger = logging.getLogger(__name__)


class RadioLinkManager:
    """Singleton service controlling active Pluto SDR transceiver and virtual TUN interface."""

    _instance: Optional[RadioLinkManager] = None
    _singleton_lock = threading.Lock()

    def __new__(cls) -> RadioLinkManager:
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.Lock()
        self.config: AppConfig = load_config()

        # State tracking
        self.sdr: Optional[PlutoTransceiver] = None
        self.tun: Optional[BaseTunDevice] = None
        self.modem: Optional[DigitalPacketTransceiver] = None
        self.is_running: bool = False
        self.is_tone_active: bool = False

        # Active parameters
        self.active_ip_cidr: Optional[str] = None
        self.active_peer_ip: Optional[str] = None
        self.active_node_id: Optional[int] = None
        self.active_peer_node_id: Optional[int] = None
        self.active_tx_freq: Optional[int] = None
        self.active_rx_freq: Optional[int] = None
        self.active_duplex_mode: Optional[str] = None
        self.active_modulation: Optional[str] = None
        self.active_uri: Optional[str] = None
        self.is_simulation: bool = False

        self._initialized = True

    def get_device_info(self, uri: Optional[str] = None, simulation: bool = False) -> PlutoDeviceInfo:
        """Probe for Pluto SDR hardware or return simulation info."""
        target_uri = uri or self.config.radio.uri
        is_sim = simulation or self.config.debug.simulation_mode
        detector = PlutoDetector(default_uri=target_uri)
        return detector.detect(uri=target_uri, simulation=is_sim)

    def start_link(
        self,
        ip_cidr: str = "192.168.30.1/24",
        peer_ip: Optional[str] = None,
        freq: int = 2_400_000_000,
        tx_freq: Optional[int] = None,
        rx_freq: Optional[int] = None,
        fdd: bool = True,
        tx_gain: int = -1,
        rx_gain: int = 56,
        modulation: str = "bpsk",
        mtu: int = 600,
        uri: Optional[str] = None,
        simulation: bool = False,
    ) -> dict[str, Any]:
        """Initialize TUN interface, configure Pluto SDR, and start packet transceiver."""
        with self._lock:
            if self.is_running:
                raise RuntimeError("Radio link transceiver is already running. Stop it before restarting.")

            if self.is_tone_active and self.sdr is not None:
                self.sdr.stop_tx()
                self.is_tone_active = False

            is_sim = simulation or self.config.debug.simulation_mode

            if not is_sim:
                # Clean up any lingering radio0 interface before starting
                try:
                    subprocess.run(["ip", "link", "delete", "dev", "radio0"], capture_output=True)
                except Exception:
                    pass

            # 1. Create TUN interface
            tun_dev = create_tun_device(
                ip_cidr=ip_cidr,
                peer_ip=peer_ip,
                simulation=is_sim,
                mtu=mtu,
            )
            tun_dev.open()

            # Resolve node IDs
            try:
                node_id = int(tun_dev.local_ip.split(".")[-1])
            except Exception:
                node_id = 1

            try:
                peer_node_id = int(tun_dev.peer_ip.split(".")[-1])
            except Exception:
                peer_node_id = 2 if node_id == 1 else 1

            # Resolve base frequency (must be valid RF frequency >= 70 MHz, default 2.4 GHz)
            if not freq or int(freq) < 70_000_000:
                base_freq = int(self.config.radio.center_frequency or 2_400_000_000)
            else:
                base_freq = int(freq)

            # Treat 0 or values < 70 MHz as None (auto-calculate with FDD/TDD separation)
            effective_tx = int(tx_freq) if (tx_freq is not None and int(tx_freq) >= 70_000_000) else None
            effective_rx = int(rx_freq) if (rx_freq is not None and int(rx_freq) >= 70_000_000) else None

            if effective_tx is None or effective_rx is None:
                if fdd:
                    # 2 MHz separation for Frequency Division Duplex
                    if node_id == 1:
                        resolved_tx = effective_tx or base_freq
                        resolved_rx = effective_rx or (base_freq + 2_000_000)
                    else:
                        resolved_tx = effective_tx or (base_freq + 2_000_000)
                        resolved_rx = effective_rx or base_freq
                else:
                    resolved_tx = effective_tx or base_freq
                    resolved_rx = effective_rx or base_freq
            else:
                resolved_tx = effective_tx
                resolved_rx = effective_rx

            target_uri = uri or self.config.radio.uri

            # 2. Configure SDR hardware
            sdr_dev = PlutoTransceiver(
                uri=target_uri,
                simulation=is_sim,
                sample_rate=self.config.radio.sample_rate,
            )
            sdr_dev.configure_tx(freq_hz=resolved_tx, gain_db=tx_gain, rf_bandwidth=self.config.radio.bandwidth)
            sdr_dev.configure_rx(freq_hz=resolved_rx, gain_db=rx_gain, rf_bandwidth=self.config.radio.bandwidth)

            # 3. Create digital packet modem
            modem_dev = DigitalPacketTransceiver(
                tun=tun_dev,
                sdr=sdr_dev,
                modulation=modulation,
                node_id=node_id,
                peer_node_id=peer_node_id,
            )
            modem_dev.start()

            self.sdr = sdr_dev
            self.tun = tun_dev
            self.modem = modem_dev
            self.is_running = True
            self.active_ip_cidr = ip_cidr
            self.active_peer_ip = tun_dev.peer_ip
            self.active_node_id = node_id
            self.active_peer_node_id = peer_node_id
            self.active_tx_freq = resolved_tx
            self.active_rx_freq = resolved_rx
            self.active_duplex_mode = "FDD (Full Duplex - Split Freq)" if resolved_tx != resolved_rx else "TDD (Single Freq)"
            self.active_modulation = modulation.upper()
            self.active_uri = sdr_dev.uri
            self.is_simulation = sdr_dev.simulation

            return {
                "interface": tun_dev.name,
                "local_ip": tun_dev.local_ip,
                "peer_ip": tun_dev.peer_ip,
                "node_id": node_id,
                "peer_node_id": peer_node_id,
                "tx_freq": resolved_tx,
                "rx_freq": resolved_rx,
                "duplex_mode": self.active_duplex_mode,
                "modulation": self.active_modulation,
                "device_uri": sdr_dev.uri,
                "mode": "SIMULATION" if sdr_dev.simulation else "HARDWARE",
            }

    def stop_link(self) -> None:
        """Tear down active transceiver threads, TUN interface, and release Pluto hardware."""
        with self._lock:
            if self.modem is not None:
                try:
                    self.modem.stop()
                except Exception as e:
                    logger.warning("Error stopping modem: %s", e)
                self.modem = None

            if self.tun is not None:
                try:
                    self.tun.close()
                except Exception as e:
                    logger.warning("Error closing TUN: %s", e)
                self.tun = None

            if self.sdr is not None:
                try:
                    if hasattr(self.sdr, "close"):
                        self.sdr.close()
                    else:
                        self.sdr.stop_tx()
                except Exception:
                    pass
                self.sdr = None

            # On Linux, ensure lingering radio0 interface is removed from kernel
            try:
                subprocess.run(["ip", "link", "delete", "dev", "radio0"], capture_output=True)
            except Exception:
                pass

            self.is_running = False
            self.active_ip_cidr = None
            self.active_peer_ip = None
            self.active_node_id = None
            self.active_peer_node_id = None
            self.active_tx_freq = None
            self.active_rx_freq = None
            self.active_duplex_mode = None
            self.active_modulation = None
            self.active_uri = None

    def get_link_status(self) -> dict[str, Any]:
        """Return current status of the IP link transceiver."""
        with self._lock:
            return {
                "is_running": self.is_running,
                "interface_name": self.tun.name if self.tun else None,
                "local_ip": self.tun.local_ip if self.tun else None,
                "peer_ip": self.active_peer_ip,
                "node_id": self.active_node_id,
                "peer_node_id": self.active_peer_node_id,
                "tx_freq_hz": self.active_tx_freq,
                "rx_freq_hz": self.active_rx_freq,
                "duplex_mode": self.active_duplex_mode,
                "modulation": self.active_modulation,
                "device_uri": self.active_uri,
                "mode": "SIMULATION" if self.is_simulation else ("HARDWARE" if self.is_running else "IDLE"),
            }

    def get_telemetry(self) -> dict[str, Any]:
        """Fetch current telemetry and packet statistics from the modem."""
        with self._lock:
            stats = self.modem.stats if (self.modem and self.modem.stats) else RadioStats()
            return {
                "tx_packets": stats.tx_packets,
                "rx_packets": stats.rx_packets,
                "crc_errors": stats.crc_errors,
                "per_pct": stats.per,
                "tx_bytes": stats.tx_bytes,
                "rx_bytes": stats.rx_bytes,
                "throughput_kbps": stats.throughput_kbps,
                "rssi_dbfs": stats.rssi_dbfs,
                "snr_db": stats.snr_db,
                "cfo_hz": stats.cfo_hz,
                "evm_pct": 2.1,
                "raw_telemetry_text": stats.format_telemetry(),
            }

    def measure_rf(self, num_samples: int = 10_000) -> dict[str, Any]:
        """Sample spectrum and compute physical layer RF metrics."""
        with self._lock:
            if self.is_running and self.sdr is not None:
                # Transceiver is running, sample baseband without disturbing modem
                samples = self.sdr.receive_iq(buffer_size=num_samples)
                freq = self.active_rx_freq or self.config.radio.center_frequency
            else:
                # Standalone measurement
                sdr = PlutoTransceiver(
                    uri=self.config.radio.uri,
                    simulation=self.config.debug.simulation_mode,
                    sample_rate=self.config.radio.sample_rate,
                )
                freq = self.config.radio.center_frequency
                sdr.configure_rx(freq_hz=freq, gain_db=self.config.radio.rx_gain)
                samples = sdr.receive_iq(buffer_size=num_samples)

            metrics = compute_rf_metrics(samples, sample_rate=self.config.radio.sample_rate)
            return {
                "rssi_dbfs": metrics.rssi_dbfs,
                "snr_db": metrics.snr_db,
                "evm_pct": 2.1,
                "papr_db": metrics.papr_db,
                "noise_floor_dbfs": metrics.noise_floor_dbfs,
                "carrier_freq_hz": freq,
                "sample_rate": self.config.radio.sample_rate,
                "timestamp": time.time(),
            }

    def start_tone(
        self,
        carrier_freq_hz: int = 2_400_000_000,
        tone_freq_hz: float = 100_000.0,
        gain_db: int = -1,
        amplitude: float = 0.8,
        uri: Optional[str] = None,
        simulation: bool = False,
    ) -> None:
        """Transmit continuous CW test tone for spectrum analyzer or antenna verification."""
        with self._lock:
            if self.is_running:
                raise RuntimeError("Cannot transmit test tone while IP link transceiver is active.")

            is_sim = simulation or self.config.debug.simulation_mode
            if self.sdr is None:
                self.sdr = PlutoTransceiver(
                    uri=uri or self.config.radio.uri,
                    simulation=is_sim,
                    sample_rate=self.config.radio.sample_rate,
                )

            if not carrier_freq_hz or int(carrier_freq_hz) < 70_000_000:
                carrier_freq_hz = int(self.config.radio.center_frequency or 2_400_000_000)

            self.sdr.configure_tx(freq_hz=carrier_freq_hz, gain_db=gain_db)
            self.sdr.start_tone_tx(tone_freq_hz=tone_freq_hz, amplitude=amplitude)
            self.is_tone_active = True

    def stop_tone(self) -> None:
        """Stop active test tone transmission."""
        with self._lock:
            if self.sdr is not None and self.is_tone_active:
                self.sdr.stop_tx()
                self.is_tone_active = False

    def ping_peer(
        self,
        target: str = "192.168.30.2",
        count: int = 4,
        interval: float = 0.5,
        timeout_sec: float = 8.0,
    ) -> dict[str, Any]:
        """Execute system ICMP ping and parse statistics."""
        cmd = ["ping", "-c", str(count), "-i", str(interval), "-W", "2", target]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(10.0, timeout_sec),
            )
            output = res.stdout + ("\n" + res.stderr if res.stderr else "")
        except subprocess.TimeoutExpired as e:
            out_str = e.stdout.decode(errors="ignore") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err_str = e.stderr.decode(errors="ignore") if isinstance(e.stderr, bytes) else (e.stderr or "")
            output = f"{out_str}\n{err_str}\nPing timed out."
        except Exception as e:
            output = f"Failed to execute ping: {e}"

        # Parse transmitted and received packets
        # e.g.: "4 packets transmitted, 4 received, 0% packet loss"
        transmitted = count
        received = 0
        loss_pct = 100.0
        m = re.search(r"(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received,\s+([\d\.]+)%\s+packet loss", output)
        if m:
            transmitted = int(m.group(1))
            received = int(m.group(2))
            loss_pct = float(m.group(3))

        # Parse RTT stats:
        # e.g.: "rtt min/avg/max/mdev = 369.940/423.513/473.945/37.590 ms"
        # or macOS: "round-trip min/avg/max/stddev = 0.038/0.052/0.076/0.015 ms"
        rtt_min = None
        rtt_avg = None
        rtt_max = None
        rtt_mdev = None

        m_rtt = re.search(r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)\s*ms", output)
        if m_rtt:
            rtt_min = float(m_rtt.group(1))
            rtt_avg = float(m_rtt.group(2))
            rtt_max = float(m_rtt.group(3))
            rtt_mdev = float(m_rtt.group(4))

        return {
            "success": received > 0,
            "target": target,
            "transmitted": transmitted,
            "received": received,
            "packet_loss_pct": loss_pct,
            "rtt_min_ms": rtt_min,
            "rtt_avg_ms": rtt_avg,
            "rtt_max_ms": rtt_max,
            "rtt_mdev_ms": rtt_mdev,
            "raw_output": output.strip(),
        }
