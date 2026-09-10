"""Automated test suite for Stages 2-7: BPSK, QPSK, Packet Framing, CRC32, and TUN Transceiver."""

import numpy as np
import pytest

from pluto_radio.dsp.bpsk import (
    bpsk_modulate,
    bpsk_demodulate,
    calculate_ber,
    bytes_to_bits,
    bits_to_bytes,
)
from pluto_radio.dsp.qpsk import (
    qpsk_modulate,
    qpsk_demodulate,
    calculate_evm,
    ascii_constellation,
)
from pluto_radio.dsp.channel import apply_awgn
from pluto_radio.protocol.crc import compute_crc32, verify_crc32
from pluto_radio.protocol.frame import build_frame, FrameDetector
from pluto_radio.network.tun import SimulatedTunDevice, create_tun_device
from pluto_radio.hardware.pluto import PlutoTransceiver
from pluto_radio.protocol.transceiver import DigitalPacketTransceiver


def test_bpsk_modulation_demodulation():
    """Verify BPSK modulation and demodulation has 0 BER on clean channel."""
    rng = np.random.default_rng(42)
    tx_bits = rng.integers(0, 2, size=1024, dtype=np.uint8)

    symbols = bpsk_modulate(tx_bits, amplitude=0.8, samples_per_symbol=4)
    assert len(symbols) == 1024 * 4
    assert symbols.dtype == np.complex64

    rx_bits = bpsk_demodulate(symbols, samples_per_symbol=4)
    ber = calculate_ber(tx_bits, rx_bits)
    assert ber == 0.0


def test_bpsk_awgn_ber():
    """Verify BPSK BER under AWGN noise channel."""
    rng = np.random.default_rng(123)
    tx_bits = rng.integers(0, 2, size=2048, dtype=np.uint8)

    symbols = bpsk_modulate(tx_bits, amplitude=0.8, samples_per_symbol=1)

    # High SNR -> BER should be 0.0
    noisy_high_snr = apply_awgn(symbols, snr_db=25.0)
    rx_bits_clean = bpsk_demodulate(noisy_high_snr, samples_per_symbol=1)
    assert calculate_ber(tx_bits, rx_bits_clean) == 0.0

    # Low SNR -> BER should show non-zero bit errors
    noisy_low_snr = apply_awgn(symbols, snr_db=0.0)
    rx_bits_noisy = bpsk_demodulate(noisy_low_snr, samples_per_symbol=1)
    ber_noisy = calculate_ber(tx_bits, rx_bits_noisy)
    assert ber_noisy > 0.02


def test_qpsk_modulation_demodulation_and_evm():
    """Verify Gray QPSK modulation, demodulation, and EVM metric."""
    rng = np.random.default_rng(999)
    tx_bits = rng.integers(0, 2, size=2048, dtype=np.uint8)

    symbols = qpsk_modulate(tx_bits, amplitude=0.8, samples_per_symbol=4)
    assert len(symbols) == 1024 * 4
    assert symbols.dtype == np.complex64

    # EVM on ideal signal should be 0.0%
    evm_clean = calculate_evm(symbols, symbols)
    assert evm_clean == 0.0

    rx_bits = qpsk_demodulate(symbols, samples_per_symbol=4)
    ber = calculate_ber(tx_bits, rx_bits)
    assert ber == 0.0

    # Test ASCII constellation diagram
    diagram = ascii_constellation(symbols)
    assert "Q" in diagram
    assert "I" in diagram
    assert "●" in diagram


def test_packet_framing_and_crc_verification():
    """Verify packet encapsulation, stream correlation, and CRC error rejection."""
    payload = b"PING ECHO REQUEST: Hello Pluto SDR IP Network!"
    seq_num = 101

    frame = build_frame(payload, seq=seq_num)
    assert len(frame) > len(payload)

    # Correlator should extract payload cleanly
    detector = FrameDetector()
    detector.push(b"\x00\x00\xff" + frame + b"\x11\x22")
    extracted = list(detector.extract_frames())
    assert len(extracted) == 1
    seq, recovered_payload = extracted[0]
    assert seq == seq_num
    assert recovered_payload == payload

    # Test CRC corruption rejection: flip 1 bit in payload
    corrupted_frame = bytearray(frame)
    corrupted_frame[12] ^= 0x01

    detector.reset()
    detector.push(bytes(corrupted_frame))
    extracted_corrupt = list(detector.extract_frames())
    assert len(extracted_corrupt) == 0  # Corrupted packet discarded


def test_simulated_tun_device_and_transceiver_loopback():
    """Verify end-to-end IP packet loop through TUN device and digital modem."""
    tun = SimulatedTunDevice(ip_cidr="192.168.50.1/24", peer_ip="192.168.50.2")
    tun.open()
    assert tun.is_open
    assert tun.local_ip == "192.168.50.1"
    assert tun.peer_ip == "192.168.50.2"

    sdr = PlutoTransceiver(simulation=True)
    modem = DigitalPacketTransceiver(tun=tun, sdr=sdr, modulation="bpsk", samples_per_symbol=2)
    modem.start()

    # Create synthetic IP ICMP packet (84 bytes standard ping)
    fake_ip_packet = b"\x45\x00\x00\x54" + b"\xaa" * 80
    tun.inject_tx_packet(fake_ip_packet)

    import time
    time.sleep(0.3)

    modem.stop()
    assert modem.stats.tx_packets >= 1
    assert "PLUTO RADIO TELEMETRY" in modem.stats.format_telemetry()
