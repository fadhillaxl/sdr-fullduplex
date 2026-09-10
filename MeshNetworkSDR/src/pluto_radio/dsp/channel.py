"""DSP Channel Simulation Models (AWGN, Frequency Offset, Phase Offset)."""

from __future__ import annotations

import numpy as np


def apply_awgn(samples: np.ndarray, snr_db: float) -> np.ndarray:
    """Add Additive White Gaussian Noise (AWGN) to achieve target SNR in dB.

    Args:
        samples: Complex or float input signal array.
        snr_db: Target Signal-to-Noise Ratio in decibels.

    Returns:
        Noisy signal array of same dtype and shape.
    """
    samples_arr = np.asarray(samples)
    if len(samples_arr) == 0:
        return samples_arr

    signal_power = np.mean(np.abs(samples_arr) ** 2)
    if signal_power == 0:
        return samples_arr

    snr_linear = 10.0 ** (snr_db / 10.0)
    noise_power = signal_power / snr_linear

    if np.iscomplexobj(samples_arr):
        sigma = np.sqrt(noise_power / 2.0)
        noise = np.random.normal(0.0, sigma, size=samples_arr.shape) + 1j * np.random.normal(
            0.0, sigma, size=samples_arr.shape
        )
    else:
        sigma = np.sqrt(noise_power)
        noise = np.random.normal(0.0, sigma, size=samples_arr.shape)

    return (samples_arr + noise).astype(samples_arr.dtype)


def apply_cfo(samples: np.ndarray, cfo_hz: float, sample_rate: float) -> np.ndarray:
    """Apply Carrier Frequency Offset (CFO) to complex IQ samples."""
    samples_arr = np.asarray(samples, dtype=np.complex64)
    t = np.arange(len(samples_arr)) / float(sample_rate)
    rotator = np.exp(1j * 2.0 * np.pi * cfo_hz * t)
    return (samples_arr * rotator).astype(np.complex64)
