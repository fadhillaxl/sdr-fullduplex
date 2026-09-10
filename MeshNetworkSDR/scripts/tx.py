#!/usr/bin/env python3
"""Stage 1: RF Transmitter Entrypoint."""

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
from pluto_radio.hardware.pluto import PlutoTransceiver


def main() -> int:
    parser = argparse.ArgumentParser(description="Pluto SDR RF Transmitter (Stage 1)")
    parser.add_argument("--tone", action="store_true", default=True, help="Send continuous test tone")
    parser.add_argument("--freq", type=int, default=None, help="Carrier frequency in Hz (default: 433000000)")
    parser.add_argument("--tone-freq", type=float, default=100000.0, help="Test tone baseband frequency in Hz (default: 100000)")
    parser.add_argument("--gain", type=int, default=None, help="TX attenuation in dB (e.g. -20)")
    parser.add_argument("--rate", type=int, default=None, help="Sample rate in SPS (default: 1000000)")
    parser.add_argument("--duration", type=float, default=None, help="Duration in seconds (default: continuous until Ctrl+C)")
    parser.add_argument("--uri", type=str, default=None, help="Pluto SDR URI override")
    parser.add_argument("--simulation", action="store_true", help="Run in simulation mode")
    args = parser.parse_args()

    config = load_config()
    freq = args.freq or config.radio.center_frequency
    gain = args.gain if args.gain is not None else config.radio.tx_gain
    sample_rate = args.rate or config.radio.sample_rate
    is_sim = args.simulation or config.debug.simulation_mode

    print("================================")
    print("PLUTO SDR RF TRANSMITTER (STAGE 1)")
    print("================================")
    print(f"Carrier Freq : {freq:,} Hz")
    print(f"Tone Offset  : {args.tone_freq:,.0f} Hz")
    print(f"TX Gain      : {gain} dB")
    print(f"Sample Rate  : {sample_rate:,} SPS")
    print(f"Mode         : {'SIMULATION' if is_sim else 'HARDWARE'}")
    print("================================")

    try:
        trx = PlutoTransceiver(
            uri=args.uri or config.radio.uri,
            simulation=is_sim,
            sample_rate=sample_rate,
        )
        trx.configure_tx(freq_hz=freq, gain_db=gain, rf_bandwidth=config.radio.bandwidth)
        trx.start_tone_tx(tone_freq_hz=args.tone_freq, amplitude=0.8)
        print(f"[+] Transmitting continuous CW tone at {freq/1e6:.3f} MHz...")
        print("    Press Ctrl+C to stop.\n")

        start_time = time.time()
        while True:
            time.sleep(0.5)
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                break
    except KeyboardInterrupt:
        print("\n[!] Stopping transmitter...")
    except Exception as e:
        print(f"\n[ERROR] Failed to start transmitter: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            trx.stop_tx()
            print("[+] RF Transmitter stopped cleanly.")
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())

