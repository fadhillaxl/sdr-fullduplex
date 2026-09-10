# Product Requirements Document (PRD)

## Pluto+ SDR Short-Range IP Mesh Radio

**Version:** 1.0
**Status:** MVP / Experimental
**Platform:** Raspberry Pi + ADALM-Pluto / Pluto+
**Target:** Short-range SDR digital communication
**Architecture:** Software-defined QPSK/OFDM IP Radio
**PA/LNA:** Tidak digunakan pada MVP

---

# 1. Product Overview

Proyek ini bertujuan membuat sistem komunikasi digital jarak pendek menggunakan:

* Raspberry Pi
* Pluto+ SDR
* Python
* libiio / pyadi-iio
* QPSK
* OFDM/COFDM
* FEC
* CRC
* Packet framing
* UDP/IP
* Linux networking

Sistem akan memungkinkan dua Raspberry Pi bertukar data melalui link RF menggunakan Pluto+ tanpa menggunakan:

* Wi-Fi sebagai jalur komunikasi utama
* 4G/5G
* Internet
* PA
* LNA
* radio modem komersial

Target akhir MVP adalah Raspberry Pi A dapat melakukan komunikasi IP dengan Raspberry Pi B melalui:

```text
Raspberry Pi A
      │
      │ USB
      ▼
   Pluto+ A
      │
      │ RF
      ▼
   Pluto+ B
      │
      │ USB
      ▼
Raspberry Pi B
```

Contoh penggunaan:

```text
Pi A
 │
 ├── ping
 ├── UDP
 ├── TCP
 ├── telemetry
 └── file/data
       │
       ▼
      RF
       │
       ▼
Pi B
```

---

# 2. Product Vision

Membangun **open-source SDR IP radio** yang dapat berkembang dari komunikasi point-to-point menjadi:

```text
Point-to-Point
      ↓
IP Radio
      ↓
OFDM Broadband
      ↓
Multi-node
      ↓
Ad-Hoc Network
      ↓
Mesh Network
      ↓
Multi-hop
      ↓
FHSS
```

Produk akhir diharapkan memiliki konsep yang mirip dengan broadband IP mesh radio komersial, tetapi modem RF dan network stack dikembangkan sendiri menggunakan Pluto+.

---

# 3. Goals

## 3.1 Primary Goals

MVP harus mampu:

1. Menginisialisasi Pluto+ dari Raspberry Pi.
2. Mengirim dan menerima IQ samples.
3. Membuat transmitter QPSK.
4. Membuat receiver QPSK.
5. Membuat OFDM modem.
6. Melakukan packet framing.
7. Menambahkan CRC.
8. Menambahkan FEC.
9. Mengirim data melalui RF.
10. Menerima dan memvalidasi packet.
11. Membawa data UDP.
12. Membuat komunikasi IP sederhana antar Raspberry Pi.

---

# 4. Non-Goals MVP

Fitur berikut tidak wajib pada versi pertama:

* PA
* LNA
* GPS synchronization
* Frequency hopping
* Adaptive modulation
* MIMO
* encryption
* multi-hop mesh
* routing dinamis
* long-range communication
* satellite communication
* internet gateway
* high-power transmission

Fitur tersebut menjadi roadmap tahap berikutnya.

---

# 5. Hardware Requirements

## Node A

* Raspberry Pi 5
* Pluto+
* USB cable
* RF antenna yang sesuai
* Power supply

## Node B

* Raspberry Pi 5 / Raspberry Pi 4
* Pluto+
* USB cable
* RF antenna yang sesuai
* Power supply

Architecture:

```text
┌─────────────────────────┐
│ Raspberry Pi A          │
│                         │
│ Python SDR Application  │
└───────────┬─────────────┘
            │ USB
            ▼
┌─────────────────────────┐
│ Pluto+ A                │
│ TX/RX                   │
└───────────┬─────────────┘
            │
            │ RF
            │
┌───────────▼─────────────┐
│ Pluto+ B                │
│ RX/TX                   │
└───────────┬─────────────┘
            │ USB
            ▼
┌─────────────────────────┐
│ Raspberry Pi B          │
│ Python SDR Application  │
└─────────────────────────┘
```

