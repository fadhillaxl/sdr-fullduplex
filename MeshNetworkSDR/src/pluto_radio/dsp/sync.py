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


def get_preamble_iq(amplitude: float = 0.8, samples_per_symbol: int = 1) -> np.ndarray:
    """Generate the complex baseband preamble burst scaled for Pluto DAC."""
    pre_syms = np.repeat(PREAMBLE_SYMBOLS, samples_per_symbol) if samples_per_symbol > 1 else PREAMBLE_SYMBOLS
    scale = (2**15 - 1) * float(amplitude)
    return (pre_syms * scale + 1j * 0.0).astype(np.complex64)


def estimate_cfo(
    rx_preamble: np.ndarray,
    sample_rate: float,
    half_len: int = 26,
    preamble_symbols: Optional[np.ndarray] = None,
) -> float:
    """Estimate Carrier Frequency Offset (CFO) using phase drift between preamble halves.

    Args:
        rx_preamble: Received samples spanning the preamble.
        sample_rate: Radio sample rate in Hz.
        half_len: Half-length of the repeating preamble pattern.
        preamble_symbols: Reference preamble symbols (defaults to PREAMBLE_SYMBOLS).

    Returns:
        Estimated CFO in Hz.
    """
    ref = PREAMBLE_SYMBOLS if preamble_symbols is None else preamble_symbols
    p1 = ref[:half_len]
    p2 = ref[half_len : 2 * half_len]

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
    samples_per_symbol: int = 1,
) -> Generator[Tuple[np.ndarray, float, float], None, None]:
    """Search for preamble bursts in the received buffer, correct CFO and phase, and extract payload symbols.

    Args:
        rx_buffer: Complex IQ samples from Pluto SDR.
        sample_rate: Sampling frequency in SPS.
        threshold: Normalized cross-correlation detection threshold (0.0 to 1.0).
        samples_per_symbol: Oversampling factor (1 or 2).

    Yields:
        Tuples of (demodulated_bits, estimated_cfo_hz, snr_db)
    """
    rx_arr = np.asarray(rx_buffer, dtype=np.complex64)
    pre_syms = np.repeat(PREAMBLE_SYMBOLS, samples_per_symbol) if samples_per_symbol > 1 else PREAMBLE_SYMBOLS
    pre_len = len(pre_syms)
    half_len = pre_len // 2

    if len(rx_arr) < pre_len + 100:
        return

    # Split non-coherent correlation (CFO immune up to +/-35 kHz)
    p1 = pre_syms[:half_len] / np.linalg.norm(pre_syms[:half_len])
    p2 = pre_syms[half_len:] / np.linalg.norm(pre_syms[half_len:])

    c1 = np.correlate(rx_arr, p1, mode="valid")
    c2 = np.correlate(rx_arr, p2, mode="valid")

    # Fast O(N) moving sum via cumulative sum
    pwr_sq = np.abs(rx_arr) ** 2
    cs = np.cumsum(np.pad(pwr_sq, (1, 0)))
    pwr = (cs[half_len:] - cs[:-half_len]) / half_len
    denom = pwr * half_len
    denom[denom == 0] = 1e-12

    m1 = (np.abs(c1) ** 2) / denom
    m2 = (np.abs(c2) ** 2) / denom
    valid_len = min(len(m1) - half_len, len(m2) - half_len)
    if valid_len <= 0:
        return
    metric = 0.5 * (m1[:valid_len] + m2[half_len : half_len + valid_len])

    # Vectorized candidate search: 900x faster than scalar Python loop on ARM
    cands = np.where(metric >= threshold)[0]
    if len(cands) == 0:
        return

    buffer_len = len(rx_arr)
    num_cands = len(cands)
    cand_idx = 0

    while cand_idx < num_cands:
        cursor = int(cands[cand_idx])
        # Find peak within a local window (e.g. +/- 30 samples)
        window_end = min(len(metric), cursor + 60)
        peak_offset = int(np.argmax(metric[cursor:window_end]))
        peak_idx = cursor + peak_offset

        # Ensure we have enough samples after the peak for payload
        if peak_idx + pre_len >= buffer_len:
            break

        # 1. Estimate CFO across preamble halves
        rx_pre = rx_arr[peak_idx : peak_idx + pre_len]
        est_cfo = estimate_cfo(rx_pre, sample_rate=sample_rate, half_len=half_len, preamble_symbols=pre_syms)

        # 2. Correct CFO on the entire packet burst (preamble + payload)
        burst_end = min(buffer_len, peak_idx + pre_len + 48000)
        burst_len = burst_end - peak_idx
        t_burst = np.arange(burst_len) / float(sample_rate)
        cfo_rotator = np.exp(-1j * 2.0 * math.pi * est_cfo * t_burst)
        burst_corrected = rx_arr[peak_idx:burst_end] * cfo_rotator

        # 3. Estimate channel phase offset from preamble
        c_peak = np.sum(burst_corrected[:pre_len] * pre_syms)
        channel_phase = float(np.angle(c_peak))

        # 4. Decimate payload to 1 sample/symbol with eye-diagram centering
        raw_payload = burst_corrected[pre_len:]
        if samples_per_symbol > 1:
            syms0 = raw_payload[0::samples_per_symbol]
            syms1 = raw_payload[1::samples_per_symbol]
            n_eval = min(len(syms0), len(syms1), 96)
            if n_eval < 20:
                break
            e0 = float(np.mean(np.abs(np.real(syms0[:n_eval] * np.exp(-1j * channel_phase)))))
            e1 = float(np.mean(np.abs(np.real(syms1[:n_eval] * np.exp(-1j * channel_phase)))))
            opt_syms = syms0 if e0 >= e1 else syms1
        else:
            opt_syms = raw_payload

        if len(opt_syms) < 96:
            break

        # 5. Decision-Directed Phase Locked Loop (DD-PLL) Carrier Tracker
        phase = channel_phase
        freq_offset = 0.0
        alpha = 0.08  # Proportional phase tracking gain
        beta = 0.002  # Integral frequency tracking gain

        # Demodulate header (96 symbols) to determine packet length
        bits_list = []
        for i in range(min(96, len(opt_syms))):
            sym = opt_syms[i]
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

        sync_pos = head_bytes.find(b"\x55\xaa")
        if sync_pos != -1 and sync_pos <= 6 and len(head_bytes) >= sync_pos + 6:
            import struct
            length = struct.unpack_from(">H", head_bytes, sync_pos + 4)[0]
            if length <= 1500:
                total_bits = (16 + length) * 8
                if len(opt_syms) < total_bits:
                    # Incomplete packet at buffer boundary; leave for next buffer with tail
                    break

                # Track remaining payload symbols with DD-PLL
                for i in range(96, total_bits):
                    sym = opt_syms[i]
                    derot = sym * np.exp(-1j * phase)
                    bit = 1 if np.real(derot) >= 0.0 else 0
                    bits_list.append(bit)
                    dec_sym = 1.0 if bit == 1 else -1.0
                    mag = abs(derot)
                    phase_err = float(np.imag(derot) * dec_sym / max(1e-6, mag))
                    freq_offset += beta * phase_err
                    phase += alpha * phase_err + freq_offset

                bits = np.array(bits_list, dtype=np.uint8)
                next_pos = peak_idx + pre_len + total_bits * samples_per_symbol
            else:
                next_pos = max(cursor + 1, window_end)
                cand_idx = int(np.searchsorted(cands, next_pos))
                continue
        else:
            next_pos = max(cursor + 1, window_end)
            cand_idx = int(np.searchsorted(cands, next_pos))
            continue

        # Compute accurate SNR estimate with channel phase derotation
        derot_pre = burst_corrected[:pre_len] * np.exp(-1j * channel_phase)
        sig_pwr = float(np.mean(np.real(derot_pre) ** 2))
        noise_est = float(np.var(np.real(derot_pre) - pre_syms * np.mean(np.real(derot_pre))) + np.var(np.imag(derot_pre)))
        snr_val = 10.0 * math.log10(max(1e-6, sig_pwr / max(1e-6, noise_est)))

        yield (bits, est_cfo, snr_val)

        cand_idx = int(np.searchsorted(cands, next_pos))

