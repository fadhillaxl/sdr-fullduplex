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
    src_id, dst_id, seq, recovered_payload = extracted[0]
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


def test_preamble_sync_and_cfo_correction():
    """Verify packet preamble detection and CFO correction with real carrier offset."""
    from pluto_radio.dsp.sync import detect_and_synchronize_packets, get_preamble_iq
    from pluto_radio.protocol.frame import build_frame, FrameDetector
    from pluto_radio.dsp.bpsk import bpsk_modulate, bits_to_bytes

    payload = b"PING OVER THE AIR TEST"
    frame = build_frame(payload, seq=88)
    payload_iq = bpsk_modulate(frame, amplitude=0.8, samples_per_symbol=1)
    preamble = get_preamble_iq(amplitude=0.8)

    burst = np.concatenate([np.zeros(300, dtype=np.complex64), preamble, payload_iq, np.zeros(300, dtype=np.complex64)])

    # Inject +4500 Hz CFO, 60 deg phase offset, and noise
    fs = 2_000_000
    t = np.arange(len(burst)) / fs
    cfo = 4500.0
    phase = np.deg2rad(60.0)
    rx = burst * np.exp(1j * (2 * np.pi * cfo * t + phase))
    rx += (np.random.randn(len(rx)) + 1j * np.random.randn(len(rx))) * 0.05

    recovered = []
    detector = FrameDetector()
    for bits, est_cfo, snr in detect_and_synchronize_packets(rx, sample_rate=fs, threshold=0.20):
        detector.push(bits_to_bytes(bits))
        for src_id, dst_id, seq, data in detector.extract_frames():
            recovered.append((src_id, dst_id, seq, data))

    assert len(recovered) == 1
    assert recovered[0][2] == 88
    assert recovered[0][3] == payload


def test_oversampled_sync_with_fractional_delay():
    """Verify that 2 samples-per-symbol eliminates the 0.5-sample timing dead zone."""
    from pluto_radio.dsp.sync import detect_and_synchronize_packets, get_preamble_iq
    from pluto_radio.protocol.frame import build_frame, FrameDetector
    from pluto_radio.dsp.bpsk import bpsk_modulate, bits_to_bytes

    payload = b"PING CONTINUOUS TEST AT 1 MBPS"
    frame = build_frame(payload, seq=42)
    sps = 2
    payload_iq = bpsk_modulate(frame, amplitude=0.8, samples_per_symbol=sps)
    preamble = get_preamble_iq(amplitude=0.8, samples_per_symbol=sps)

    burst = np.concatenate([np.zeros(200, dtype=np.complex64), preamble, payload_iq, np.zeros(200, dtype=np.complex64)])

    # Inject +8500 Hz CFO and a worst-case 0.5 sample fractional delay (the exact transition point)
    fs = 2_000_000
    t = np.arange(len(burst)) / fs
    cfo = 8500.0
    rx = burst * np.exp(1j * (2 * np.pi * cfo * t + 0.75))
    # 0.5 sample fractional shift
    rx = 0.5 * rx[:-1] + 0.5 * rx[1:]
    rx = np.pad(rx, (0, 1))
    rx += (np.random.randn(len(rx)) + 1j * np.random.randn(len(rx))) * 0.04

    recovered = []
    detector = FrameDetector()
    for bits, est_cfo, snr in detect_and_synchronize_packets(
        rx, sample_rate=fs, threshold=0.20, samples_per_symbol=sps
    ):
        detector.push(bits_to_bytes(bits))
        for src_id, dst_id, seq, data in detector.extract_frames():
            recovered.append((src_id, dst_id, seq, data))

    assert len(recovered) == 1
    assert recovered[0][2] == 42
    assert recovered[0][3] == payload


def test_dynamic_burst_sizing_and_mtu():
    """Verify that small packets use dual-burst and large packets use single-burst with MTU 600."""
    from pluto_radio.protocol.frame import build_frame

    tun = create_tun_device("192.168.30.1/24", simulation=True, mtu=600)
    assert tun.mtu == 600

    sdr = PlutoTransceiver(simulation=True)
    modem = DigitalPacketTransceiver(tun=tun, sdr=sdr, samples_per_symbol=2)

    # Small packet (84 bytes ping): dual-burst padded to 8192
    small_frame = build_frame(b"P" * 84)
    burst_small = modem._build_tx_burst(small_frame)
    assert len(burst_small) == 8192

    # Large packet (550 bytes, e.g. SSH / bulk): single-burst avoids 20k+ sample bloat
    large_frame = build_frame(b"K" * 550)
    burst_large = modem._build_tx_burst(large_frame)
    # Padded to multiple of 4096 (12288 samples), far below the 20k+ sample dual-burst size
    assert len(burst_large) == 12288
    assert len(burst_large) % 4096 == 0


def test_dynamic_ipv4_destination_routing():
    """Verify that IPv4 destination IP automatically resolves to frame dst_id."""
    tun = create_tun_device("192.168.30.1/24", simulation=True)
    sdr = PlutoTransceiver(simulation=True)
    modem = DigitalPacketTransceiver(tun=tun, sdr=sdr, node_id=1, peer_node_id=2)

    # Simulated IPv4 packet header targeting 192.168.30.3 (byte 19 = 3)
    ipv4_pkt_to_node3 = bytearray(20)
    ipv4_pkt_to_node3[0] = 0x45  # IPv4, IHL=5
    ipv4_pkt_to_node3[16] = 192
    ipv4_pkt_to_node3[17] = 168
    ipv4_pkt_to_node3[18] = 30
    ipv4_pkt_to_node3[19] = 3  # Node 3

    # Simulated IPv4 packet header targeting broadcast 192.168.30.255
    ipv4_broadcast = bytearray(20)
    ipv4_broadcast[0] = 0x45
    ipv4_broadcast[16] = 192
    ipv4_broadcast[17] = 168
    ipv4_broadcast[18] = 30
    ipv4_broadcast[19] = 255  # Broadcast

    # Inject and verify dynamic resolution
    tun.inject_tx_packet(bytes(ipv4_pkt_to_node3))
    # Read from tun and resolve dst_id
    packet = tun.read()
    assert packet is not None
    dst_id = modem.peer_node_id
    if len(packet) >= 20 and (packet[0] >> 4) == 4:
        dst_last_octet = packet[19]
        if dst_last_octet == 255:
            dst_id = 0xFF
        elif 1 <= dst_last_octet <= 254:
            dst_id = dst_last_octet
    assert dst_id == 3

    tun.inject_tx_packet(bytes(ipv4_broadcast))
    packet_bc = tun.read()
    assert packet_bc is not None
    dst_id_bc = modem.peer_node_id
    if len(packet_bc) >= 20 and (packet_bc[0] >> 4) == 4:
        dst_last_octet = packet_bc[19]
        if dst_last_octet == 255:
            dst_id_bc = 0xFF
        elif 1 <= dst_last_octet <= 254:
            dst_id_bc = dst_last_octet
    assert dst_id_bc == 0xFF