---

# 6. RF Safety

MVP harus dimulai dengan daya transmit serendah mungkin dan jarak pendek.

Target awal:

```text
1–5 meter
```

Kemudian:

```text
10 m
25 m
50 m
```

hanya jika link tetap stabil dan penggunaan frekuensi/daya sesuai regulasi yang berlaku.

Untuk pengujian conducted:

```text
Pluto TX
   │
   ▼
Attenuator
   │
   ▼
Pluto RX
```

Jangan menghubungkan TX Pluto langsung ke RX Pluto tanpa attenuator yang sesuai.

---

# 7. Software Stack

## Operating System

Raspberry Pi OS / Linux.

## Programming Language

Primary:

```text
Python 3
```

## SDR Libraries

```text
libiio
pyadi-iio
numpy
scipy
```

Optional:

```text
numba
```

untuk optimasi DSP.

---

# 8. System Architecture

```text
                 APPLICATION
                     │
                     ▼
                 UDP / IP
                     │
                     ▼
               Packet Layer
                     │
                     ▼
                   CRC
                     │
                     ▼
                   FEC
                     │
                     ▼
              Frame Generator
                     │
                     ▼
              OFDM Modulator
                     │
                     ▼
                 QPSK
                     │
                     ▼
                 IFFT
                     │
                     ▼
               Pluto+ TX
                     │
                     ▼
                    RF
                     │
                     ▼
               Pluto+ RX
                     │
                     ▼
                   FFT
                     │
                     ▼
             OFDM Demodulator
                     │
                     ▼
                   QPSK
                     │
                     ▼
                   FEC
                     │
                     ▼
                   CRC
                     │
                     ▼
               Packet Layer
                     │
                     ▼
                  UDP/IP
```

---

# 9. Communication Protocol

## 9.1 Frame Structure

Setiap RF frame menggunakan:

```text
┌──────────┬────────┬──────────┬─────────┬──────────┐
│ Preamble │ Header │ Sequence │ Payload │ CRC      │
└──────────┴────────┴──────────┴─────────┴──────────┘
```

### Preamble

Digunakan untuk:

* packet detection
* synchronization
* timing synchronization
* frequency offset estimation

### Header

Berisi:

```text
version
packet_type
payload_length
sequence_number
modulation
coding_rate
```

### Sequence Number

Digunakan untuk:

* packet ordering
* packet loss detection
* duplicate detection

### Payload

Membawa data aplikasi.

### CRC

Digunakan untuk mendeteksi packet corruption.

---

# 10. Modulation

## MVP Stage 1

Gunakan:

```text
BPSK
```

untuk memastikan seluruh modem bekerja.

## MVP Stage 2

Naik ke:

```text
QPSK
```

QPSK menjadi modulasi utama MVP.

## Future

```text
16-QAM
64-QAM
```

Adaptive modulation dapat ditambahkan kemudian.

---

# 11. OFDM

Target konfigurasi awal:

```text
Sample Rate : ~2 MSPS
RF Bandwidth: ~1 MHz
FFT Size    : 64
CP          : 16
Modulation  : QPSK
```

Parameter tersebut bukan nilai final dan harus dapat dikonfigurasi.

Configuration file:

```yaml
radio:
  sample_rate: 2000000
  bandwidth: 1000000
  center_frequency: 433000000

ofdm:
  fft_size: 64
  cyclic_prefix: 16

modulation:
  mode: qpsk

network:
  mtu: 1024
```

---

# 12. Transmitter Pipeline

```text
Application
     │
     ▼
UDP packet
     │
     ▼
Packet serializer
     │
     ▼
CRC
     │
     ▼
FEC encoder
     │
     ▼
Frame builder
     │
     ▼
QPSK mapper
     │
     ▼
OFDM symbol generator
     │
     ▼
IFFT
     │
     ▼
Cyclic Prefix
     │
     ▼
Pulse shaping
     │
     ▼
IQ samples
     │
     ▼
Pluto+
```

---

# 13. Receiver Pipeline

