# MASTER PROMPT

## Implement Pluto+ SDR Short-Range IP Radio

Kamu adalah **senior SDR/DSP engineer, Linux networking engineer, dan Python developer**.

Saya ingin kamu mengimplementasikan proyek berdasarkan PRD berikut:

> **Project:** Pluto+ SDR Short-Range IP Radio
> **Hardware:** 2× Raspberry Pi + 2× ADALM-Pluto/Pluto+
> **RF:** direct short-range OTA
> **PA:** tidak digunakan
> **LNA:** tidak digunakan
> **Language:** Python
> **DSP:** NumPy/SciPy + pyadi-iio/libiio
> **Target akhir:** IP communication melalui RF, kemudian dikembangkan menjadi Mesh + FHSS.

---

# 1. ATURAN UTAMA

Jangan mencoba membuat seluruh sistem sekaligus.

Implementasikan secara bertahap:

```text
Stage 0
Hardware detection
        ↓
Stage 1
RF TX/RX
        ↓
Stage 2
BPSK
        ↓
Stage 3
QPSK
        ↓
Stage 4
OFDM
        ↓
Stage 5
Packet modem
        ↓
Stage 6
UDP
        ↓
Stage 7
TUN/TAP IP
        ↓
Stage 8
Mesh
        ↓
Stage 9
FHSS
```

**Jangan melanjutkan ke stage berikutnya sebelum stage sebelumnya dapat diuji.**

Jika hardware belum tersedia, buat software simulation/test mode sehingga DSP dapat diuji tanpa Pluto.

---

# 2. HARDWARE

Target node:

```text
Node A:

Raspberry Pi
     │
    USB
     │
   Pluto+
     │
    RF
```

Node B memiliki konfigurasi yang sama.

Gunakan pyadi-iio/libiio untuk komunikasi dengan Pluto.

Jangan menggunakan GNU Radio sebagai dependency utama.

Python adalah DSP/modem utama.

---

# 3. SOFTWARE STACK

Gunakan:

```text
Python 3
NumPy
SciPy
pyadi-iio
libiio
pytest
PyYAML
```

Untuk networking:

```text
socket
asyncio
TUN/TAP
Linux networking
```

Jangan menambahkan dependency besar tanpa alasan.

---

# 4. PROJECT STRUCTURE

Buat repository:

```text
pluto-ip-radio/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
│
├── config/
│   └── radio.yaml
│
├── src/
│   └── pluto_radio/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── hardware/
│       │   ├── __init__.py
│       │   ├── pluto.py
│       │   └── iio.py
│       │
│       ├── dsp/
│       │   ├── __init__.py
│       │   ├── qpsk.py
│       │   ├── ofdm.py
│       │   ├── sync.py
│       │   ├── channel.py
│       │   └── filters.py
│       │
│       ├── protocol/
│       │   ├── __init__.py
│       │   ├── frame.py
│       │   ├── crc.py
│       │   ├── fec.py
│       │   └── sequence.py
│       │
│       ├── network/
│       │   ├── __init__.py
│       │   ├── udp.py
│       │   └── tun.py
│       │
│       └── telemetry/
│           ├── __init__.py
│           └── stats.py
│
├── scripts/
│   ├── detect_pluto.py
│   ├── tx.py
│   ├── rx.py
│   └── link.py
│
├── tests/
│   ├── test_qpsk.py
│   ├── test_ofdm.py
│   ├── test_crc.py
│   ├── test_frame.py
│   └── test_protocol.py
│
└── systemd/
    └── pluto-radio.service
```

---

# 5. CONFIGURATION

Semua parameter radio harus configurable.

Buat:

```yaml
radio:
  uri: "ip:192.168.2.1"
  center_frequency: 433000000
  sample_rate: 2000000
  bandwidth: 1000000
  tx_gain: -20
  rx_gain_mode: "slow_attack"

ofdm:
  fft_size: 64
  cyclic_prefix: 16
  pilot_spacing: 4

modulation:
  mode: "bpsk"

network:
  mtu: 1024

debug:
  simulation_mode: true
```

