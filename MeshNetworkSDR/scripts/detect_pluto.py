#!/usr/bin/env python3
"""Stage 0: Hardware Detection for ADALM-Pluto / Pluto+ SDR."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ directory is importable
repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pluto_radio.config import load_config
from pluto_radio.hardware.pluto import PlutoDetector


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect connected ADALM-Pluto / Pluto+ SDR hardware.",
    )
    parser.add_argument(
        "--uri",
        type=str,
        default=None,
        help="Pluto SDR URI (e.g. ip:192.168.2.1 or usb:x.y.z)",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--simulation",
        "-s",
        action="store_true",
        help="Run in software simulation mode without physical SDR",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    uri = args.uri or config.radio.uri
    is_simulation = args.simulation

    detector = PlutoDetector(default_uri=uri)
    info = detector.detect(uri=uri, simulation=is_simulation)

    print(info.format_report())
    return 0 if info.status in ("CONNECTED", "SIMULATION") else 1


if __name__ == "__main__":
    sys.exit(main())
