#!/usr/bin/env python3
"""Stage 1/5: Full Link Transceiver Entrypoint."""

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
    parser = argparse.ArgumentParser(description="Pluto SDR Full Link Transceiver (Stage 1/5)")
    parser.add_argument("--simulation", action="store_true", help="Run in loopback simulation mode")
    args = parser.parse_args()

    config = load_config()
    print("================================")
    print("PLUTO SDR LINK TRANSCEIVER")
    print("================================")
    print(f"Center Freq : {config.radio.center_frequency:,} Hz")
    print(f"Sample Rate : {config.radio.sample_rate:,} SPS")
    print(f"Bandwidth   : {config.radio.bandwidth:,} Hz")
    print(f"Mode        : {'SIMULATION' if args.simulation or config.debug.simulation_mode else 'HARDWARE'}")
    print("Status      : Ready for Stage 1/5 implementation")
    print("================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