Jangan hard-code parameter RF di source code.

Jika Pluto menggunakan URI USB berbeda, konfigurasi harus mudah diubah.

---

# 6. STAGE 0 — HARDWARE DETECTION

Buat:

```bash
python scripts/detect_pluto.py
```

Output:

```text
================================
PLUTO SDR
================================
Status       : CONNECTED
URI          : ...
Model        : ADALM-PLUTO
TX channels  : OK
RX channels  : OK
Sample rate  : ...
================================
```

Jika Pluto tidak tersedia:

```text
Status : NOT FOUND
```

Jangan crash dengan traceback yang tidak jelas.

Berikan troubleshooting message.

---

# 7. STAGE 1 — RF TEST

Implementasikan:

```bash
python scripts/tx.py
python scripts/rx.py
```

TX mengirim test tone.

RX menghitung:

```text
RSSI
signal power
noise power
SNR
```

Output:

```text
RX
----------------------
Signal : -45.2 dBFS
Noise  : -72.4 dBFS
SNR    : 27.2 dB
```

Tambahkan simulation mode.

---

# 8. STAGE 2 — BPSK

Implementasikan:

```python
bpsk_modulate(bits)
bpsk_demodulate(symbols)
```

Buat unit test:

```text
random bits
    ↓
BPSK modulate
    ↓
AWGN
    ↓
BPSK demodulate
    ↓
compare bits
```

Test harus menghitung BER.

Contoh:

```text
BER: 0.0001
```

---

# 9. STAGE 3 — QPSK

Implementasikan:

```python
qpsk_modulate(bits)
qpsk_demodulate(symbols)
```

Gunakan Gray coding.

Buat constellation diagnostic:

```text
        Q
        │
    ●   │   ●
        │
────────┼──────── I
        │
    ●   │   ●
        │
```

Test:

```text
bits
 ↓
QPSK
 ↓
channel
 ↓
QPSK RX
 ↓
bits
```

Hitung:

```text
BER
EVM
```

---

# 10. STAGE 4 — OFDM

Implementasikan OFDM modem.

Parameter awal:

```text
FFT = 64
CP = 16
```

Pipeline TX:

```text
bits
 ↓
QPSK
 ↓
subcarrier mapping
 ↓
pilot insertion
 ↓
IFFT
 ↓
cyclic prefix
 ↓
IQ
```

RX:

```text
IQ
 ↓
timing synchronization
 ↓
remove CP
 ↓
FFT
 ↓
channel estimation
 ↓
pilot correction
 ↓
QPSK demodulation
 ↓
bits
```

Implementasikan:

```python
ofdm_modulate()
ofdm_demodulate()
```

---

# 11. SYNCHRONIZATION

Implementasikan secara bertahap:

1. packet detection
2. coarse timing synchronization
3. carrier frequency offset estimation
4. frequency correction
5. fine synchronization

Jangan menganggap sample alignment sempurna.

Buat test dengan:

```text
timing offset
frequency offset
AWGN
```

dan pastikan receiver masih dapat recover packet.

---

# 12. CHANNEL ESTIMATION

Gunakan pilot subcarriers.

Receiver harus dapat mengestimasi:

```text
H(f)
```

dan melakukan equalization:

```text
Y(f) / H(f)
```

Buat test channel:

```text
AWGN
+
frequency offset
+
multipath
```

---

# 13. PACKET PROTOCOL

Frame:

```text
┌──────────┬────────┬──────────┬──────────┬────────┐
│ Preamble │ Header │ Sequence │ Payload  │ CRC    │
└──────────┴────────┴──────────┴──────────┴────────┘
```

Header minimal:

```text
version
packet_type
payload_length
sequence_number
modulation
coding_rate
```

Implementasikan:

```python
encode_frame()
decode_frame()
```

---

# 14. CRC

Gunakan CRC yang umum dan terdokumentasi.

Implementasikan:

```python
calculate_crc()
verify_crc()
```

Test:

```text
valid packet → PASS
modified packet → FAIL
```

---

# 15. FEC

