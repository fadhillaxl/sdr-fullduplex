# SDR Full-Duplex Messenger (PlutoSDR / ADALM-PLUTO)

A real-time, bidirectional **Full-Duplex Text Transceiver / Messenger** for the **ADALM-PLUTO (PlutoSDR)** using **Python**, **pyadi-iio**, and **2-FSK modulation** with **CRC16 validation**.

---

## Features

- **Simultaneous Full-Duplex (FDD)**: Transmit (TX) and Receive (RX) text messages at the same time on separate carrier frequencies.
- **Robust 2-FSK Modulation**:
  - Sample Rate: 1 MSps
  - Symbol Rate: 20 kBaud (20 kbps)
  - Frequency Deviation: $\pm 35\text{ kHz}$
- **Packet Framing & Integrity**:
  - 8-Byte Preamble + 16-bit Sync Word (`0x2DD4`)
  - Sequence numbering and length headers
  - CRC16-CCITT checksum verification (filters noise & invalid packets)
- **Automatic Device Discovery**:
  - Auto-detects PlutoSDR connected via USB (`usb:x.x.x`) or Network/LAN (`ip:192.168.2.1`).
- **Interactive Multi-Threaded CLI**:
  - Background RX listener displaying incoming messages with live relative RSSI (dB).
  - Non-blocking TX terminal prompt.
- **Multiple Operational Modes**:
  - Role A (Node 1): TX 433 MHz | RX 440 MHz
  - Role B (Node 2): TX 440 MHz | RX 433 MHz
  - Loopback Test: TX 434 MHz | RX 434 MHz (Self-test on 1 device)
  - Custom Frequency Configuration

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/fadhillaxl/sdr-fullduplex.git
cd sdr-fullduplex
```

### 2. Create and Activate Virtual Environment
```bash
# Recommended using Python 3.12 / 3.11
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Usage

### Interactive Mode (Menu-Driven)
```bash
python full-duplex.py
```

### Two-Device Communication (Node A <-> Node B)
- **On Device A (Node 1)**:
  ```bash
  python full-duplex.py --role A
  ```
- **On Device B (Node 2)**:
  ```bash
  python full-duplex.py --role B
  ```

### Loopback Self-Test (Single PlutoSDR)
```bash
python full-duplex.py --role loopback
```

### Command Line Options
```text
options:
  -h, --help            Show help message and exit
  --role {A,B,loopback} Pre-configured operating role
  --tx-freq TX_FREQ     Custom TX Frequency in MHz
  --rx-freq RX_FREQ     Custom RX Frequency in MHz
  --ip IP               Target PlutoSDR IP address for LAN connection
  --tx-gain TX_GAIN     TX Hardware Gain in dB (default: -10)
  --rx-gain RX_GAIN     RX Hardware Gain in dB (default: 40)
```

---

## License
MIT License
