"""RF signal metrics and test tone generation for Stage 1."""

from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np


@dataclass
class RFMetrics:
    """Spectral metrics measured from received IQ samples."""
    signal_dbfs: float
    noise_dbfs: float
    snr_db: float
    rssi_dbfs: float
    peak_freq_offset_hz: float = 0.0

    def format_report(self) -> str:
        return (
            "RX\n"
            "----------------------\n"
            f"Signal : {self.signal_dbfs:+.1f} dBFS\n"
            f"Noise  : {self.noise_dbfs:+.1f} dBFS\n"
            f"SNR    : {self.snr_db:.1f} dB"
        )


def generate_complex_tone(
    tone_freq_hz: float = 100_000.0,
    sample_rate: float = 1_000_000.0,
    num_samples: int = 10_000,
    amplitude: float = 0.8,
) -> np.ndarray:
    """Generate a cyclic continuous-phase complex tone for Pluto SDR TX.

    To ensure perfect cyclic boundary continuity, the tone period is adjusted
    so that an exact integer number of cycles fits in num_samples.
    
    Returns:
        np.ndarray of complex64 scaled to Pluto integer range (+/- 2**14).
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if num_samples <= 0:
        raise ValueError("num_samples must be positive")

    # Align tone frequency to nearest exact FFT / cyclic bin
    cycles = max(1, round(tone_freq_hz * num_samples / sample_rate))
    actual_freq = cycles * sample_rate / num_samples

    t = np.arange(num_samples) / sample_rate
    phase = 2.0 * np.pi * actual_freq * t
    complex_tone = np.exp(1j * phase)

    # Pluto AD9361 16-bit integer DAC scale (+/- 2**14 = 16384)
    scale = (2**14 - 1) * max(0.01, min(1.0, amplitude))
    iq_samples = (complex_tone * scale).astype(np.complex64)
    return iq_samples


def compute_rf_metrics(
    iq_samples: np.ndarray,
    sample_rate: float = 1_000_000.0,
    reference_scale: float = 16384.0,
) -> RFMetrics:
    """Compute Signal Power, Noise Floor, SNR, and RSSI from IQ buffer.
    
    Args:
        iq_samples: Array of complex IQ samples from Pluto SDR or simulation.
        sample_rate: Sample rate in Hz.
        reference_scale: Full-scale reference magnitude (16384 for Pluto raw int16).
        
    Returns:
        RFMetrics dataclass instance.
    """
    n = len(iq_samples)
    if n < 64:
        raise ValueError(f"Too few samples for spectral estimation: {n}")

    # Determine normalization reference
    max_amp = float(np.max(np.abs(iq_samples))) if n > 0 else 0.0
    # If samples are already normalized in [-1.0, 1.0], scale accordingly
    norm_scale = 1.0 if max_amp <= 2.0 else reference_scale

    norm_iq = iq_samples / norm_scale

    # 1. Total RMS RSSI
    mean_power = float(np.mean(np.abs(norm_iq) ** 2))
    rssi_dbfs = 10.0 * math.log10(max(mean_power, 1e-12))

    # 2. Windowed FFT Power Spectral Density
    window = np.hanning(n)
    win_power_gain = float(np.mean(window ** 2))
    windowed = norm_iq * window

    fft_vals = np.fft.fftshift(np.fft.fft(windowed))
    psd = (np.abs(fft_vals) ** 2) / (n * win_power_gain)

    # 3. Peak signal bin search
    peak_idx = int(np.argmax(psd))
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate))
    peak_freq_offset = float(freqs[peak_idx])

    # Integrate signal power across peak bin +/- 3 bins (accounting for window mainlobe)
    guard = 4
    idx_min = max(0, peak_idx - guard)
    idx_max = min(n, peak_idx + guard + 1)

    signal_power = float(np.sum(psd[idx_min:idx_max]) / n)
    signal_dbfs = 10.0 * math.log10(max(signal_power, 1e-12))

    # 4. Noise floor calculation: mask out signal peak and DC spike (+/- 3 bins around DC)
    dc_idx = n // 2
    dc_guard = 3
    mask = np.ones(n, dtype=bool)
    mask[idx_min:idx_max] = False
    mask[max(0, dc_idx - dc_guard):min(n, dc_idx + dc_guard + 1)] = False

    noise_bins = psd[mask]
    if len(noise_bins) > 0:
        # Robust noise floor: median of non-signal bins scaled to total bandwidth
        noise_bin_level = float(np.median(noise_bins))
        # Total equivalent in-band noise power
        noise_power = noise_bin_level
        noise_dbfs = 10.0 * math.log10(max(noise_power, 1e-12))
    else:
        noise_dbfs = signal_dbfs - 30.0

    # 5. SNR calculation
    snr_db = max(0.0, signal_dbfs - noise_dbfs)

    return RFMetrics(
        signal_dbfs=signal_dbfs,
        noise_dbfs=noise_dbfs,
        snr_db=snr_db,
        rssi_dbfs=rssi_dbfs,
        peak_freq_offset_hz=peak_freq_offset,
    )