Buat abstraction:

```python
fec_encode()
fec_decode()
```

Implementasi awal dapat menggunakan coding sederhana yang mudah diuji.

Architecture harus memungkinkan penggantian FEC kemudian.

Contoh future:

```text
Convolutional
LDPC
Reed-Solomon
```

Jangan membuat FEC terlalu kompleks pada tahap awal.

---

# 16. RF PACKET TEST

Buat:

```bash
python scripts/link.py
```

Node A:

```text
TX
```

Node B:

```text
RX
```

Kirim:

```text
HELLO WORLD
```

Output RX:

```text
Packet received
SEQ       : 100
Length    : 11
CRC       : OK
Payload   : HELLO WORLD
RSSI      : -48 dBFS
SNR       : 24 dB
```

---

# 17. LOOPBACK MODE

WAJIB membuat mode:

```text
simulation_mode
```

sehingga:

```text
TX
 ↓
channel simulator
 ↓
RX
```

dapat diuji tanpa Pluto.

Channel simulator harus mendukung:

```text
AWGN
frequency offset
timing offset
multipath
```

Contoh:

```bash
python scripts/link.py --simulation
```

---

# 18. UDP TRANSPORT

Setelah RF packet stabil, implementasikan:

```text
UDP socket
    ↓
packet protocol
    ↓
RF
    ↓
packet protocol
    ↓
UDP socket
```

Node A:

```text
UDP 192.168.50.1:5000
```

Node B:

```text
UDP 192.168.50.2:5000
```

Test:

```bash
iperf3
```

atau custom UDP benchmark.

Catat:

```text
throughput
packet loss
latency
jitter
```

---

# 19. TUN/TAP

Setelah UDP stabil, buat virtual network interface:

```text
radio0
```

Node A:

```text
192.168.50.1/24
```

Node B:

```text
192.168.50.2/24
```

Linux packet:

```text
IP packet
 ↓
radio0
 ↓
Python modem
 ↓
RF
 ↓
Python modem
 ↓
radio0
 ↓
Linux
```

Target:

```bash
ping 192.168.50.2
```

---

# 20. TELEMETRY

Implementasikan:

```python
RadioStats
```

minimal:

```text
tx_packets
rx_packets
crc_errors
fec_errors
packet_loss
rssi
snr
ber
per
evm
cfo
throughput
latency
```

CLI:

```bash
pluto-radio stats
```

---

# 21. CLI

Buat command:

```text
pluto-radio status
pluto-radio tx
pluto-radio rx
pluto-radio link
pluto-radio ping
pluto-radio stats
```

Gunakan argparse atau typer.

CLI harus memberikan error yang mudah dipahami.

---

# 22. TESTING

Setiap DSP component wajib mempunyai unit test.

Minimal:

```text
test_bpsk
test_qpsk
test_ofdm
test_crc
test_fec
test_frame
test_sync
```

Tambahkan integration test:

```text
payload
 ↓
frame
 ↓
FEC
 ↓
QPSK
 ↓
OFDM
 ↓
channel
 ↓
OFDM
 ↓
QPSK
 ↓
FEC
 ↓
frame
 ↓
payload
```

Acceptance:

```text
input == output
```

untuk kondisi channel yang sesuai.

---

# 23. DEBUGGING TOOLS

Sediakan optional diagnostic output:

```text
constellation
spectrum
waterfall
eye diagram
channel response
```

Gunakan matplotlib hanya untuk debugging/offline analysis.

Jangan membuat GUI sebagai prioritas MVP.

---

# 24. PERFORMANCE

Target awal:

```text
Distance:
1–5 meter

Bandwidth:
~1 MHz

Sample rate:
~2 MSPS

Modulation:
QPSK

Packet:
≤1024 bytes

Latency:
<100 ms

Packet loss:
<5%

Throughput:
≥100 kbps
```

Jangan mengejar maximum throughput terlebih dahulu.

Prioritaskan:

```text
CORRECTNESS
→
STABILITY
→
MEASUREMENT
→
PERFORMANCE
```

---

