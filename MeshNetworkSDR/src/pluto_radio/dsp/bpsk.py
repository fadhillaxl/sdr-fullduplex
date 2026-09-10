"""Stage 2: Binary Phase Shift Keying (BPSK) Modulation and Demodulation."""

from __future__ import annotations

import numpy as np


def bytes_to_bits(data: bytes | bytearray) -> np.ndarray:
    """Convert bytes to an array of individual bits (0 or 1, MSB first)."""
    byte_arr = np.frombuffer(data, dtype=np.uint8)
    return np.unpackbits(byte_arr)


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """Pack an array of bits (0 or 1) into bytes (MSB first)."""
    bits_arr = np.asarray(bits, dtype=np.uint8)
    # Pad to multiple of 8 if necessary
    remainder = len(bits_arr) % 8
    if remainder != 0:
        padding = 8 - remainder
        bits_arr = np.pad(bits_arr, (0, padding), mode="constant", constant_values=0)
    return bytes(np.packbits(bits_arr))


def bpsk_modulate(
    bits: np.ndarray | bytes,
    amplitude: float = 0.8,
    samples_per_symbol: int = 1,
) -> np.ndarray:
    """Modulate a sequence of bits to BPSK complex symbols.

    Mapping:
      Bit 0 -> -1.0 + 0.0j
      Bit 1 -> +1.0 + 0.0j

    Output is scaled to Pluto 16-bit integer DAC dynamic range (+/- 16384 * amplitude).

    Args:
        bits: 1D array of 0s and 1s, or raw bytes.
        amplitude: Normalized amplitude scalar (0.0 to 1.0).
        samples_per_symbol: Number of repeated samples per symbol (oversampling).

    Returns:
        Complex IQ array (np.complex64).
    """
    if isinstance(bits, (bytes, bytearray)):
        bit_array = bytes_to_bits(bits)
    else:
        bit_array = np.asarray(bits, dtype=np.uint8).flatten()

    scale = (2**14 - 1) * float(amplitude)

    # 0 -> -1.0, 1 -> +1.0
    bipolar = np.where(bit_array == 1, 1.0, -1.0)
    symbols = (bipolar * scale + 1j * 0.0).astype(np.complex64)

    if samples_per_symbol > 1:
        symbols = np.repeat(symbols, samples_per_symbol)

    return symbols


def bpsk_demodulate(
    symbols: np.ndarray,
    samples_per_symbol: int = 1,
) -> np.ndarray:
    """Demodulate BPSK complex symbols to binary bits.

    Hard-decision slicing on Real component:
      Re{s} >= 0 -> 1
      Re{s} < 0  -> 0

    Args:
        symbols: Complex IQ input array.
        samples_per_symbol: Downsampling factor if oversampled.

    Returns:
        1D numpy array of uint8 bits (0 or 1).
    """
    sym_arr = np.asarray(symbols, dtype=np.complex64)
    if len(sym_arr) == 0:
        return np.array([], dtype=np.uint8)

    if samples_per_symbol > 1:
        # Sample at symbol midpoint
        midpoint = samples_per_symbol // 2
        sym_arr = sym_arr[midpoint::samples_per_symbol]

    return np.where(np.real(sym_arr) >= 0.0, 1, 0).astype(np.uint8)


def calculate_ber(tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
    """Calculate Bit Error Rate (BER) between transmitted and received bitstreams."""
    t_bits = np.asarray(tx_bits, dtype=np.uint8).flatten()
    r_bits = np.asarray(rx_bits, dtype=np.uint8).flatten()

    min_len = min(len(t_bits), len(r_bits))
    if min_len == 0:
        return 0.0

    errors = np.sum(t_bits[:min_len] != r_bits[:min_len])
    return float(errors) / float(min_len)
