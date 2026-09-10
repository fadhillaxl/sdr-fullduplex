"""Tests for hardware detection and simulation modes."""

from unittest.mock import MagicMock, patch
import pytest

from pluto_radio.hardware.iio import get_troubleshooting_guide, scan_iio_contexts
from pluto_radio.hardware.pluto import PlutoDetector, PlutoDeviceInfo, SimulatedPlutoDevice


def test_troubleshooting_guide():
    guide = get_troubleshooting_guide()
    assert "Pluto SDR not detected" in guide
    assert "USB connection" in guide
    assert "iio_info -s" in guide
    assert "libiio installation" in guide


def test_simulation_detection():
    detector = PlutoDetector()
    info = detector.detect(simulation=True)
    assert info.status == "SIMULATION"
    assert info.uri == "sim:pluto0"
    assert "Simulated" in info.model
    assert info.tx_channels == "OK"
    assert info.rx_channels == "OK"

    report = info.format_report()
    assert "================================" in report
    assert "PLUTO SDR" in report
    assert "Status       : SIMULATION" in report
    assert "URI          : sim:pluto0" in report


def test_detection_hardware_not_found():
    detector = PlutoDetector(default_uri="ip:192.0.2.254")  # non-routable dummy test IP
    # When probing fails on nonexistent IP, returns NOT FOUND with troubleshooting guide
    with patch("pluto_radio.hardware.pluto.find_candidate_uris", return_value=["ip:192.0.2.254"]):
        with patch("adi.Pluto", side_effect=Exception("Connection timed out")):
            info = detector.detect(simulation=False)
            assert info.status == "NOT FOUND"
            assert info.troubleshooting is not None
            assert "Pluto SDR not detected" in info.troubleshooting


def test_detection_hardware_success():
    mock_sdr = MagicMock()
    mock_sdr.sample_rate = 2000000

    detector = PlutoDetector(default_uri="ip:192.168.2.1")
    with patch("pluto_radio.hardware.pluto.is_ip_reachable", return_value=True):
        with patch("pluto_radio.hardware.pluto.find_candidate_uris", return_value=["ip:192.168.2.1"]):
            with patch("adi.Pluto", return_value=mock_sdr):
                info = detector.detect(simulation=False)
                assert info.status == "CONNECTED"
                assert info.uri == "ip:192.168.2.1"
                assert info.tx_channels == "OK"
                assert info.rx_channels == "OK"
                assert "2,000,000 SPS" in info.sample_rate


def test_simulated_pluto_device():
    dev = SimulatedPlutoDevice()
    assert dev.sample_rate == 2000000
    assert dev.rx_lo == 433000000
    assert dev.tx_lo == 433000000

    import numpy as np
    tx_data = np.array([1.0 + 1j * 0.0, 0.0 + 1j * 1.0], dtype=np.complex64)
    dev.tx(tx_data)
    rx_data = dev.rx()
    assert len(rx_data) == len(tx_data)
    # Check that rx received the tx data with small noise
    np.testing.assert_allclose(rx_data.real, tx_data.real, atol=0.01)
    np.testing.assert_allclose(rx_data.imag, tx_data.imag, atol=0.01)
