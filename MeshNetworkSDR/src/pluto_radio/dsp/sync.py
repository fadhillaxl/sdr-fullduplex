"""Stage 11: Preamble Cross-Correlation, Packet Detection, CFO Estimation & Phase Synchronization."""

from __future__ import annotations

import math
from typing import Generator, Tuple
import numpy as np

# Barker-13 sequence repeated 4 times (52 symbols)
# Offers exceptional autocorrelation peak-to-sidelobe ratio (> 15 dB)
BARKER_13 = np.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=np.float32)
PREAMBLE_SYMBOLS = np.tile(BARKER_13, 4)
PREAMBLE_LEN = len(PREAMBLE_SYMBOLS)  # 52


def get_preamble_iq(amplitude: float = 0.8) -> np.ndarray:
    """Generate the complex baseband preamble burst scaled for Pluto DAC."""
    scale = (2**15 - 1) * float(amplitude)
    return (PREAMBLE_SYMBOLS * scale + 1j * 0.0).astype(np.complex64)


def estimate_cfo(
    rx_preamble: np.ndarray,
    sample_rate: float,
    half_len: int = 26,
) -> float:
    """Estimate Carrier Frequency Offset (CFO) using phase drift between preamble halves.

    Args:
        rx_preamble: Received samples spanning the preamble (at least 52 samples).
        sample_rate: Radio sample rate in Hz.
        half_len: Half-length of the repeating preamble pattern.

    Returns:
        Estimated CFO in Hz.
    """
    p1 = PREAMBLE_SYMBOLS[:half_len]
    p2 = PREAMBLE_SYMBOLS[half_len : 2 * half_len]

    c1 = np.sum(rx_preamble[:half_len] * p1)
    c2 = np.sum(rx_preamble[half_len : 2 * half_len] * p2)

    if c1 == 0 or c2 == 0:
        return 0.0

    phase_drift = float(np.angle(c2 * np.conj(c1)))
    time_delta = float(half_len) / float(sample_rate)
    return phase_drift / (2.0 * math.pi * time_delta)


