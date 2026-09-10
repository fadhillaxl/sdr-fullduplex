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
    parent_parser.add_argument(
        "--uri",
        "-u",
        type=str,
        default=None,
        help="Override Pluto SDR URI (e.g. usb:0.3.5 or ip:192.168.2.1)",
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
    link_parser.add_argument("--ip", type=str, default="192.168.50.1/24", help="Virtual IP address for radio0/utun")
    link_parser.add_argument("--peer-ip", type=str, default=None, help="Peer IP address (default: auto-inferred)")
    link_parser.add_argument("--role", choices=["tx", "rx", "loopback"], default="loopback", help="Transceiver role")
    link_parser.add_argument("--data", type=str, default="HELLO RASPBERRY PI", help="Data to transmit")
    link_parser.add_argument("--freq", type=int, default=None, help="Carrier frequency in Hz (default: 433000000)")
    link_parser.add_argument("--tx-freq", type=int, default=None, help="Custom TX carrier frequency in Hz")
    link_parser.add_argument("--rx-freq", type=int, default=None, help="Custom RX carrier frequency in Hz")
    link_parser.add_argument("--tx-gain", type=int, default=None, help="TX attenuation in dB (default: -5 dB for strong signal)")
    link_parser.add_argument("--rx-gain", type=int, default=None, help="RX hardware gain in dB (default: 50 dB)")
    link_parser.add_argument("--fdd", action="store_true", help="Enable FDD Full-Duplex (split TX/RX frequencies between nodes)")
    link_parser.add_argument("--node-id", type=int, default=None, help="Local node ID (default: auto-inferred from IP)")
    link_parser.add_argument("--peer-node-id", type=int, default=None, help="Peer node ID (default: auto-inferred from peer IP)")
    link_parser.add_argument("--modulation", choices=["bpsk", "qpsk"], default="bpsk", help="Digital modulation mode")
    link_parser.add_argument("--duration", type=float, default=None, help="Duration in seconds (default: continuous)")

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


def handle_link(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    if not getattr(args, "tun", False):
        print("Command 'link' is reserved for Stage 2/Stage 5.")
        print("To start the Stage 7 Virtual TUN/TAP IP Network Interface, run with:")
        print(f"    sudo pluto-radio link --tun --ip {getattr(args, 'ip', '192.168.50.1/24')}")
        return 0

    from .hardware.pluto import PlutoTransceiver
    from .network.tun import create_tun_device
    from .protocol.transceiver import DigitalPacketTransceiver
    import time

    ip_cidr = getattr(args, "ip", "192.168.50.1/24")
    peer_ip = getattr(args, "peer_ip", None)
    freq = getattr(args, "freq", None) or config.radio.center_frequency
    modulation = getattr(args, "modulation", None) or config.modulation.mode
    is_sim = args.simulation or config.debug.simulation_mode

    tun_dev = None
    modem = None

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )

    try:
        # Create TUN interface first to obtain assigned local and peer IPs
        tun_dev = create_tun_device(
            ip_cidr=ip_cidr,
            peer_ip=peer_ip,
            simulation=is_sim,
        )
        tun_dev.open()

        node_id = getattr(args, "node_id", None)
        if node_id is None:
            try:
                node_id = int(tun_dev.local_ip.split(".")[-1])
            except Exception:
                node_id = 1

        peer_node_id = getattr(args, "peer_node_id", None)
        if peer_node_id is None:
            try:
                peer_node_id = int(tun_dev.peer_ip.split(".")[-1])
            except Exception:
                peer_node_id = 2 if node_id == 1 else 1

        # Resolve TX/RX frequencies (FDD full-duplex vs TDD single-frequency)
        base_freq = getattr(args, "freq", None) or config.radio.center_frequency
        tx_freq = getattr(args, "tx_freq", None)
        rx_freq = getattr(args, "rx_freq", None)

        if tx_freq is None or rx_freq is None:
            if getattr(args, "fdd", False):
                # Frequency Division Duplex (2 MHz channel separation)
                if node_id == 1:
                    tx_freq = tx_freq or base_freq
                    rx_freq = rx_freq or (base_freq + 2_000_000)
                else:
                    tx_freq = tx_freq or (base_freq + 2_000_000)
                    rx_freq = rx_freq or base_freq
            else:
                tx_freq = tx_freq or base_freq
                rx_freq = rx_freq or base_freq

        tx_gain = getattr(args, "tx_gain", None)
        if tx_gain is None:
            tx_gain = -6  # Safe linear transmit power to prevent near-field distortion

        rx_gain = getattr(args, "rx_gain", None)
        if rx_gain is None:
            rx_gain = 50  # Balanced RX gain (prevents AD9361 ADC 0 dBFS saturation on desk)

        trx = PlutoTransceiver(
            uri=args.uri,
            simulation=is_sim,
            sample_rate=config.radio.sample_rate,
        )
        trx.configure_tx(freq_hz=tx_freq, gain_db=tx_gain, rf_bandwidth=config.radio.bandwidth)
        trx.configure_rx(freq_hz=rx_freq, gain_db=rx_gain, rf_bandwidth=config.radio.bandwidth)

        duplex_label = "FDD (Full Duplex - Split Freq)" if tx_freq != rx_freq else "TDD (Single Freq - Echo Filtered)"

        print("================================")
        print("PLUTO SDR IP RADIO LINK (STAGE 7)")
        print("================================")
        print(f"Interface   : {tun_dev.name}")
        print(f"Local Node  : {tun_dev.local_ip} (Node {node_id})")
        print(f"Peer Node   : {tun_dev.peer_ip} (Node {peer_node_id})")
        print(f"TX Freq     : {tx_freq:,} Hz (Gain: {tx_gain} dB)")
        print(f"RX Freq     : {rx_freq:,} Hz (Gain: {rx_gain} dB)")
        print(f"Duplex Mode : {duplex_label}")
        print(f"Modulation  : {modulation.upper()}")
        print(f"Device URI  : {trx.uri}")
        print(f"Mode        : {'SIMULATION' if trx.simulation else 'HARDWARE'}")
        print("================================\n")
        print("[*] Virtual IP network interface is ACTIVE!")
        print("[*] To test IP ping in another terminal, run:")
        print(f"    ping {tun_dev.peer_ip}\n")
        print("[*] Streaming telemetry (Press Ctrl+C to stop)...\n")

        modem = DigitalPacketTransceiver(
            tun=tun_dev,
            sdr=trx,
            modulation=modulation,
            node_id=node_id,
            peer_node_id=peer_node_id,
        )
        modem.start()

        duration = getattr(args, "duration", None)
        start_time = time.time()
        last_report = time.time()

        while True:
            time.sleep(1.0)
            now = time.time()
            if now - last_report >= 5.0:
                last_report = now
                print(modem.stats.format_telemetry())
                print()
            if duration is not None and (now - start_time) >= duration:
                break

    except KeyboardInterrupt:
        print("\n[!] Stopping IP link transceiver...")
    except PermissionError:
        print(f"\n[ERROR] Permission denied: Root/sudo privileges required to configure virtual TUN interface.")
        print(f"        Please run with sudo: sudo {' '.join(sys.argv)}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Link failed: {e}", file=sys.stderr)
        return 1
    finally:
        if modem is not None:
            modem.stop()
        elif tun_dev is not None:
            tun_dev.close()

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
    elif args.command == "link":
        return handle_link(args)
    elif args.command == "ping":
        print(f"Command '{args.command}' is reserved for Stage 2/Stage 5.")
        print("Run 'pluto-radio link --tun' to start IP link and use system 'ping' command.")
        return 0
    elif args.command == "stats":
        return handle_stats(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

