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
            from pluto_radio.network.tun import create_tun_device
            from pluto_radio.protocol.transceiver import DigitalPacketTransceiver

            tun_dev = create_tun_device(ip_cidr=args.ip, simulation=trx.simulation)
            tun_dev.open()
            print(f"[*] Virtual TUN network interface active: {tun_dev.name} ({tun_dev.local_ip} -> {tun_dev.peer_ip})")
            print(f"[*] Run 'ping {tun_dev.peer_ip}' in another terminal to test.\n")

            modem = DigitalPacketTransceiver(tun=tun_dev, sdr=trx, modulation=config.modulation.mode)
            modem.start()

            start_time = time.time()
            last_rep = time.time()
            while True:
                time.sleep(1.0)
                now = time.time()
                if now - last_rep >= 5.0:
                    last_rep = now
                    print(modem.stats.format_telemetry())
                    print()
                if args.duration is not None and (now - start_time) >= args.duration:
                    break

        elif args.role == "tx":
            from pluto_radio.protocol.frame import build_frame
            from pluto_radio.dsp.bpsk import bpsk_modulate

            gain = args.gain if args.gain is not None else config.radio.tx_gain
            trx.configure_tx(freq_hz=freq, gain_db=gain)

            payload = args.data.encode("utf-8")
            frame = build_frame(payload, seq=1)
            iq_burst = bpsk_modulate(frame, amplitude=0.8, samples_per_symbol=4)

            print(f"[TX] Transmitting digital packet burst on {freq/1e6:.3f} MHz...")
            print(f"     Payload: \"{args.data}\" ({len(payload)} bytes, {len(frame)} frame bytes, {len(iq_burst)} IQ samples)")
            print("     Press Ctrl+C to stop.\n")

            start_time = time.time()
            seq = 1
            while True:
                frame = build_frame(payload, seq=seq)
                iq_burst = bpsk_modulate(frame, amplitude=0.8, samples_per_symbol=4)
                trx.sdr.tx(iq_burst)
                seq = (seq + 1) & 0xFFFF
                time.sleep(0.5)
                if args.duration is not None and (time.time() - start_time) >= args.duration:
                    break

        elif args.role == "rx":
            from pluto_radio.protocol.frame import FrameDetector
            from pluto_radio.dsp.bpsk import bpsk_demodulate, bits_to_bytes

            gain = args.gain if args.gain is not None else config.radio.rx_gain
            trx.configure_rx(freq_hz=freq, gain_db=gain)
            print(f"[RX] Listening for digital packets on {freq/1e6:.3f} MHz...")
            print("     Press Ctrl+C to stop.\n")

            detector = FrameDetector()
            start_time = time.time()
            while True:
                samples = trx.receive_iq(16384)
                if len(samples) > 0:
                    bits = bpsk_demodulate(samples, samples_per_symbol=4)
                    detector.push(bits_to_bytes(bits))
                    for seq, pkt_data in detector.extract_frames():
                        metrics = compute_rf_metrics(samples, sample_rate=config.radio.sample_rate)
                        try:
                            text = pkt_data.decode("utf-8", errors="replace")
                        except Exception:
                            text = repr(pkt_data)
                        print(f"[RX Packet #{seq}] {len(pkt_data)} bytes | SNR: {metrics.snr_db:.1f} dB | Payload: \"{text}\"")

                time.sleep(0.1)
                if args.duration is not None and (time.time() - start_time) >= args.duration:
                    break

        else:  # loopback
            from pluto_radio.protocol.frame import build_frame, FrameDetector
            from pluto_radio.dsp.bpsk import bpsk_modulate, bpsk_demodulate, bits_to_bytes

            print("[LOOPBACK] Testing digital packet modulation and frame detection loopback...")
            payload = args.data.encode("utf-8")
            frame = build_frame(payload, seq=42)
            iq_burst = bpsk_modulate(frame, amplitude=0.8, samples_per_symbol=4)

            trx.sdr.tx(iq_burst)
            rx_samples = trx.receive_iq(len(iq_burst))
            rx_bits = bpsk_demodulate(rx_samples, samples_per_symbol=4)
            detector = FrameDetector()
            detector.push(bits_to_bytes(rx_bits))

            extracted = list(detector.extract_frames())
            if extracted:
                seq, dec_data = extracted[0]
                print(f"[SUCCESS] Loopback verified! Packet #{seq}: \"{dec_data.decode('utf-8')}\"")
            else:
                print("[!] No packet recovered in loopback.")

    except KeyboardInterrupt:
        print("\n[!] Stopping transceiver...")
    except Exception as e:
        print(f"\n[ERROR] Transceiver error: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            if "modem" in locals() and modem is not None:
                modem.stop()
            if "tun_dev" in locals() and tun_dev is not None:
                tun_dev.close()
            trx.stop_tx()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())

