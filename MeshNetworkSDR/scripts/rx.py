#!/usr/bin/env python3
"""Stage 1: RF Receiver Entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pluto_radio.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Pluto SDR RF Receiver (Stage 1)")
    parser.add_argument("--freq", type=int, default=None, help="Carrier frequency in Hz")
    parser.add_argument("--simulation", action="store_true", help="Run in simulation mode")
    args = parser.parse_args()

    config = load_config()
    freq = args.freq or config.radio.center_frequency

    print("================================")
    print("PLUTO SDR RF RECEIVER (STAGE 1)")
    print("================================")
    print(f"Frequency   : {freq:,} Hz")
    print(f"Mode        : {'SIMULATION' if args.simulation else 'HARDWARE'}")
    print("Status      : Ready for Stage 1 implementation")
    print("================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
