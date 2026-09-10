"""Packet framing, CRC validation, and digital protocol layer."""

from .crc import compute_crc32, verify_crc32
from .frame import build_frame, FrameDetector, PREAMBLE, SYNC_WORD
from .transceiver import DigitalPacketTransceiver, RadioStats

__all__ = [
    "compute_crc32",
    "verify_crc32",
    "build_frame",
    "FrameDetector",
    "PREAMBLE",
    "SYNC_WORD",
    "DigitalPacketTransceiver",
    "RadioStats",
]
