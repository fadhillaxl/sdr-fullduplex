"""Configuration management for Pluto+ SDR IP Radio."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


@dataclass
class RadioConfig:
    uri: str = "ip:192.168.2.1"
    center_frequency: int = 433000000
    sample_rate: int = 2000000
    bandwidth: int = 1000000
    tx_gain: int = -20
    rx_gain: int = 40
    rx_gain_mode: str = "slow_attack"


@dataclass
class OFDMConfig:
    fft_size: int = 64
    cyclic_prefix: int = 16
    pilot_spacing: int = 4


@dataclass
class ModulationConfig:
    mode: str = "bpsk"


@dataclass
class NetworkConfig:
    mtu: int = 1024


@dataclass
class DebugConfig:
    simulation_mode: bool = True


@dataclass
class AppConfig:
    radio: RadioConfig = field(default_factory=RadioConfig)
    ofdm: OFDMConfig = field(default_factory=OFDMConfig)
    modulation: ModulationConfig = field(default_factory=ModulationConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)

    def validate(self) -> None:
        """Validate configuration values."""
        if self.radio.center_frequency <= 0:
            raise ValueError(f"Invalid center_frequency: {self.radio.center_frequency}. Must be > 0.")
        if self.radio.sample_rate <= 0:
            raise ValueError(f"Invalid sample_rate: {self.radio.sample_rate}. Must be > 0.")
        if self.radio.bandwidth <= 0:
            raise ValueError(f"Invalid bandwidth: {self.radio.bandwidth}. Must be > 0.")
        if self.ofdm.fft_size <= 0 or (self.ofdm.fft_size & (self.ofdm.fft_size - 1)) != 0:
            raise ValueError(f"Invalid fft_size: {self.ofdm.fft_size}. Must be a power of 2.")
        if self.ofdm.cyclic_prefix < 0 or self.ofdm.cyclic_prefix >= self.ofdm.fft_size:
            raise ValueError(f"Invalid cyclic_prefix: {self.ofdm.cyclic_prefix}. Must be 0 <= CP < fft_size.")
        if self.modulation.mode.lower() not in ("bpsk", "qpsk", "16qam", "64qam"):
            raise ValueError(f"Unsupported modulation mode: {self.modulation.mode}")
        if self.network.mtu < 64 or self.network.mtu > 9000:
            raise ValueError(f"Invalid MTU: {self.network.mtu}. Must be between 64 and 9000.")


def find_default_config_path() -> Optional[Path]:
    """Search for radio.yaml in common project locations across OSes."""
    env_path = os.getenv("PLUTO_RADIO_CONFIG")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    candidates: list[Path] = [
        Path.cwd() / "config" / "radio.yaml",
        Path.cwd() / "radio.yaml",
    ]

    # Walk up parent directories to locate config/radio.yaml
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        candidates.append(curr / "config" / "radio.yaml")
        candidates.append(curr / "MeshNetworkSDR" / "config" / "radio.yaml")
        if curr.parent == curr:
            break
        curr = curr.parent

    for p in candidates:
        if p.is_file():
            return p
    return None


def load_config(config_path: Optional[str | Path] = None) -> AppConfig:
    """Load configuration from YAML file or return defaults if not specified/found."""
    resolved_path: Optional[Path] = None
    if config_path:
        resolved_path = Path(config_path)
        if not resolved_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {resolved_path}")
    else:
        resolved_path = find_default_config_path()

    if resolved_path is None or not resolved_path.is_file():
        config = AppConfig()
        config.validate()
        return config

    with open(resolved_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}

    radio_data = data.get("radio", {})
    ofdm_data = data.get("ofdm", {})
    mod_data = data.get("modulation", {})
    net_data = data.get("network", {})
    debug_data = data.get("debug", {})

    config = AppConfig(
        radio=RadioConfig(
            uri=str(radio_data.get("uri", "ip:192.168.2.1")),
            center_frequency=int(radio_data.get("center_frequency", 433000000)),
            sample_rate=int(radio_data.get("sample_rate", 2000000)),
            bandwidth=int(radio_data.get("bandwidth", 1000000)),
            tx_gain=int(radio_data.get("tx_gain", -20)),
            rx_gain_mode=str(radio_data.get("rx_gain_mode", "slow_attack")),
        ),
        ofdm=OFDMConfig(
            fft_size=int(ofdm_data.get("fft_size", 64)),
            cyclic_prefix=int(ofdm_data.get("cyclic_prefix", 16)),
            pilot_spacing=int(ofdm_data.get("pilot_spacing", 4)),
        ),
        modulation=ModulationConfig(
            mode=str(mod_data.get("mode", "bpsk")),
        ),
        network=NetworkConfig(
            mtu=int(net_data.get("mtu", 1024)),
        ),
        debug=DebugConfig(
            simulation_mode=bool(debug_data.get("simulation_mode", True)),
        ),
    )
    config.validate()
    return config
