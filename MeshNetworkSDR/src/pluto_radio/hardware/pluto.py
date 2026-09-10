"""Pluto+ SDR hardware detection and device management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np

from .iio import find_candidate_uris, get_troubleshooting_guide, is_ip_reachable, HAS_IIO

logger = logging.getLogger(__name__)

try:
    import adi
    HAS_ADI = True
except ImportError:
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
        self.gain_control_mode_chan0 = "slow_attack"
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

    def rx(self) -> np.ndarray:
        """Return simulated received samples (or AWGN noise if buffer empty)."""
        buffer_len = len(self._tx_buffer) if len(self._tx_buffer) > 0 else 1024
        noise = (np.random.randn(buffer_len) + 1j * np.random.randn(buffer_len)) * 1e-4
        if len(self._tx_buffer) > 0:
            return self._tx_buffer + noise.astype(np.complex64)
        return noise.astype(np.complex64)


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

        candidate_uris = find_candidate_uris(uri or self.default_uri)
        last_error: Optional[str] = None

        for cand_uri in candidate_uris:
            if cand_uri.startswith("ip:"):
                host = cand_uri[3:]
                # Check if reachable first to avoid 15s kernel TCP timeout
                if not is_ip_reachable(host):
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
