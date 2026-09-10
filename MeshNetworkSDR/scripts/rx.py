#!/usr/bin/env python3
"""Stage 1: RF Receiver Entrypoint."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pluto_radio.config import load_config
from pluto_radio.dsp.rf_metrics import compute_rf_metrics
from pluto_radio.hardware.pluto import PlutoTransceiver


def main() -> int:
    parser = argparse.ArgumentParser(description="Pluto SDR RF Receiver (Stage 1)")
    parser.add_argument("--freq", type=int, default=None, help="Carrier frequency in Hz (default: 433000000)")
    parser.add_argument("--gain", type=int, default=None, help="RX hardware gain in dB (default: 40)")
    parser.add_argument("--rate", type=int, default=None, help="Sample rate in SPS (default: 1000000)")
    parser.add_argument("--count", type=int, default=None, help="Number of measurements to take (default: continuous)")
    parser.add_argument("--interval", type=float, default=0.5, help="Update interval in seconds (default: 0.5)")
    parser.add_argument("--uri", type=str, default=None, help="Pluto SDR URI override")
    parser.add_argument("--simulation", action="store_true", help="Run in simulation mode")
    args = parser.parse_args()

    config = load_config()
    freq = args.freq or config.radio.center_frequency
    gain = args.gain if args.gain is not None else config.radio.rx_gain
    sample_rate = args.rate or config.radio.sample_rate
    is_sim = args.simulation or config.debug.simulation_mode

    try:
        trx = PlutoTransceiver(
            uri=args.uri,
            simulation=is_sim,
            sample_rate=sample_rate,
        )

        print("================================")
        print("PLUTO SDR RF RECEIVER (STAGE 1)")
        print("================================")
        print(f"Carrier Freq : {freq:,} Hz")
        print(f"RX Gain      : {gain} dB")
        print(f"Sample Rate  : {sample_rate:,} SPS")
        print(f"Device URI   : {trx.uri}")
        print(f"Mode         : {'SIMULATION' if trx.simulation else 'HARDWARE'}")
        print("================================\n")

        trx.configure_rx(freq_hz=freq, gain_db=gain, rf_bandwidth=config.radio.bandwidth)

        measured = 0
        while True:
            samples = trx.receive_iq(10000)
            metrics = compute_rf_metrics(samples, sample_rate=sample_rate)

            print(metrics.format_report())
            print()
            measured += 1

            if args.count is not None and measured >= args.count:
                break
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("[!] Stopping receiver...")
    except Exception as e:
        print(f"\n[ERROR] Receiver failed: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

