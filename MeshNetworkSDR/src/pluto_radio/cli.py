"""Command-line interface for Pluto+ SDR IP Radio."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .config import load_config
from .hardware.pluto import PlutoDetector


def build_parser() -> argparse.ArgumentParser:
    # Shared parent parser for common options
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to YAML configuration file (default: config/radio.yaml)",
    )
    parent_parser.add_argument(
        "--simulation",
        "-s",
        action="store_true",
        help="Force simulation mode without physical hardware",
    )

    parser = argparse.ArgumentParser(
        prog="pluto-radio",
        description="Pluto+ SDR Short-Range IP Radio & Modem CLI",
        parents=[parent_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: status
    status_parser = subparsers.add_parser(
        "status",
        parents=[parent_parser],
        help="Detect and report Pluto SDR hardware status",
    )
    status_parser.add_argument("--uri", type=str, default=None, help="Override Pluto URI (e.g. ip:192.168.2.1)")

    # Command: tx
    tx_parser = subparsers.add_parser(
        "tx",
        parents=[parent_parser],
        help="Start transmitter (Stage 1)",
    )
    tx_parser.add_argument("--tone", action="store_true", help="Transmit continuous test tone")
    tx_parser.add_argument("--freq", type=int, default=433000000, help="RF center frequency in Hz")
    tx_parser.add_argument("--gain", type=int, default=-20, help="TX attenuation in dB")

    tx_parser.add_argument("--duration", type=float, default=None, help="Duration in seconds")

    # Command: rx
    rx_parser = subparsers.add_parser(
        "rx",
        parents=[parent_parser],
        help="Start receiver and signal monitor (Stage 1)",
    )
    rx_parser.add_argument("--freq", type=int, default=433000000, help="RF center frequency in Hz")
    rx_parser.add_argument("--gain", type=int, default=40, help="RX gain in dB")
    rx_parser.add_argument("--count", type=int, default=None, help="Number of measurements to take")
    rx_parser.add_argument("--interval", type=float, default=0.5, help="Update interval in seconds")

    # Command: link
    link_parser = subparsers.add_parser(
        "link",
        parents=[parent_parser],
        help="Start full transceiver link (Stage 1/5/7)",
    )
    link_parser.add_argument("--tun", action="store_true", help="Enable TUN/TAP virtual network interface (Stage 7)")
    link_parser.add_argument("--ip", type=str, default="192.168.50.1/24", help="Virtual IP address for radio0")
    link_parser.add_argument("--role", choices=["tx", "rx", "loopback"], default="loopback", help="Transceiver role")
    link_parser.add_argument("--data", type=str, default="HELLO RASPBERRY PI", help="Data to transmit")

    # Command: ping
    ping_parser = subparsers.add_parser(
        "ping",
        parents=[parent_parser],
        help="Send test RF packet (Stage 2/5)",
    )
    ping_parser.add_argument("target", nargs="?", default="192.168.50.2", help="Target node address")

    # Command: stats
    stats_parser = subparsers.add_parser(
        "stats",
        parents=[parent_parser],
        help="Show link telemetry and statistics",
    )

    return parser


def handle_status(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    uri = args.uri or config.radio.uri
    is_simulation = args.simulation or config.debug.simulation_mode

    detector = PlutoDetector(default_uri=uri)
    info = detector.detect(uri=uri, simulation=args.simulation)

    print(info.format_report())
    return 0 if info.status in ("CONNECTED", "SIMULATION") else 2


def handle_tx(args: argparse.Namespace) -> int:
    from .hardware.pluto import PlutoTransceiver
    import time
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    freq = getattr(args, "freq", None) or config.radio.center_frequency
    gain = getattr(args, "gain", None)
    if gain is None:
        gain = config.radio.tx_gain
    sample_rate = config.radio.sample_rate
    is_sim = args.simulation or config.debug.simulation_mode

    print("================================")
    print("PLUTO SDR RF TRANSMITTER (STAGE 1)")
    print("================================")
    print(f"Carrier Freq : {freq:,} Hz")
    print(f"TX Gain      : {gain} dB")
    print(f"Sample Rate  : {sample_rate:,} SPS")
    print(f"Mode         : {'SIMULATION' if is_sim else 'HARDWARE'}")
    print("================================")

    try:
        trx = PlutoTransceiver(
            uri=config.radio.uri,
            simulation=is_sim,
            sample_rate=sample_rate,
        )
        trx.configure_tx(freq_hz=freq, gain_db=gain)
        trx.start_tone_tx(tone_freq_hz=100000.0, amplitude=0.8)
        print(f"[+] Transmitting continuous CW tone at {freq/1e6:.3f} MHz...")
        print("    Press Ctrl+C to stop.\n")

        duration = getattr(args, "duration", None)
        start_time = time.time()
        while True:
            time.sleep(0.5)
            if duration is not None and (time.time() - start_time) >= duration:
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


def handle_rx(args: argparse.Namespace) -> int:
    from .hardware.pluto import PlutoTransceiver
    from .dsp.rf_metrics import compute_rf_metrics
    import time
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    freq = getattr(args, "freq", None) or config.radio.center_frequency
    gain = getattr(args, "gain", None)
    if gain is None:
        gain = config.radio.rx_gain
    sample_rate = config.radio.sample_rate
    is_sim = args.simulation or config.debug.simulation_mode

    print("================================")
    print("PLUTO SDR RF RECEIVER (STAGE 1)")
    print("================================")
    print(f"Carrier Freq : {freq:,} Hz")
    print(f"RX Gain      : {gain} dB")
    print(f"Sample Rate  : {sample_rate:,} SPS")
    print(f"Mode         : {'SIMULATION' if is_sim else 'HARDWARE'}")
    print("================================\n")

    try:
        trx = PlutoTransceiver(
            uri=config.radio.uri,
            simulation=is_sim,
            sample_rate=sample_rate,
        )
        trx.configure_rx(freq_hz=freq, gain_db=gain)

        count = getattr(args, "count", None)
        interval = getattr(args, "interval", 0.5)
        measured = 0
        while True:
            samples = trx.receive_iq(10000)
            metrics = compute_rf_metrics(samples, sample_rate=sample_rate)
            print(metrics.format_report())
            print()
            measured += 1
            if count is not None and measured >= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[!] Stopping receiver...")
    except Exception as e:
        print(f"\n[ERROR] Receiver failed: {e}", file=sys.stderr)
        return 1

    return 0


def handle_stats(args: argparse.Namespace) -> int:
    print("--------------------------------")
    print("PLUTO RADIO TELEMETRY (BASELINE)")
    print("--------------------------------")
    print("RSSI       : - dBFS")
    print("SNR        : - dB")
    print("EVM        : - %")
    print("CFO        : - Hz")
    print("")
    print("TX packets : 0")
    print("RX packets : 0")
    print("CRC errors : 0")
    print("PER        : 0.0 %")
    print("")
    print("Throughput : 0 kbps")
    print("Latency    : - ms")
    print("--------------------------------")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "status":
        return handle_status(args)
    elif args.command == "tx":
        return handle_tx(args)
    elif args.command == "rx":
        return handle_rx(args)
    elif args.command in ("link", "ping"):
        if args.command == "link" and getattr(args, "tun", False):
            print(f"[*] Perintah 'link --tun' (Stage 7 IP Virtual Network Interface: {args.ip})")
            print("    Status saat ini: STAGE 0 selesai (Hardware terdeteksi & terhubung).")
            print("    Tahapan pengembangan saat ini siap memasuki: STAGE 1 (RF Tone TX/RX).")
            print("    Interface TUN/TAP IP radio0 akan diaktifkan secara penuh pada STAGE 7.")
            print("    Ketik 'lanjut' atau 'setuju' untuk memulai implementasi STAGE 1!")
            return 0
        print(f"Command '{args.command}' is reserved for Stage 2/Stage 5.")
        print("Run 'pluto-radio tx' and 'pluto-radio rx' to test RF transmission (Stage 1).")
        return 0
    elif args.command == "stats":
        return handle_stats(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

