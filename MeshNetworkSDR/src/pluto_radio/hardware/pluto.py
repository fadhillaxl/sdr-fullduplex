"""Pluto+ SDR hardware detection and device management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import time
from typing import Any, Optional
import numpy as np

from .iio import find_candidate_uris, get_troubleshooting_guide, is_ip_reachable, HAS_IIO

logger = logging.getLogger(__name__)

try:
    import adi
    HAS_ADI = True
except Exception as e:
    logger.debug("Failed to import adi: %s", e)
    adi = None  # type: ignore
    HAS_ADI = False


@dataclass
class PlutoDeviceInfo:
    status: str  # "CONNECTED", "NOT FOUND", "SIMULATION"
    uri: str
    model: str = "ADALM-PLUTO"
    tx_channels: str = "N/A"
    rx_channels: str = "N/A"
    sample_rate: str = "N/A"
    error_message: Optional[str] = None
    troubleshooting: Optional[str] = None

    def format_report(self) -> str:
        """Format detection report strictly according to Section 6 of the prompt."""
        lines = [
            "================================",
            "PLUTO SDR",
            "================================",
            f"Status       : {self.status}",
        ]
        if self.status in ("CONNECTED", "SIMULATION"):
            lines.extend([
                f"URI          : {self.uri}",
                f"Model        : {self.model}",
                f"TX channels  : {self.tx_channels}",
                f"RX channels  : {self.rx_channels}",
                f"Sample rate  : {self.sample_rate}",
            ])
        lines.append("================================")
        if self.error_message:
            lines.append("")
            lines.append(self.error_message)
        if self.troubleshooting:
            lines.append("")
            lines.append(self.troubleshooting)
        return "\n".join(lines)


class SimulatedPlutoDevice:
    """Software simulation mode for ADALM-Pluto / Pluto+."""

    def __init__(self, uri: str = "sim:pluto0", sample_rate: int = 2000000):
        self.uri = uri
        self._sample_rate = sample_rate
        self.rx_lo = 433000000
        self.tx_lo = 433000000
        self.rx_rf_bandwidth = 1000000
        self.tx_rf_bandwidth = 1000000
        self.tx_hardwaregain_chan0 = -20
        self.rx_hardwaregain_chan0 = 40
        self.gain_control_mode_chan0 = "manual"
        self.rx_buffer_size = 10000
        self.tx_cyclic_buffer = False
        self._tx_buffer: np.ndarray = np.array([], dtype=np.complex64)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        self._sample_rate = int(value)

    def tx(self, samples: np.ndarray) -> None:
        """Store transmitted samples for simulated loopback."""
        self._tx_buffer = np.asarray(samples, dtype=np.complex64)

    def tx_destroy_buffer(self) -> None:
        self._tx_buffer = np.array([], dtype=np.complex64)

    def rx(self) -> np.ndarray:
        """Return simulated received samples (realistic tone + AWGN noise)."""
        if len(self._tx_buffer) > 0:
            buffer_len = len(self._tx_buffer)
            noise = (np.random.randn(buffer_len) + 1j * np.random.randn(buffer_len)) * 1e-4
            return (self._tx_buffer + noise).astype(np.complex64)

        buffer_len = self.rx_buffer_size if getattr(self, "rx_buffer_size", 0) > 0 else 10000
        noise_sigma = 4.1
        noise = (np.random.randn(buffer_len) + 1j * np.random.randn(buffer_len)) * (noise_sigma / np.sqrt(2))
        signal_amp = 90.0
        t = np.arange(buffer_len) / self.sample_rate
        sim_tone = signal_amp * np.exp(1j * 2.0 * np.pi * 100_000.0 * t)
        return (sim_tone + noise).astype(np.complex64)


class PlutoTransceiver:
    """High-level transceiver controller for Pluto+ SDR hardware and simulation."""

    def __init__(
        self,
        uri: Optional[str] = None,
        simulation: bool = False,
        sample_rate: int = 1_000_000,
    ):
        self.simulation = simulation
        self.sample_rate = int(sample_rate)
        self.uri = uri
        self.sdr: Any = None
        self._is_tx_running: bool = False

        if simulation:
            self.sdr = SimulatedPlutoDevice(uri=uri or "sim:pluto0", sample_rate=sample_rate)
            self.uri = uri or "sim:pluto0"
        else:
            if not HAS_ADI:
                print("[WARNING] Pluto SDR not detected (pyadi-iio missing). Falling back to simulation mode.")
                self.simulation = True
                self.sdr = SimulatedPlutoDevice(uri="sim:pluto0", sample_rate=sample_rate)
                self.uri = "sim:pluto0"
                return

            target_uri = uri
            candidate_uris = find_candidate_uris(target_uri)
            connected = False
            for cand_uri in candidate_uris:
                is_explicit = bool(target_uri and (target_uri in cand_uri or cand_uri in target_uri))
                if cand_uri.startswith("ip:"):
                    host = cand_uri[3:]
                    if not is_explicit and not is_ip_reachable(host):
                        continue
                try:
                    self.sdr = adi.Pluto(uri=cand_uri)
                    self.uri = cand_uri
                    self.sdr.sample_rate = int(sample_rate)
                    if hasattr(self.sdr, "_rxadc") and hasattr(self.sdr._rxadc, "set_kernel_buffers_count"):
                        try:
                            self.sdr._rxadc.set_kernel_buffers_count(4)
                        except Exception:
                            pass
                    connected = True
                    break
                except Exception as e:
                    logger.debug("Failed probe on URI %s: %s", cand_uri, e)

            if not connected:
                print("[WARNING] Pluto SDR not detected. Falling back to simulation mode.")
                self.simulation = True
                self.sdr = SimulatedPlutoDevice(uri="sim:pluto0", sample_rate=sample_rate)
                self.uri = "sim:pluto0"

    def configure_tx(
        self,
        freq_hz: int = 433_000_000,
        gain_db: int = -20,
        rf_bandwidth: int = 1_000_000,
    ) -> None:
        """Configure transmitter carrier frequency, bandwidth, and gain."""
        self.sdr.tx_lo = int(freq_hz)
        self.sdr.tx_rf_bandwidth = int(rf_bandwidth)
        self.sdr.tx_hardwaregain_chan0 = int(gain_db)

    def configure_rx(
        self,
        freq_hz: int = 433_000_000,
        gain_db: Optional[int] = None,
        rf_bandwidth: int = 1_000_000,
    ) -> None:
        """Configure receiver carrier frequency, bandwidth, and gain."""
        self.sdr.rx_lo = int(freq_hz)
        self.sdr.rx_rf_bandwidth = int(rf_bandwidth)
        if gain_db is not None:
            self.sdr.gain_control_mode_chan0 = "manual"
            self.sdr.rx_hardwaregain_chan0 = int(gain_db)
        else:
            self.sdr.gain_control_mode_chan0 = "slow_attack"

    def transmit_iq(
        self,
        samples: np.ndarray,
        cyclic: bool = False,
        burst_duration: Optional[float] = None,
    ) -> None:
        """Transmit IQ samples over SDR with full DAC dynamic range scaling."""
        samples_c64 = np.asarray(samples, dtype=np.complex64)
        if not self.simulation and self.sdr is not None:
            # Pluto DAC requires integer int16 format. If input samples are normalized floats
            # (amplitude <= 2.0), scale by 16384 (2**14) so fractional values aren't truncated to zero.
            max_mag = float(np.max(np.abs(samples_c64))) if len(samples_c64) > 0 else 0.0
            if 0.0 < max_mag <= 2.0:
                samples_to_send = (samples_c64 * 16384.0).astype(np.complex64)
            else:
                samples_to_send = samples_c64

            # Always clean up any existing buffer before reconfiguring cyclic buffer mode
            if hasattr(self.sdr, "_txbuf") and self.sdr._txbuf is not None:
                try:
                    self.sdr.tx_destroy_buffer()
                except Exception:
                    pass

            if burst_duration is not None or not cyclic:
                # Transmit burst cyclically for controlled duration so receiver window reliably captures it,
                # then tear down buffer cleanly to prevent buffer leaks and DAC locking.
                duration = burst_duration if burst_duration is not None else 0.10
                self.sdr.tx_cyclic_buffer = True
                self.sdr.tx(samples_to_send)
                time.sleep(duration)
                try:
                    self.sdr.tx_destroy_buffer()
                except Exception:
                    pass
            else:
                self.sdr.tx_cyclic_buffer = True
                self.sdr.tx(samples_to_send)
                self._is_tx_running = True
        elif self.sdr is not None:
            self.sdr.tx(samples_c64)

    def start_tone_tx(
        self,
        tone_freq_hz: float = 100_000.0,
        amplitude: float = 0.8,
    ) -> None:
        """Transmit continuous cyclic complex tone."""
        from ..dsp.rf_metrics import generate_complex_tone
        num_samples = 10_000
        iq_tone = generate_complex_tone(
            tone_freq_hz=tone_freq_hz,
            sample_rate=float(self.sample_rate),
            num_samples=num_samples,
            amplitude=amplitude,
        )
        self.transmit_iq(iq_tone, cyclic=True)
        self._is_tx_running = True

    def stop_tx(self) -> None:
        """Stop active transmission and release TX buffer."""
        if not self._is_tx_running:
            return
        if self.simulation:
            self.sdr.tx_destroy_buffer()
        else:
            try:
                self.sdr.tx_destroy_buffer()
            except Exception:
                pass
        self._is_tx_running = False

    def receive_iq(self, buffer_size: int = 10_000) -> np.ndarray:
        """Fetch a buffer of complex IQ samples."""
        target_size = int(buffer_size)
        if getattr(self.sdr, "rx_buffer_size", None) != target_size:
            self.sdr.rx_buffer_size = target_size
        return self.sdr.rx()



class PlutoDetector:
    """Detects and inspects connected ADALM-Pluto / Pluto+ SDR devices."""

    def __init__(self, default_uri: Optional[str] = None):
        self.default_uri = default_uri

    def detect(self, uri: Optional[str] = None, simulation: bool = False) -> PlutoDeviceInfo:
        """Probe for Pluto SDR hardware or return simulation info."""
        if simulation:
            return PlutoDeviceInfo(
                status="SIMULATION",
                uri="sim:pluto0",
                model="ADALM-PLUTO (Simulated)",
                tx_channels="OK",
                rx_channels="OK",
                sample_rate="2000000 MSPS",
            )

        if not HAS_ADI:
            return PlutoDeviceInfo(
                status="NOT FOUND",
                uri="N/A",
                error_message="pyadi-iio library is not available.",
                troubleshooting=get_troubleshooting_guide(),
            )

        target_uri = uri or self.default_uri
        candidate_uris = find_candidate_uris(target_uri)
        last_error: Optional[str] = None

        for cand_uri in candidate_uris:
            is_explicit = bool(target_uri and (target_uri in cand_uri or cand_uri in target_uri))
            if cand_uri.startswith("ip:"):
                host = cand_uri[3:]
                # Check if reachable first to avoid 15s kernel TCP timeout on fallback scans
                if not is_explicit and not is_ip_reachable(host):
                    last_error = f"Network host '{host}' unreachable"
                    continue

            try:
                sdr = adi.Pluto(uri=cand_uri)
                sample_rate_val = getattr(sdr, "sample_rate", "2000000")
                # Format nicely
                try:
                    sr_num = int(sample_rate_val)
                    sr_str = f"{sr_num:,} SPS ({sr_num/1e6:.2f} MSPS)"
                except Exception:
                    sr_str = str(sample_rate_val)

                return PlutoDeviceInfo(
                    status="CONNECTED",
                    uri=cand_uri,
                    model="ADALM-PLUTO",
                    tx_channels="OK",
                    rx_channels="OK",
                    sample_rate=sr_str,
                )
            except Exception as e:
                last_error = str(e)
                logger.debug("Failed probe on URI %s: %s", cand_uri, e)

        return PlutoDeviceInfo(
            status="NOT FOUND",
            uri="N/A",
            error_message=f"Details: {last_error}" if last_error else None,
            troubleshooting=get_troubleshooting_guide(),
        )
