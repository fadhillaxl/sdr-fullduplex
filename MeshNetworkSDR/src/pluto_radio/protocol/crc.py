"""CRC32 packet integrity validation."""

from __future__ import annotations

import zlib


def compute_crc32(data: bytes | bytearray | memoryview) -> int:
    """Compute 32-bit CRC checksum using standard IEEE 802.3 polynomial."""
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_crc32(data: bytes | bytearray | memoryview, expected_crc: int) -> bool:
    """Verify if the data matches the expected CRC32 value."""
    return compute_crc32(data) == (expected_crc & 0xFFFFFFFF)