def detect_and_synchronize_packets(
    rx_buffer: np.ndarray,
    sample_rate: float = 2_000_000.0,
    threshold: float = 0.25,
) -> Generator[Tuple[np.ndarray, float, float], None, None]:
    """Search for preamble bursts in the received buffer, correct CFO and phase, and extract payload symbols.

    Args:
        rx_buffer: Complex IQ samples from Pluto SDR.
        sample_rate: Sampling frequency in SPS.
        threshold: Normalized cross-correlation detection threshold (0.0 to 1.0).

    Yields:
        Tuples of (demodulated_bits, estimated_cfo_hz, snr_db)
    """
    rx_arr = np.asarray(rx_buffer, dtype=np.complex64)
    if len(rx_arr) < PREAMBLE_LEN + 100:
        return

    # Normalize template
    p_norm = PREAMBLE_SYMBOLS / np.linalg.norm(PREAMBLE_SYMBOLS)

    # Cross-correlation with preamble
    corr = np.correlate(rx_arr, p_norm, mode="valid")
    corr_mag_sq = np.abs(corr) ** 2

    # Moving average of received signal power
    kernel = np.ones(PREAMBLE_LEN, dtype=np.float32) / PREAMBLE_LEN
    pwr = np.convolve(np.abs(rx_arr) ** 2, kernel, mode="valid")

    # Normalized cross-correlation metric M[n] in [0, 1]
    denom = pwr[: len(corr_mag_sq)] * PREAMBLE_LEN
    denom[denom == 0] = 1e-12
    metric = corr_mag_sq / denom

    cursor = 0
    buffer_len = len(rx_arr)

    while cursor < len(metric):
        # Look for local peak above threshold
        if metric[cursor] >= threshold:
            # Find peak within a local window (e.g. +/- 30 samples)
            window_end = min(len(metric), cursor + 60)
            peak_offset = int(np.argmax(metric[cursor:window_end]))
            peak_idx = cursor + peak_offset

            # Ensure we have enough samples after the peak for payload
            if peak_idx + PREAMBLE_LEN >= buffer_len:
                break

            # 1. Estimate CFO across preamble halves
            rx_pre = rx_arr[peak_idx : peak_idx + PREAMBLE_LEN]
            est_cfo = estimate_cfo(rx_pre, sample_rate=sample_rate, half_len=26)

            # 2. Correct CFO on the entire packet burst (preamble + payload)
            burst_end = min(buffer_len, peak_idx + PREAMBLE_LEN + 24000)
            burst_len = burst_end - peak_idx
            t_burst = np.arange(burst_len) / float(sample_rate)
            cfo_rotator = np.exp(-1j * 2.0 * math.pi * est_cfo * t_burst)
            burst_corrected = rx_arr[peak_idx:burst_end] * cfo_rotator

            # 3. Estimate channel phase offset from preamble
            c_peak = np.sum(burst_corrected[:PREAMBLE_LEN] * PREAMBLE_SYMBOLS)
            channel_phase = float(np.angle(c_peak))

            # 4. Decision-Directed Phase Locked Loop (DD-PLL) Carrier Tracker
            # Tracks residual frequency offset and phase drift continuously across all symbols
            raw_payload = burst_corrected[PREAMBLE_LEN:]
            if len(raw_payload) < 96:
                cursor = max(cursor + 1, window_end)
                continue

            phase = channel_phase
            freq_offset = 0.0
            alpha = 0.08  # Proportional phase tracking gain
            beta = 0.002  # Integral frequency tracking gain

            # Demodulate header (96 symbols) to determine packet length
            bits_list = []
            for i in range(min(96, len(raw_payload))):
                sym = raw_payload[i]
                derot = sym * np.exp(-1j * phase)
                bit = 1 if np.real(derot) >= 0.0 else 0
                bits_list.append(bit)
                dec_sym = 1.0 if bit == 1 else -1.0
                mag = abs(derot)
                phase_err = float(np.imag(derot) * dec_sym / max(1e-6, mag))
                freq_offset += beta * phase_err
                phase += alpha * phase_err + freq_offset

            from .bpsk import bits_to_bytes
            head_bytes = bits_to_bytes(np.array(bits_list, dtype=np.uint8))

            if len(head_bytes) >= 6 and head_bytes[4:6] == b"\x55\xaa":
                import struct
                length = struct.unpack_from(">H", head_bytes, 8)[0]
                if length <= 1500:
                    total_bits = (16 + length) * 8
                    if len(raw_payload) < total_bits:
                        # Incomplete packet at buffer boundary; leave for next buffer with tail
                        break

                    # Track remaining payload symbols with DD-PLL
                    for i in range(96, total_bits):
                        sym = raw_payload[i]
                        derot = sym * np.exp(-1j * phase)
                        bit = 1 if np.real(derot) >= 0.0 else 0
                        bits_list.append(bit)
                        dec_sym = 1.0 if bit == 1 else -1.0
                        mag = abs(derot)
                        phase_err = float(np.imag(derot) * dec_sym / max(1e-6, mag))
                        freq_offset += beta * phase_err
                        phase += alpha * phase_err + freq_offset

                    bits = np.array(bits_list, dtype=np.uint8)
                    cursor = peak_idx + PREAMBLE_LEN + total_bits
                else:
                    cursor = max(cursor + 1, window_end)
                    continue
            else:
                cursor = max(cursor + 1, window_end)
                continue

            # Compute local SNR estimate
            sig_pwr = np.mean(np.abs(burst_corrected[:PREAMBLE_LEN]) ** 2)
            noise_est = np.var(burst_corrected[:PREAMBLE_LEN] - PREAMBLE_SYMBOLS * np.mean(np.abs(burst_corrected[:PREAMBLE_LEN])))
            snr_val = 10.0 * math.log10(max(1e-6, sig_pwr / max(1e-6, noise_est)))

            yield (bits, est_cfo, snr_val)
        else:
            cursor += 1