# 25. MESH — JANGAN IMPLEMENTASIKAN DULU

Setelah point-to-point IP link stabil, baru desain:

```text
Node A
  │
  ▼
Node B
  │
  ▼
Node C
```

Setiap node harus dapat forward packet.

Pertimbangkan:

```text
Babel
BATMAN-adv
OLSR
```

Jangan memilih secara otomatis.

Evaluasi terlebih dahulu interface yang dihasilkan modem.

---

# 26. FHSS — FUTURE

Jangan implementasikan FHSS sebelum:

```text
QPSK
+
OFDM
+
packet
+
IP
```

stabil.

Setelah itu buat:

```yaml
fhss:
  enabled: false
  dwell_time_ms: 100
  channels:
    - ...
    - ...
    - ...
```

Hanya gunakan frekuensi dan parameter transmit yang legal untuk lingkungan pengujian.

---

# 27. DEVELOPMENT RULE

Setiap selesai satu stage:

1. Implementasikan kode.
2. Buat/update unit tests.
3. Jalankan tests.
4. Perbaiki error.
5. Update README.
6. Berikan command untuk mencoba stage tersebut.
7. Jangan lanjut jika test gagal.

Format laporan setiap stage:

```text
STAGE:
Status:

Implemented:
- ...
- ...

Tests:
- ...
- ...

Result:
PASS / FAIL

How to run:
...

Known issues:
...

Next stage:
...
```

---

# 28. HARDWARE-AWARE DEVELOPMENT

Jika Pluto tidak tersedia:

```text
SIMULATION MODE
```

harus tetap memungkinkan pengembangan DSP.

Jika Pluto tersedia:

```text
HARDWARE MODE
```

digunakan.

Jangan membuat test suite bergantung pada hardware.

---

# 29. ERROR HANDLING

Jika Pluto tidak terdeteksi:

JANGAN:

```text
Traceback...
```

sebagai satu-satunya informasi.

Gunakan:

```text
ERROR: Pluto SDR not detected.

Check:
1. USB connection
2. `iio_info -s`
3. Pluto network/USB URI
4. libiio installation
5. permissions
```

---

# 30. DOCUMENTATION

README harus menjelaskan:

```text
Architecture
Hardware
Installation
Pluto setup
Configuration
Simulation
BPSK
QPSK
OFDM
Packet protocol
UDP
TUN/TAP
Testing
Troubleshooting
Performance testing
Roadmap
```

Buat juga:

```text
docs/
├── architecture.md
├── dsp.md
├── protocol.md
├── networking.md
├── testing.md
└── troubleshooting.md
```

---

# 31. IMPORTANT ENGINEERING RULES

Jangan:

* hard-code RF configuration
* membuat semua kode dalam satu file
* menggunakan global state berlebihan
* mencampur DSP dengan networking
* membuat mesh sebelum P2P stabil
* membuat FHSS sebelum modem stabil
* menganggap channel ideal
* menganggap frequency synchronization sempurna
* mengabaikan packet loss
* mengabaikan CRC
* mengabaikan FEC
* mengklaim throughput tanpa benchmark

Pisahkan layer:

```text
Hardware
   ↓
DSP
   ↓
Protocol
   ↓
Transport
   ↓
Network
   ↓
Application
```

---

# 32. FIRST TASK

**Jangan langsung mengimplementasikan seluruh PRD.**

Mulai hanya dengan:

## STAGE 0

Implementasikan:

```text
project structure
pyproject.toml
requirements
configuration system
Pluto detection
simulation mode
basic CLI
tests
README
```

Kemudian jalankan test.

Setelah STAGE 0 selesai, tampilkan:

```text
STAGE 0 COMPLETE
```

beserta:

1. file yang dibuat
2. file yang diubah
3. command installation
4. command test
5. hasil test
6. command untuk mendeteksi Pluto
7. masalah yang ditemukan
8. rekomendasi STAGE 1

**Jangan mengimplementasikan STAGE 1 sebelum saya memberikan persetujuan atau meminta lanjut.**

# END OF PROMPT