```text
Pluto+
   │
   ▼
IQ samples
   │
   ▼
AGC / normalization
   │
   ▼
Packet detection
   │
   ▼
Timing synchronization
   │
   ▼
Frequency correction
   │
   ▼
Remove cyclic prefix
   │
   ▼
FFT
   │
   ▼
Channel estimation
   │
   ▼
QPSK demodulation
   │
   ▼
FEC decoder
   │
   ▼
CRC validation
   │
   ▼
Frame parser
   │
   ▼
UDP packet
```

---

# 14. Network Architecture

Setiap node mempunyai interface virtual:

```text
radio0
```

Contoh:

```text
Node A:
192.168.50.1/24

Node B:
192.168.50.2/24
```

Target:

```bash
ping 192.168.50.2
```

Traffic:

```text
Application
    │
    ▼
192.168.50.2
    │
    ▼
Linux networking
    │
    ▼
radio0
    │
    ▼
RF modem
```

---

# 15. MVP Networking Strategy

Versi pertama tidak harus membuat full Linux TAP/TUN interface.

Tahap awal:

```text
Python UDP
   ↓
RF modem
   ↓
Python UDP
```

Contoh:

```text
Pi A
UDP 5000
   ↓
RF
   ↓
Pi B
UDP 5000
```

Setelah stabil:

```text
TUN interface
    ↓
IP packet
    ↓
RF modem
```

Sehingga Linux menganggap radio sebagai network interface.

---

# 16. Required Applications

Project harus memiliki command-line tools:

```bash
pluto-radio status
```

Menampilkan:

```text
Pluto detected
TX frequency: ...
RX frequency: ...
Sample rate: ...
Bandwidth: ...
```

---

```bash
pluto-radio tx
```

Menjalankan transmitter.

---

```bash
pluto-radio rx
```

Menjalankan receiver.

---

```bash
pluto-radio link
```

Menjalankan TX/RX modem.

---

```bash
pluto-radio ping
```

Melakukan test RF packet.

---

```bash
pluto-radio stats
```

Menampilkan:

```text
TX packets
RX packets
Packet loss
CRC errors
RSSI
SNR
EVM
Throughput
Latency
```

---

# 17. Telemetry

System harus menyediakan statistik:

```text
RSSI
SNR
EVM
CFO
Packet Loss
BER
PER
Throughput
Latency
TX packets
RX packets
CRC errors
FEC errors
```

Contoh:

```text
--------------------------------
PLUTO RADIO LINK
--------------------------------
RSSI       : -48 dBm
SNR        : 22.4 dB
EVM        : 4.8 %
CFO        : 1.2 kHz

TX packets : 1250
RX packets : 1248
CRC errors : 2
PER        : 0.16 %

Throughput : 820 kbps
Latency    : 18 ms
--------------------------------
```

---

# 18. Testing Strategy

## Test 1 — Pluto Detection

Acceptance criteria:

```text
Pluto+ detected
IIO connection successful
TX/RX channels available
```

---

## Test 2 — IQ Loopback

Test:

```text
TX → attenuator → RX
```

Acceptance:

* signal detected
* constellation visible
* synchronization successful

---

## Test 3 — BPSK

Acceptance:

* packet transmitted
* packet received
* CRC valid

---

## Test 4 — QPSK

Acceptance:

* QPSK constellation stable
* packet error rate acceptable

---

## Test 5 — OFDM

Acceptance:

* synchronization successful
* OFDM symbols decoded
* no continuous frame loss

---

## Test 6 — UDP

```text
Pi A
UDP
 ↓
RF
 ↓
Pi B
```

Acceptance:

* packets arrive
* sequence numbers correct
* CRC valid

---

## Test 7 — IP

Target:

```bash
ping 192.168.50.2
```

Acceptance:

```text
0% packet loss
```

under controlled short-range conditions.

---

# 19. Performance Targets

Initial MVP target:

| Metric      |      Target |
| ----------- | ----------: |
| Distance    |       1–5 m |
| Modulation  |        QPSK |
| Bandwidth   |      ~1 MHz |
| Sample rate |     ~2 MSPS |
| Packet size | ≤1024 bytes |
| Packet loss |         <5% |
| CRC error   |         <5% |
| Latency     |     <100 ms |
| Throughput  |   ≥100 kbps |

