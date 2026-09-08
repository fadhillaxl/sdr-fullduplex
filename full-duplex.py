#!/usr/bin/env python3
"""
PlutoSDR Full-Duplex Text Messenger (Transceiver)
Mendukung pengiriman dan penerimaan pesan teks secara simultan (Full-Duplex)
menggunakan modulasi FSK (Frequency Shift Keying) dengan verifikasi CRC16.
"""

import sys
import os
import time
import struct
import threading
import argparse
import collections
import numpy as np

try:
    import iio
    import adi
except ImportError:
    print("[!] Error: Modul 'iio' atau 'adi' tidak ditemukan.")
    print("    Pastikan Anda sudah mengaktifkan virtual environment:")
    print("    source .venv/bin/activate")
    sys.exit(1)

# ================= Konfigurasi Protokol =================
PREAMBLE = b'\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa'  # 8 byte preamble untuk sinkronisasi
SYNC_WORD = b'\x2d\xd4'                         # 16-bit Sync Word (0x2DD4)
SAMPLE_RATE = int(1e6)                          # 1 MSps (aman untuk USB 2.0 & LAN)
BAUD_RATE = 20000                               # 20 kBaud (20 kbps)
F_DEV = 35000                                   # Deviasi frekuensi FSK (±35 kHz)
SAMPLES_PER_SYMBOL = int(SAMPLE_RATE / BAUD_RATE)  # 50 sampel/simbol
RX_BUFFER_SIZE = 32768                          # Ukuran buffer RX per panggilan

