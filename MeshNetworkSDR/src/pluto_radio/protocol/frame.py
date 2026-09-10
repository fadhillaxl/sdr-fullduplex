"""Stage 4: Packet Framing, Serialization, and Stream Synchronization."""

from __future__ import annotations

import struct
from typing import Generator, List, Optional, Tuple

from .crc import compute_crc32, verify_crc32


PREAMBLE = b"\xaa\xaa\xaa\xaa"  # 32-bit alternating bit pattern for clock sync
SYNC_WORD = b"\x55\xaa"          # 16-bit unique synchronization marker
HEADER_FORMAT = ">HH"             # (length: uint16, seq: uint16) -> 4 bytes
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
TRAILER_FORMAT = ">I"             # (crc32: uint32) -> 4 bytes
TRAILER_SIZE = struct.calcsize(TRAILER_FORMAT)
MAX_PAYLOAD_SIZE = 1500           # Standard Ethernet MTU


def build_frame(payload: bytes, seq: int = 0) -> bytes:
    """Encapsulate an IP/raw packet into a framed transmission burst.

    Frame format:
      [ PREAMBLE (4B) | SYNC_WORD (2B) | LENGTH (2B) | SEQ (2B) | PAYLOAD (NB) | CRC32 (4B) ]
    """
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload size {len(payload)} exceeds max MTU {MAX_PAYLOAD_SIZE}")

    length = len(payload)
    header = struct.pack(HEADER_FORMAT, length, seq & 0xFFFF)
    protected_data = header + payload
    crc = compute_crc32(protected_data)
    trailer = struct.pack(TRAILER_FORMAT, crc)

    return PREAMBLE + SYNC_WORD + protected_data + trailer


class FrameDetector:
    """Stream correlator that searches for sync markers and extracts verified packets."""

    def __init__(self, max_buffer_size: int = 65536):
        self.buffer = bytearray()
        self.max_buffer_size = max_buffer_size

    def push(self, data: bytes | bytearray) -> None:
        """Append incoming byte stream into the correlator buffer."""
        self.buffer.extend(data)
        if len(self.buffer) > self.max_buffer_size:
            # Prevent runaway buffer growth under heavy noise
            self.buffer = self.buffer[-self.max_buffer_size // 2 :]

    def extract_frames(self) -> Generator[Tuple[int, bytes], None, None]:
        """Extract and yield all complete, CRC-verified packets currently in the buffer."""
        while True:
            # Search for sync word
            sync_idx = self.buffer.find(SYNC_WORD)
            if sync_idx == -1:
                # Keep last byte in case sync word spans boundaries
                if len(self.buffer) > 1:
                    self.buffer = self.buffer[-1:]
                break

            # Discard bytes before sync word
            if sync_idx > 0:
                del self.buffer[:sync_idx]

            # Buffer now starts with SYNC_WORD (2 bytes)
            # Need at least SYNC (2B) + HEADER (4B) to determine frame length
            min_header_needed = len(SYNC_WORD) + HEADER_SIZE
            if len(self.buffer) < min_header_needed:
                break

            # Read payload length and sequence
            length, seq = struct.unpack_from(HEADER_FORMAT, self.buffer, len(SYNC_WORD))
            if length > MAX_PAYLOAD_SIZE:
                # False sync word detection; discard this sync marker and continue
                del self.buffer[: len(SYNC_WORD)]
                continue

            total_frame_len = len(SYNC_WORD) + HEADER_SIZE + length + TRAILER_SIZE
            if len(self.buffer) < total_frame_len:
                # Wait for remainder of packet to arrive
                break

            # Extract protected data and CRC
            protected_start = len(SYNC_WORD)
            protected_end = protected_start + HEADER_SIZE + length
            protected_data = bytes(self.buffer[protected_start:protected_end])

            expected_crc = struct.unpack_from(TRAILER_FORMAT, self.buffer, protected_end)[0]

            if verify_crc32(protected_data, expected_crc):
                payload = protected_data[HEADER_SIZE:]
                del self.buffer[:total_frame_len]
                yield (seq, payload)
            else:
                # CRC failure: false sync or corrupted packet; advance by 1 byte
                del self.buffer[:1]

    def reset(self) -> None:
        """Clear internal stream buffer."""
        self.buffer.clear()
