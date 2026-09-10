# Testing & Verification Guide

## Automated Unit Testing

Run unit tests via pytest:

```bash
pytest tests/ -v
```

Tests cover:
- Configuration parsing and bounds validation (`test_config.py`).
- IIO and Pluto device probing, mock detection, and simulation mode (`test_detection.py`).
- CLI interface parser and execution paths (`test_cli.py`).

## Hardware Loopback Testing

Conducted test setup:
```text
Pluto TX -> 30dB Attenuator -> Pluto RX
```
Always use an attenuator to protect the AD9363/AD9364 receiver front-end from excessive input power.
