"""Stage 3: Quadrature Phase Shift Keying (QPSK) Modulation and Demodulation with Gray Coding."""

from __future__ import annotations

import math
import numpy as np

from .bpsk import bytes_to_bits, bits_to_bytes, calculate_ber


# Gray Coding Constellation Mapping:
# 00 -> (+1 + 1j) / sqrt(2)
# 01 -> (-1 + 1j) / sqrt(2)
# 11 -> (-1 - 1j) / sqrt(2)
# 10 -> (+1 - 1j) / sqrt(2)
GRAY_TABLE_MAP = {
    (0, 0): complex(1.0, 1.0) / math.sqrt(2),
    (0, 1): complex(-1.0, 1.0) / math.sqrt(2),
    (1, 1): complex(-1.0, -1.0) / math.sqrt(2),
    (1, 0): complex(1.0, -1.0) / math.sqrt(2),
}


def qpsk_modulate(
    bits: np.ndarray | bytes,
    amplitude: float = 0.8,
    samples_per_symbol: int = 1,
) -> np.ndarray:
    """Modulate a sequence of bits to QPSK complex symbols using Gray coding.

    Args:
        bits: Bit array or raw bytes.
        amplitude: Normalized amplitude scalar (0.0 to 1.0).
        samples_per_symbol: Oversampling factor.

    Returns:
        Complex IQ array (np.complex64) scaled for Pluto DAC (+/- 16384 * amplitude).
    """
    if isinstance(bits, (bytes, bytearray)):
        bit_array = bytes_to_bits(bits)
    else:
        bit_array = np.asarray(bits, dtype=np.uint8).flatten()

    # Ensure even number of bits for QPSK pairs
    if len(bit_array) % 2 != 0:
        bit_array = np.append(bit_array, 0)

    scale = (2**15 - 1) * float(amplitude)

    b0 = bit_array[0::2]
    b1 = bit_array[1::2]

    # Gray coding mapping:
    # I component: +1 if b1 == 0 else -1
    # Q component: +1 if b0 == 0 else -1
    # Check:
    # (0,0) -> I=+1, Q=+1
    # (0,1) -> I=-1, Q=+1
    # (1,1) -> I=-1, Q=-1
    # (1,0) -> I=+1, Q=-1
    i_comp = np.where(b1 == 0, 1.0, -1.0) / math.sqrt(2)
    q_comp = np.where(b0 == 0, 1.0, -1.0) / math.sqrt(2)

    symbols = ((i_comp + 1j * q_comp) * scale).astype(np.complex64)

    if samples_per_symbol > 1:
        symbols = np.repeat(symbols, samples_per_symbol)

    return symbols


def qpsk_demodulate(
    symbols: np.ndarray,
    samples_per_symbol: int = 1,
) -> np.ndarray:
    """Demodulate QPSK complex symbols to binary bits using Gray decision boundaries.

    Decision boundaries:
      I >= 0 -> b1 = 0, else 1
      Q >= 0 -> b0 = 0, else 1

    Args:
        symbols: Complex IQ symbols.
        samples_per_symbol: Downsampling factor.

    Returns:
        1D numpy array of uint8 bits.
    """
    sym_arr = np.asarray(symbols, dtype=np.complex64)
    if len(sym_arr) == 0:
        return np.array([], dtype=np.uint8)

    if samples_per_symbol > 1:
        midpoint = samples_per_symbol // 2
        sym_arr = sym_arr[midpoint::samples_per_symbol]

    i_val = np.real(sym_arr)
    q_val = np.imag(sym_arr)

    b0 = np.where(q_val >= 0.0, 0, 1).astype(np.uint8)
    b1 = np.where(i_val >= 0.0, 0, 1).astype(np.uint8)

    bits = np.empty(len(sym_arr) * 2, dtype=np.uint8)
    bits[0::2] = b0
    bits[1::2] = b1
    return bits


def calculate_evm(ideal_symbols: np.ndarray, received_symbols: np.ndarray) -> float:
    """Calculate Error Vector Magnitude (EVM) in percentage (%)."""
    s_ideal = np.asarray(ideal_symbols, dtype=np.complex64).flatten()
    s_rx = np.asarray(received_symbols, dtype=np.complex64).flatten()

    min_len = min(len(s_ideal), len(s_rx))
    if min_len == 0:
        return 0.0

    s_ideal = s_ideal[:min_len]
    s_rx = s_rx[:min_len]

    # Normalize power
    ref_pwr = np.mean(np.abs(s_ideal) ** 2)
    if ref_pwr == 0:
        return 0.0

    error_vectors = s_rx - s_ideal
    err_pwr = np.mean(np.abs(error_vectors) ** 2)
    evm_rms = math.sqrt(err_pwr / ref_pwr)
    return float(evm_rms * 100.0)


def ascii_constellation(symbols: np.ndarray) -> str:
    """Render terminal ASCII 4-quadrant constellation diagnostic.

    Format strictly according to Section 9 of the prompt:
            Q
            │
        ●   │   ●
            │
    ────────┼──────── I
            │
        ●   │   ●
            │
    """
    sym_arr = np.asarray(symbols, dtype=np.complex64)
    q1 = np.sum((np.real(sym_arr) >= 0) & (np.imag(sym_arr) >= 0))
    q2 = np.sum((np.real(sym_arr) < 0) & (np.imag(sym_arr) >= 0))
    q3 = np.sum((np.real(sym_arr) < 0) & (np.imag(sym_arr) < 0))
    q4 = np.sum((np.real(sym_arr) >= 0) & (np.imag(sym_arr) < 0))
    total = max(1, len(sym_arr))

    c_q2 = "●" if q2 / total > 0.05 else " "
    c_q1 = "●" if q1 / total > 0.05 else " "
    c_q3 = "●" if q3 / total > 0.05 else " "
    c_q4 = "●" if q4 / total > 0.05 else " "

    lines = [
        "        Q        ",
        "        │        ",
        f"    {c_q2}   │   {c_q1}    ",
        "        │        ",
        "────────┼──────── I",
        "        │        ",
        f"    {c_q3}   │   {c_q4}    ",
        "        │        ",
    ]
    return "\n".join(lines)
