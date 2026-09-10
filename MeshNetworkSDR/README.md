# Pluto+ SDR Short-Range IP Radio & Modem

Open-source Software-Defined Radio IP Radio system engineered for Raspberry Pi and ADALM-Pluto / Pluto+ SDRs.

The target of this project is to provide a fully-functional digital communications link directly connecting two nodes over RF without relying on commercial cellular or Wi-Fi chipsets, evolving from short-range point-to-point IP connectivity to an ad-hoc mesh network with FHSS.

---

## 1. Architecture Overview

```text
                 APPLICATION
                      │
                      ▼
                  UDP / IP
                      │
                      ▼
                Packet Layer (Framing, Sequence)
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
                  QPSK / BPSK
                      │
                      ▼
                  IFFT + CP
                      │
                      ▼
                Pluto+ SDR TX
                      │
                      ▼
                     RF
                      │
                      ▼
                Pluto+ SDR RX
                      │
                      ▼
                  Sync & FFT
                      │
                      ▼
               Channel Equalizer
                      │
                      ▼
                 Demodulator
                      │
                      ▼
                     FEC
                      │
                      ▼
                     CRC
                      │
                      ▼
                 UDP / IP Layer
```

For in-depth architectural details, refer to [docs/architecture.md](docs/architecture.md).

---

## 2. Hardware Requirements

- **Nodes**: 2× Raspberry Pi (Pi 4 or Pi 5 recommended).
- **SDRs**: 2× ADALM-Pluto or Pluto+ SDRs.
- **RF**: Direct short-range OTA (1–5 meters initially) or conducted cable with suitable 30–40 dB RF attenuator.
- **Amplifiers**: PA and LNA are **not used** for MVP safety and linearity.

---

## 3. Installation

Ensure Python 3.10+ is available on your host or Raspberry Pi.

```bash
# Clone the repository and navigate to MeshNetworkSDR
cd MeshNetworkSDR

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install pluto-radio CLI in editable mode
pip install -e .
```

---

## 4. Pluto SDR Setup & Troubleshooting

### USB Connection
Connect the Pluto SDR to the Raspberry Pi's high-power USB port (or active USB hub) using a high-quality data micro-USB cable.

Verify the device is recognized:
```bash
python scripts/detect_pluto.py
# or using the CLI:
pluto-radio status
```

### Network URI
If accessing Pluto over Ethernet/USB-RNDIS:
```bash
python scripts/detect_pluto.py --uri ip:192.168.2.1
```

---

## 5. Configuration

All radio and modem parameters are configured in [`config/radio.yaml`](config/radio.yaml):

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

---

## 6. Simulation Mode

For development and automated testing without connected Pluto hardware, pass `--simulation`:

```bash
# Hardware detection in simulation mode
python scripts/detect_pluto.py --simulation

# CLI status in simulation mode
pluto-radio status --simulation
```

---

## 7. Running the Test Suite

Run pytest to execute the full unit test suite:

```bash
pytest tests/ -v
```

---

## 8. Development Stages & Roadmap

The project follows a phased, gate-controlled implementation:

| Stage | Milestone | Status | Description |
|---|---|---|---|
| **Stage 0** | Hardware Detection & Project Foundation | **Complete** | Structure, packaging, config, detection, simulation mode, and unit tests. |
| **Stage 1** | RF TX/RX | Planned | Continuous test tone TX, RX power, RSSI, noise floor, SNR calculation. |
| **Stage 2** | BPSK | Planned | BPSK mapper, AWGN simulation, BER verification. |
| **Stage 3** | QPSK | Planned | Gray-coded QPSK mapper/demapper, EVM & BER diagnostics. |
| **Stage 4** | OFDM | Planned | FFT/IFFT 64/16, pilot subcarriers, coarse/fine sync, channel equalizer. |
| **Stage 5** | Packet Modem | Planned | Preamble, header, sequencing, CRC, and FEC. |
| **Stage 6** | UDP Transport | Planned | UDP socket over SDR packet modem, throughput/loss benchmarking. |
| **Stage 7** | TUN/TAP IP Interface | Planned | Virtual network interface `radio0`, ICMP ping between nodes. |
| **Stage 8** | Mesh Network | Roadmap | Ad-hoc mesh routing (Babel / BATMAN-adv). |
| **Stage 9** | FHSS | Roadmap | Configurable pseudo-random frequency hopping spread spectrum. |

---

## 9. Documentation

- [Step-by-Step Ping Guide: Windows PC to Raspberry Pi](STEP_PING_WINDOWS_TO_PI.md) ([Interactive HTML](STEP_PING_WINDOWS_TO_PI.html))
- [Step-by-Step Ping Guide: Mac to Raspberry Pi](STEP_PING_MAC_TO_PI.md) ([Interactive HTML](STEP_PING_MAC_TO_PI.html))
- [Interactive SDR Simulator & Dual Terminal](preview.html)
- [Command Cheat Sheet](command.md)
- [Architecture Overview](docs/architecture.md)
- [DSP Pipeline Guide](docs/dsp.md)
- [Packet Protocol Specification](docs/protocol.md)
- [Networking & TUN/TAP](docs/networking.md)
- [Testing & Verification](docs/testing.md)
- [Hardware & Driver Troubleshooting](docs/troubleshooting.md)
