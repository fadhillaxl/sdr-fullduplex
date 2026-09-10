# Architecture Overview

## Layered Architecture

The Pluto+ SDR IP Radio is structured into clean, decoupled layers:

```text
Layer 5: Application / Linux IP Stack (ping, iperf, sockets)
Layer 4: Virtual Network Interface (radio0 TUN/TAP driver)
Layer 3: Transport & Framing (Packet framing, Sequence, CRC, FEC)
Layer 2: Modem DSP (QPSK/OFDM, Timing & Carrier Frequency Synchronization, Equalization)
Layer 1: Hardware Abstraction & IIO (pyadi-iio, libiio, AD9363/AD9364 transceiver)
```

## Modular Components

- `pluto_radio.hardware`: Handles physical discovery, IIO contexts, and simulation wrappers.
- `pluto_radio.dsp`: Signal processing algorithms (filters, mapper/demappers, FFT, synchronization).
- `pluto_radio.protocol`: Header serialization, CRC checksums, and forward error correction.
- `pluto_radio.network`: Socket transport and Linux kernel TUN device bridging.
- `pluto_radio.telemetry`: Runtime link statistics and health telemetry.
