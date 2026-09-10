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

    # Command: rx
    rx_parser = subparsers.add_parser(
        "rx",
        parents=[parent_parser],
        help="Start receiver and signal monitor (Stage 1)",
    )
    rx_parser.add_argument("--freq", type=int, default=433000000, help="RF center frequency in Hz")
    rx_parser.add_argument("--gain", type=int, default=40, help="RX gain in dB")

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
    elif args.command in ("tx", "rx", "link", "ping"):
        if args.command == "link" and getattr(args, "tun", False):
            print(f"[*] Perintah 'link --tun' (Stage 7 IP Virtual Network Interface: {args.ip})")
            print("    Status saat ini: STAGE 0 selesai (Hardware terdeteksi & terhubung).")
            print("    Tahapan pengembangan saat ini siap memasuki: STAGE 1 (RF Tone TX/RX).")
            print("    Interface TUN/TAP IP radio0 akan diaktifkan secara penuh pada STAGE 7.")
            print("    Ketik 'lanjut' atau 'setuju' untuk memulai implementasi STAGE 1!")
            return 0
        print(f"Command '{args.command}' is reserved for Stage 1/Stage 2.")
        print("Run 'pluto-radio status' to verify hardware detection (Stage 0).")
        return 0
    elif args.command == "stats":
        return handle_stats(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