Target is experimental stability, not maximum Pluto+ performance.

---

# 20. Logging

Application harus menghasilkan log:

```text
logs/
├── tx.log
├── rx.log
├── modem.log
├── network.log
└── errors.log
```

Contoh:

```text
[08:21:01.120] TX packet seq=100
[08:21:01.145] RX packet seq=100
[08:21:01.145] CRC OK
[08:21:01.146] latency=26ms
```

---

# 21. Project Structure

Recommended:

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
│       │
│       ├── hardware/
│       │   ├── pluto.py
│       │   └── iio.py
│       │
│       ├── dsp/
│       │   ├── qpsk.py
│       │   ├── ofdm.py
│       │   ├── sync.py
│       │   ├── channel.py
│       │   └── filter.py
│       │
│       ├── protocol/
│       │   ├── frame.py
│       │   ├── crc.py
│       │   ├── fec.py
│       │   └── sequence.py
│       │
│       ├── network/
│       │   ├── udp.py
│       │   └── tun.py
│       │
│       ├── telemetry/
│       │   └── stats.py
│       │
│       └── cli.py
│
├── tests/
│   ├── test_qpsk.py
│   ├── test_ofdm.py
│   ├── test_crc.py
│   └── test_protocol.py
│
├── scripts/
│   ├── tx.py
│   ├── rx.py
│   └── link.py
│
└── systemd/
    └── pluto-radio.service
```

---

# 22. Development Phases

## Phase 0 — Hardware

* Raspberry Pi setup
* Pluto+ detection
* USB connection
* libiio
* pyadi-iio

Deliverable:

```text
Pluto+ READY
```

---

## Phase 1 — RF

Implement:

```text
TX tone
RX tone
```

Deliverable:

```text
RF signal detected
```

---

## Phase 2 — BPSK

Implement:

```text
Preamble
BPSK
CRC
```

Deliverable:

```text
HELLO WORLD
```

transmitted over RF.

---

## Phase 3 — QPSK

Implement:

```text
QPSK mapper
QPSK demapper
```

Deliverable:

```text
Packet TX/RX
```

---

## Phase 4 — OFDM

Implement:

```text
FFT
IFFT
Cyclic Prefix
Pilot
Synchronization
Channel estimation
```

Deliverable:

```text
Reliable OFDM packet
```

---

## Phase 5 — UDP

Implement:

```text
UDP → RF → UDP
```

Deliverable:

```text
UDP communication
```

---

## Phase 6 — IP Interface

Implement:

```text
TUN/TAP
```

Deliverable:

```text
Pi A
192.168.50.1
       │
       RF
       │
Pi B
192.168.50.2
```

and:

```bash
ping 192.168.50.2
```

---

# 23. Phase 7 — Mesh

Add:

```text
Node A
   │
   ▼
Node B
   │
   ▼
Node C
```

Routing:

```text
A → B → C
```

Potential technologies:

* BATMAN-adv
* Babel
* OLSR
* custom routing

Initial recommendation:

```text
Babel / BATMAN-adv
```

depending on how the virtual RF interface is implemented.

---

# 24. Phase 8 — FHSS

Add configurable hopping:

```text
frequency_table:
  - F1
  - F2
  - F3
  - F4
  - F5
```

Both nodes maintain:

```text
hop_sequence
hop_interval
channel_table
synchronization
```

Important:

FHSS must only operate over frequencies/channels and transmit parameters that are legally permitted for the intended deployment.

---

# 25. Phase 9 — Adaptive Modulation

Potential modes:

```text
BPSK
QPSK
16-QAM
64-QAM
```

Example:

```text
SNR < 5 dB
    ↓
BPSK

SNR 5–12 dB
    ↓
QPSK

SNR 12–20 dB
    ↓
16-QAM

SNR > 20 dB
    ↓
