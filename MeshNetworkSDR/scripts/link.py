#!/usr/bin/env python3
"""Stage 1/5/7: Full Link Transceiver Entrypoint."""

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
    parser = argparse.ArgumentParser(description="Pluto SDR Full Link Transceiver (Stage 1/5/7)")
    parser.add_argument("--role", choices=["tx", "rx", "loopback"], default="loopback", help="Transceiver role (tx/rx/loopback)")
    parser.add_argument("--data", type=str, default="HELLO PLUTO SDR", help="Payload message to transmit")
    parser.add_argument("--freq", type=int, default=None, help="Carrier frequency in Hz (default: 433000000)")
    parser.add_argument("--gain", type=int, default=None, help="Hardware gain in dB")
    parser.add_argument("--tun", action="store_true", help="Enable TUN/TAP virtual network interface (Stage 7)")
    parser.add_argument("--ip", type=str, default="192.168.50.1/24", help="Virtual IP for radio0 (Stage 7)")
    parser.add_argument("--duration", type=float, default=None, help="Duration in seconds (default: continuous)")
    parser.add_argument("--uri", type=str, default=None, help="Pluto SDR URI override")
    parser.add_argument("--simulation", action="store_true", help="Run in simulation mode")
    args = parser.parse_args()

    config = load_config()
    freq = args.freq or config.radio.center_frequency
    is_sim = args.simulation or config.debug.simulation_mode

    try:
        trx = PlutoTransceiver(
            uri=args.uri,
            simulation=is_sim,
            sample_rate=config.radio.sample_rate,
        )

        print("================================")
        print(f"PLUTO SDR LINK TRANSCEIVER ({args.role.upper()})")
        print("================================")
        print(f"Center Freq : {freq:,} Hz")
        print(f"Sample Rate : {config.radio.sample_rate:,} SPS")
        print(f"Role        : {args.role}")
        if args.role in ("tx", "loopback"):
            print(f"Payload     : \"{args.data}\"")
        if args.tun:
            print(f"Virtual IP  : {args.ip} (radio0)")
        print(f"Device URI  : {trx.uri}")
        print(f"Mode        : {'SIMULATION' if trx.simulation else 'HARDWARE'}")
        print("================================\n")

        if args.tun:
            print(f"[*] Mode virtual TUN/TAP ({args.ip}) disiapkan untuk Stage 7.")
            print("    Status saat ini: Stage 1 (RF Tone & Signal Measurement).")

        start_time = time.time()
        if args.role == "tx":
            gain = args.gain if args.gain is not None else config.radio.tx_gain
            trx.configure_tx(freq_hz=freq, gain_db=gain)
            trx.start_tone_tx(tone_freq_hz=100000.0, amplitude=0.8)
            print(f"[TX] Transmitting Stage 1 carrier signal on {freq/1e6:.3f} MHz...")
            print(f"     Payload: \"{args.data}\" (Digital QPSK packet framing active in Stage 3-5)")
            print("     Press Ctrl+C to stop.\n")
            while True:
                time.sleep(1.0)
                if args.duration is not None and (time.time() - start_time) >= args.duration:
                    break

        elif args.role == "rx":
            gain = args.gain if args.gain is not None else config.radio.rx_gain
            trx.configure_rx(freq_hz=freq, gain_db=gain)
            print(f"[RX] Listening on {freq/1e6:.3f} MHz (Stage 1 Signal & Power Monitor)...")
            print("     Press Ctrl+C to stop.\n")
            while True:
                samples = trx.receive_iq(10000)
                metrics = compute_rf_metrics(samples, sample_rate=config.radio.sample_rate)
                print(metrics.format_report())
                print()
                time.sleep(1.0)
                if args.duration is not None and (time.time() - start_time) >= args.duration:
                    break

        else:  # loopback
            print("[LOOPBACK] Initialized transceiver in loopback verification mode.")
            samples = trx.receive_iq(10000)
            metrics = compute_rf_metrics(samples, sample_rate=config.radio.sample_rate)
            print(metrics.format_report())

    except KeyboardInterrupt:
        print("\n[!] Stopping transceiver...")
    except Exception as e:
        print(f"\n[ERROR] Transceiver error: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            trx.stop_tx()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())

