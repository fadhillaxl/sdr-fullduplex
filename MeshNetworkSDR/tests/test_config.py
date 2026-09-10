"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path
import pytest
import yaml

from pluto_radio.config import (
    AppConfig,
    RadioConfig,
    OFDMConfig,
    ModulationConfig,
    NetworkConfig,
    DebugConfig,
    load_config,
)


def test_default_config():
    cfg = AppConfig()
    cfg.validate()
    assert cfg.radio.center_frequency == 433000000
    assert cfg.radio.sample_rate == 2000000
    assert cfg.ofdm.fft_size == 64
    assert cfg.ofdm.cyclic_prefix == 16
    assert cfg.modulation.mode == "bpsk"
    assert cfg.network.mtu == 1024


def test_load_config_from_file():
    data = {
        "radio": {
            "uri": "ip:192.168.2.10",
            "center_frequency": 915000000,
            "sample_rate": 3000000,
            "bandwidth": 2000000,
            "tx_gain": -15,
            "rx_gain_mode": "manual",
        },
        "ofdm": {
            "fft_size": 128,
            "cyclic_prefix": 32,
            "pilot_spacing": 8,
        },
        "modulation": {
            "mode": "qpsk",
        },
        "network": {
            "mtu": 1500,
        },
        "debug": {
            "simulation_mode": False,
        },
    }

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        temp_path = Path(f.name)

    try:
        cfg = load_config(temp_path)
        assert cfg.radio.uri == "ip:192.168.2.10"
        assert cfg.radio.center_frequency == 915000000
        assert cfg.ofdm.fft_size == 128
        assert cfg.ofdm.cyclic_prefix == 32
        assert cfg.modulation.mode == "qpsk"
        assert cfg.network.mtu == 1500
        assert cfg.debug.simulation_mode is False
    finally:
        temp_path.unlink()


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/non/existent/path/radio.yaml")


@pytest.mark.parametrize(
    "fft_size,valid",
    [
        (64, True),
        (128, True),
        (63, False),
        (0, False),
        (-16, False),
    ],
)
def test_fft_size_validation(fft_size, valid):
    cfg = AppConfig(ofdm=OFDMConfig(fft_size=fft_size, cyclic_prefix=8))
    if valid:
        cfg.validate()
    else:
        with pytest.raises(ValueError, match="fft_size"):
            cfg.validate()


def test_cyclic_prefix_validation():
    # CP >= fft_size should fail
    cfg = AppConfig(ofdm=OFDMConfig(fft_size=64, cyclic_prefix=64))
    with pytest.raises(ValueError, match="cyclic_prefix"):
        cfg.validate()


def test_modulation_validation():
    cfg = AppConfig(modulation=ModulationConfig(mode="unsupported_mode"))
    with pytest.raises(ValueError, match="Unsupported modulation mode"):
        cfg.validate()