64-QAM
```

This is a future feature.

---

# 26. Phase 10 — Web UI

Future architecture:

```text
                 Web UI
                   │
                FastAPI
                   │
        ┌──────────┴─────────┐
        │                    │
     Radio API          Telemetry
        │                    │
        └──────────┬─────────┘
                   │
               Pluto Radio
                   │
                 Pluto+
```

Dashboard:

```text
┌───────────────────────────────────┐
│ Pluto IP Radio                    │
├───────────────────────────────────┤
│ Status       CONNECTED            │
│ Frequency    433 MHz              │
│ Bandwidth    1 MHz                │
│ Modulation   QPSK                 │
│                                   │
│ RSSI         -48 dBm              │
│ SNR          22 dB                │
│ BER          0.01%                │
│ PER          0.16%                │
│                                   │
│ RX           820 kbps              │
│ TX           790 kbps              │
└───────────────────────────────────┘
```

---

# 27. Future Architecture

Target final system:

```text
                         NODE B
                           │
                       Pluto+
                           │
                           │
NODE A                 RF MESH                NODE C
Raspberry Pi ─ Pluto+ )))))))))))) (((((((( Pluto+ ─ Raspberry Pi
                           │
                           │
                         NODE D
                           │
                        Pluto+
```

Every node:

```text
Linux
 │
 ├── IP
 ├── Routing
 ├── Mesh
 ├── Telemetry
 └── SDR modem
       │
       └── Pluto+
```

---

# 28. Future Satellite Integration

Setelah terrestrial link berhasil, sistem dapat digunakan sebagai experimental ground link untuk project satelit.

Contoh:

```text
                    SATELLITE
                       │
                       │ RF
                       ▼
                  Pluto SDR
                       │
                  Raspberry Pi
                       │
                 Ground Station
                       │
            ┌──────────┴──────────┐
            │                     │
         Gpredict               SatDump
            │                     │
            └──────────┬──────────┘
                       │
                    Web UI
```

Untuk komunikasi satelit, modem, frekuensi, power, antenna, link budget, dan protokol harus dirancang ulang sesuai satelit yang digunakan.

---

# 29. Security

MVP:

```text
No encryption
```

Future:

```text
AES-256
ChaCha20-Poly1305
```

Authentication:

```text
PSK
Node ID
Packet authentication
```

Security tidak boleh menjadi prioritas sebelum RF link stabil.

---

# 30. Success Criteria

MVP dianggap berhasil apabila:

### Hardware

* [ ] Raspberry Pi mendeteksi Pluto+
* [ ] IIO dapat digunakan
* [ ] TX berfungsi
* [ ] RX berfungsi

### DSP

* [ ] QPSK TX berhasil
* [ ] QPSK RX berhasil
* [ ] OFDM synchronization berhasil
* [ ] Channel estimation berhasil
* [ ] CRC berhasil
* [ ] FEC berhasil

### Networking

* [ ] UDP dapat dikirim melalui RF
* [ ] UDP dapat diterima
* [ ] packet loss dapat diukur
* [ ] latency dapat diukur
* [ ] TUN/TAP berhasil
* [ ] IP address dapat digunakan
* [ ] ping berhasil

### Stability

* [ ] Link stabil minimal 10 menit
* [ ] Packet statistics tersedia
* [ ] Error logging tersedia
* [ ] Radio dapat restart tanpa reboot Raspberry Pi

---

# 31. MVP Definition

MVP minimum:

```text
Pi A
 │
 │ UDP
 ▼
Python modem
 │
 │ QPSK
 ▼
OFDM
 │
 ▼
Pluto+
 │
 │ RF
 ▼
Pluto+
 │
 ▼
OFDM
 │
 ▼
QPSK
 │
 ▼
Python modem
 │
 ▼
UDP
 │
 ▼
Pi B
```

**MVP selesai ketika data `HELLO WORLD` dan UDP dapat berhasil dikirim melalui RF dari Pi A ke Pi B menggunakan Pluto+ tanpa PA/LNA.**

Setelah itu:

```text
UDP
 ↓
TUN
 ↓
IP
 ↓
Routing
 ↓
Mesh
 ↓
FHSS
```

menjadi pengembangan berikutnya.
