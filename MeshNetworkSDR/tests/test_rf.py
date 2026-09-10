"""Automated test suite for Stage 1: RF Tone TX and Signal Power/Noise/SNR RX."""

import math
import numpy as np
import pytest

from pluto_radio.dsp.rf_metrics import generate_complex_tone, compute_rf_metrics, RFMetrics
from pluto_radio.hardware.pluto import SimulatedPlutoDevice, PlutoTransceiver
from pluto_radio.cli import main


def test_tone_generation():
    """Verify complex test tone properties and boundary continuity."""
    sample_rate = 1_000_000
    tone_freq = 100_000
    num_samples = 10_000
    amplitude = 0.8

    tone = generate_complex_tone(
        tone_freq_hz=tone_freq,
        sample_rate=sample_rate,
        num_samples=num_samples,
        amplitude=amplitude,
    )

    assert len(tone) == num_samples
    assert tone.dtype == np.complex64

    # Peak amplitude should be scaled within Pluto DAC limit (+/- 16384)
    max_val = np.max(np.abs(tone))
    expected_scale = (2**14 - 1) * amplitude
    assert math.isclose(max_val, expected_scale, rel_tol=0.05)

    # FFT peak should be exactly at +100 kHz
    fft_spec = np.abs(np.fft.fft(tone))
    freqs = np.fft.fftfreq(num_samples, d=1.0 / sample_rate)
    peak_freq = freqs[np.argmax(fft_spec)]
    assert abs(peak_freq - tone_freq) < (sample_rate / num_samples)


def test_rf_metrics_pure_tone():
    """Verify metrics computation on a pure simulated tone."""
    sample_rate = 1_000_000
    tone = generate_complex_tone(
        tone_freq_hz=100_000,
        sample_rate=sample_rate,
        num_samples=10_000,
        amplitude=0.8,
    )

    metrics = compute_rf_metrics(tone, sample_rate=sample_rate)

    assert isinstance(metrics, RFMetrics)
    assert -5.0 < metrics.signal_dbfs < 0.0  # ~ -2 dBFS for 0.8 amplitude
    assert metrics.noise_dbfs < -40.0
    assert metrics.snr_db > 35.0
    assert "RX" in metrics.format_report()
    assert "Signal :" in metrics.format_report()
    assert "SNR    :" in metrics.format_report()


def test_rf_metrics_noisy_signal():
    """Verify SNR computation against known injected AWGN noise."""
    sample_rate = 1_000_000
    n = 10_000
    t = np.arange(n) / sample_rate

    # Signal with known power
    sig_amp = 1000.0
    signal = sig_amp * np.exp(1j * 2.0 * np.pi * 150_000.0 * t)

    # Noise with known power (~ 20 dB lower)
    noise_sigma = 100.0  # Power ratio ~ (1000/100)^2 = 100 = 20 dB
    noise = (np.random.randn(n) + 1j * np.random.randn(n)) * (noise_sigma / np.sqrt(2))

    combined = (signal + noise).astype(np.complex64)
    metrics = compute_rf_metrics(combined, sample_rate=sample_rate)

    assert metrics.signal_dbfs > metrics.noise_dbfs
    assert 15.0 < metrics.snr_db < 26.0


def test_simulated_pluto_transceiver():
    """Verify PlutoTransceiver in simulation mode for Stage 1."""
    trx = PlutoTransceiver(simulation=True, sample_rate=1_000_000)
    trx.configure_tx(freq_hz=433_000_000, gain_db=-20)
    trx.configure_rx(freq_hz=433_000_000, gain_db=40)

    # 1. Test RX default tone reception (simulates incoming OTA signal)
    rx_samples = trx.receive_iq(10_000)
    assert len(rx_samples) == 10_000
    metrics = compute_rf_metrics(rx_samples, sample_rate=1_000_000)
    assert -55.0 < metrics.signal_dbfs < -35.0  # Approx -45.2 dBFS per prompt
    assert -80.0 < metrics.noise_dbfs < -65.0  # Approx -72.4 dBFS per prompt
    assert metrics.snr_db > 20.0               # Approx 27.2 dB per prompt

    # 2. Test active cyclic TX -> loopback
    trx.start_tone_tx(tone_freq_hz=100_000.0)
    assert trx._is_tx_running is True
    loopback_samples = trx.receive_iq(10_000)
    trx.stop_tx()
    assert trx._is_tx_running is False

    loopback_metrics = compute_rf_metrics(loopback_samples, sample_rate=1_000_000)
    assert loopback_metrics.snr_db > 20.0


def test_cli_tx_and_rx_simulation(capsys):
    """Verify CLI tx and rx subcommands in simulation mode."""
    # Test CLI tx with short duration
    ret_tx = main(["tx", "--simulation", "--duration", "0.2"])
    assert ret_tx == 0
    captured_tx = capsys.readouterr()
    assert "PLUTO SDR RF TRANSMITTER (STAGE 1)" in captured_tx.out
    assert "Transmitting continuous CW tone" in captured_tx.out

    # Test CLI rx with single measurement count
    ret_rx = main(["rx", "--simulation", "--count", "1"])
    assert ret_rx == 0
    captured_rx = capsys.readouterr()
    assert "PLUTO SDR RF RECEIVER (STAGE 1)" in captured_rx.out
    assert "Signal :" in captured_rx.out
    assert "Noise  :" in captured_rx.out
    assert "SNR    :" in captured_rx.out
