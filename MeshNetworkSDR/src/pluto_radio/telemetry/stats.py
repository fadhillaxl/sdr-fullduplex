"""Radio statistics and telemetry data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RadioStats:
    tx_packets: int = 0
    rx_packets: int = 0
    crc_errors: int = 0
    fec_errors: int = 0
    packet_loss: int = 0
    rssi: Optional[float] = None
    snr: Optional[float] = None
    ber: Optional[float] = None
    per: Optional[float] = None
    evm: Optional[float] = None
    cfo: Optional[float] = None
    throughput_kbps: float = 0.0
    latency_ms: Optional[float] = None

    def format_report(self) -> str:
        """Format telemetry output matching PRD Section 17 & 20."""
        lines = [
            "--------------------------------",
            "PLUTO RADIO LINK",
            "--------------------------------",
            f"RSSI       : {f'{self.rssi:.1f} dBFS' if self.rssi is not None else 'N/A'}",
            f"SNR        : {f'{self.snr:.1f} dB' if self.snr is not None else 'N/A'}",
            f"EVM        : {f'{self.evm:.1f} %' if self.evm is not None else 'N/A'}",
            f"CFO        : {f'{self.cfo:.1f} Hz' if self.cfo is not None else 'N/A'}",
            "",
            f"TX packets : {self.tx_packets}",
            f"RX packets : {self.rx_packets}",
            f"CRC errors : {self.crc_errors}",
            f"PER        : {f'{self.per:.2f} %' if self.per is not None else '0.00 %'}",
            "",
            f"Throughput : {self.throughput_kbps:.1f} kbps",
            f"Latency    : {f'{self.latency_ms:.1f} ms' if self.latency_ms is not None else 'N/A'}",
            "--------------------------------",
        ]
        return "\n".join(lines)