# ================= Fungsi Utilitas CRC & Paket =================
def crc16(data: bytes) -> int:
    """Menghitung CRC16-CCITT (Poly 0x1021, Init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))

def bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()

def create_packet(message: str, seq: int = 0) -> bytes:
    """
    Struktur Paket:
    [PREAMBLE (8B)] [SYNC_WORD (2B)] [SEQ (1B)] [PAYLOAD_LEN (1B)] [PAYLOAD] [CRC16 (2B)]
    """
    payload = message.encode('utf-8')
    if len(payload) > 250:
        payload = payload[:250]
    header = struct.pack('!BB', seq & 0xFF, len(payload))
    crc = struct.pack('!H', crc16(payload))
    return PREAMBLE + SYNC_WORD + header + payload + crc

def modulate_fsk(packet_bytes: bytes) -> np.ndarray:
    """Mengubah byte paket menjadi sinyal kompleks IQ FSK."""
    bits = bytes_to_bits(packet_bytes)
    freq_dev = np.where(bits == 1, F_DEV, -F_DEV)
    freq_series = np.repeat(freq_dev, SAMPLES_PER_SYMBOL)
    phase = 2 * np.pi * np.cumsum(freq_series) / SAMPLE_RATE
    iq = np.exp(1j * phase).astype(np.complex64)
    
    # Tambahkan ramp-up dan ramp-down dengan sedikit silence
    silence = np.zeros(200, dtype=np.complex64)
    iq_signal = np.concatenate([silence, iq, silence])
    
    # Skalakan ke rentang 14-bit DAC PlutoSDR (~12000 dari max 32767)
    return (iq_signal * 12000).astype(np.complex64)

def demodulate_fsk_stream(iq_samples: np.ndarray):
    """
    Demodulasi diskriminator kuadratur (FM demod) + filter + sinkronisasi framing.
    Mengembalikan daftar tuple: (message_str, seq_num, crc_val)
    """
    if len(iq_samples) < SAMPLES_PER_SYMBOL * 20:
        return []

    # Diskriminator FM: selisih fase sampel berturutan
    diff = iq_samples[1:] * np.conj(iq_samples[:-1])
    inst_freq = np.angle(diff)

    # Matched filter / moving average
    kernel = np.ones(SAMPLES_PER_SYMBOL, dtype=np.float32) / SAMPLES_PER_SYMBOL
    filtered = np.convolve(inst_freq, kernel, mode='same')

    # Hard decision slicer
    hard_bits = (filtered > 0).astype(np.uint8)

    sync_bits = bytes_to_bits(SYNC_WORD)
    sync_len = len(sync_bits)
    sync_str = ''.join(map(str, sync_bits))

    found_messages = []

    # Periksa setiap kemungkinan offset clock simbol
    for phase_offset in range(0, SAMPLES_PER_SYMBOL, max(1, SAMPLES_PER_SYMBOL // 8)):
        decimated_bits = hard_bits[phase_offset::SAMPLES_PER_SYMBOL]
        if len(decimated_bits) < sync_len + 16:
            continue

        bit_str = ''.join(map(str, decimated_bits))
        idx = 0
        while True:
            pos = bit_str.find(sync_str, idx)
            if pos == -1:
                break
            idx = pos + 1

            start_header = pos + sync_len
            if len(decimated_bits) - start_header < 16:
                continue

            header_bits = decimated_bits[start_header:start_header + 16]
            header_bytes = bits_to_bytes(header_bits)
            seq, payload_len = struct.unpack('!BB', header_bytes)

            total_needed_bits = 16 + payload_len * 8 + 16
            if len(decimated_bits) - start_header < total_needed_bits:
                continue

            payload_bits = decimated_bits[start_header + 16 : start_header + 16 + payload_len * 8]
            crc_bits = decimated_bits[start_header + 16 + payload_len * 8 : start_header + total_needed_bits]

            payload_bytes = bits_to_bytes(payload_bits)
            rx_crc = struct.unpack('!H', bits_to_bytes(crc_bits))[0]

            if rx_crc == crc16(payload_bytes):
                try:
                    text = payload_bytes.decode('utf-8', errors='ignore')
                    found_messages.append((text, seq, rx_crc))
                except Exception:
                    pass
    return found_messages

# ================= Deteksi PlutoSDR URI =================
def find_pluto_uri(target_ip=None):
    if hasattr(iio, "scan_contexts"):
        discovered = iio.scan_contexts()
    elif hasattr(iio, "ScanContext"):
        scan_ctx = iio.ScanContext()
        discovered = scan_ctx.get_info()
    else:
        discovered = {}

    if discovered:
        for uri, desc in discovered.items():
            print(f"[*] Ditemukan perangkat: {desc} -> {uri}")
            if target_ip and target_ip in uri:
                return uri
            if "usb:" in uri:
                return uri

    candidate_ips = [target_ip] if target_ip else ["192.168.2.1", "192.168.1.10"]
    for ip in filter(None, candidate_ips):
        test_uri = f"ip:{ip}"
        try:
            ctx = iio.Context(test_uri)
            if any("ad9361" in dev.name for dev in ctx.devices):
                return test_uri
        except Exception:
            continue
    return None

# ================= Kelas Full-Duplex Messenger =================
class PlutoMessenger:
    def __init__(self, uri, tx_freq, rx_freq, tx_gain=-10, rx_gain=40):
        self.uri = uri
        self.tx_freq = int(tx_freq)
        self.rx_freq = int(rx_freq)
        self.tx_gain = tx_gain
        self.rx_gain = rx_gain
        self.running = False
        self.seq_num = 0
        self.recent_crcs = collections.deque(maxlen=100)
        self.recent_times = collections.deque(maxlen=100)
        self.sdr_lock = threading.Lock()

        print(f"\n[+] Menginisialisasi PlutoSDR di {uri}...")
        self.sdr = adi.Pluto(uri)

        # Konfigurasi Radio
        self.sdr.sample_rate = SAMPLE_RATE
        self.sdr.tx_rf_bandwidth = int(SAMPLE_RATE * 0.8)
        self.sdr.rx_rf_bandwidth = int(SAMPLE_RATE * 0.8)
        self.sdr.tx_lo = self.tx_freq
        self.sdr.rx_lo = self.rx_freq
        self.sdr.tx_hardwaregain_chan0 = int(self.tx_gain)
        self.sdr.rx_hardwaregain_chan0 = int(self.rx_gain)
        self.sdr.rx_buffer_size = RX_BUFFER_SIZE
        self.sdr.tx_cyclic_buffer = False

        print(f"    TX LO: {self.tx_freq / 1e6:.3f} MHz | Gain: {self.tx_gain} dB")
        print(f"    RX LO: {self.rx_freq / 1e6:.3f} MHz | Gain: {self.rx_gain} dB")
        print(f"    Modulasi: 2-FSK ({BAUD_RATE/1000:.0f} kbps, dev ±{F_DEV/1000:.0f} kHz)")

    def start(self):
        self.running = True
        self.rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
        self.rx_thread.start()

    def stop(self):
        self.running = False
        time.sleep(0.2)

    def send_message(self, text: str):
        """Modulasi dan transmisi pesan teks."""
        if not text.strip():
            return
        self.seq_num = (self.seq_num + 1) & 0xFF
        pkt = create_packet(text, self.seq_num)
        iq_burst = modulate_fsk(pkt)

        # Ulangi transmisi burst 2x untuk keandalan nirkabel
        gap = np.zeros(int(SAMPLE_RATE * 0.01), dtype=np.complex64)
        tx_stream = np.concatenate([iq_burst, gap, iq_burst])

        with self.sdr_lock:
            try:
                self.sdr.tx(tx_stream)
            except Exception as e:
                print(f"\n[!] Gagal mengirim: {e}")

    def _rx_worker(self):
        """Thread background untuk menerima sinyal dan mendemodulasi pesan secara continuous."""
        rolling_buffer = np.zeros(0, dtype=np.complex64)
        overlap_size = RX_BUFFER_SIZE // 2

        while self.running:
            try:
                with self.sdr_lock:
                    new_samples = self.sdr.rx()

                if len(rolling_buffer) > 0:
                    analysis_block = np.concatenate([rolling_buffer[-overlap_size:], new_samples])
                else:
                    analysis_block = new_samples
                rolling_buffer = new_samples

                # Hitung RSSI relatif
                pwr = np.mean(np.abs(analysis_block)**2)
                rssi_db = 10 * np.log10(pwr + 1e-12)

                # Demodulasi
                messages = demodulate_fsk_stream(analysis_block)
                now = time.time()

                for msg_text, seq, crc_val in messages:
                    # Filter duplikasi pesan dalam rentang waktu 3 detik
                    is_duplicate = False
                    for old_crc, old_time in zip(self.recent_crcs, self.recent_times):
                        if old_crc == crc_val and (now - old_time) < 3.0:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        self.recent_crcs.append(crc_val)
                        self.recent_times.append(now)
                        timestamp = time.strftime('%H:%M:%S')
                        # Cetak pesan masuk dengan format rapi
                        sys.stdout.write(f"\r\033[K[{timestamp}] [RX RSSI: {rssi_db:5.1f} dB] Teman #{seq} > {msg_text}\n[Saya] > ")
                        sys.stdout.flush()

            except Exception as e:
                if self.running:
                    time.sleep(0.05)

# ================= Program Utama & CLI =================
def select_mode_interactive():
    print("\n" + "=" * 55)
    print("      PLUTOSDR FULL-DUPLEX TEXT MESSENGER")
    print("=" * 55)
    print("Pilih Peran Perangkat:")
    print("  1. Device A (Node 1) -> TX: 433 MHz | RX: 440 MHz")
    print("  2. Device B (Node 2) -> TX: 440 MHz | RX: 433 MHz")
    print("  3. Loopback Test    -> TX: 434 MHz | RX: 434 MHz (1 Pluto)")
    print("  4. Custom Frekuensi")
    print("=" * 55)
    
    choice = input("Pilihan [1/2/3/4] (Default 1): ").strip()
    if choice == "2":
        return 440e6, 433e6, "Device B"
    elif choice == "3":
        return 434e6, 434e6, "Loopback"
    elif choice == "4":
        tx = float(input("Masukkan Frekuensi TX (MHz): ")) * 1e6
        rx = float(input("Masukkan Frekuensi RX (MHz): ")) * 1e6
        return tx, rx, "Custom"
    else:
        return 433e6, 440e6, "Device A"

def main():
    parser = argparse.ArgumentParser(description="PlutoSDR Full-Duplex Text Chat")
    parser.add_argument("--role", choices=["A", "B", "loopback"], help="Peran perangkat (A, B, atau loopback)")
    parser.add_argument("--tx-freq", type=float, help="Frekuensi TX dalam MHz")
    parser.add_argument("--rx-freq", type=float, help="Frekuensi RX dalam MHz")
    parser.add_argument("--ip", type=str, help="IP target PlutoSDR jika via LAN (misal: 192.168.2.1)")
    parser.add_argument("--tx-gain", type=int, default=-10, help="TX Hardware Gain dalam dB (default -10)")
    parser.add_argument("--rx-gain", type=int, default=40, help="RX Hardware Gain dalam dB (default 40)")
    args = parser.parse_args()

    if args.role == "A":
        tx_freq, rx_freq, role_name = 433e6, 440e6, "Device A"
    elif args.role == "B":
        tx_freq, rx_freq, role_name = 440e6, 433e6, "Device B"
    elif args.role == "loopback":
        tx_freq, rx_freq, role_name = 434e6, 434e6, "Loopback"
    elif args.tx_freq and args.rx_freq:
        tx_freq, rx_freq, role_name = args.tx_freq * 1e6, args.rx_freq * 1e6, "Custom"
    else:
        tx_freq, rx_freq, role_name = select_mode_interactive()

    uri = find_pluto_uri(args.ip)
    if not uri:
        print("[!] Gagal: PlutoSDR tidak ditemukan via USB maupun Jaringan.")
        return

    try:
        messenger = PlutoMessenger(
            uri=uri,
            tx_freq=tx_freq,
            rx_freq=rx_freq,
            tx_gain=args.tx_gain,
            rx_gain=args.rx_gain
        )
    except Exception as e:
        print(f"[!] Gagal menghubungkan ke SDR: {e}")
        return

    messenger.start()

    print("\n" + "-" * 55)
    print(f" Siap berkomunikasi ({role_name})!")
    print(" Ketik pesan lalu tekan Enter untuk mengirim.")
    print(" Ketik 'exit' atau 'quit' atau tekan Ctrl+C untuk keluar.")
    print("-" * 55 + "\n")

    try:
        while True:
            try:
                user_msg = input("[Saya] > ").strip()
            except EOFError:
                break

            if not user_msg:
                continue
            if user_msg.lower() in ["exit", "quit"]:
                break

            timestamp = time.strftime('%H:%M:%S')
            messenger.send_message(user_msg)
            sys.stdout.write(f"\033[A\r\033[K[{timestamp}] [TX] Anda > {user_msg}\n")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\n[!] Menutup komunikasi...")
    finally:
        messenger.stop()
        print("[+] Program selesai.")
        os._exit(0)

if __name__ == "__main__":
    main()
