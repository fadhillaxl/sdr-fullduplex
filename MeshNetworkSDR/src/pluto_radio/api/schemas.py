"""Pydantic data models and schemas for Pluto+ SDR REST API & Swagger UI."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class PlutoDeviceInfoSchema(BaseModel):
    """SDR hardware probe and diagnostic report."""

    status: str = Field(..., description="Connection status: CONNECTED, NOT FOUND, or SIMULATION", examples=["CONNECTED"])
    uri: str = Field(..., description="Target or detected device URI", examples=["ip:192.168.2.1"])
    model: str = Field(..., description="Hardware model name", examples=["Analog Devices ADALM-PLUTO"])
    tx_channels: str = Field(..., description="TX channel status", examples=["OK (1 channel)"])
    rx_channels: str = Field(..., description="RX channel status", examples=["OK (1 channel)"])
    sample_rate: str = Field(..., description="Configured sample rate", examples=["2,000,000 SPS (2.00 MSPS)"])
    error_message: Optional[str] = Field(None, description="Error reason if probe failed")
    troubleshooting: Optional[str] = Field(None, description="Troubleshooting guide for hardware issues")


class RadioConfigSchema(BaseModel):
    """Radio hardware RF and baseband parameters."""

    uri: str = Field("ip:192.168.2.1", description="Default Pluto SDR URI", examples=["ip:192.168.2.1"])
    center_frequency: int = Field(2_400_000_000, description="Carrier frequency in Hz (2.4 GHz default for stock antennas)", examples=[2400000000])
    sample_rate: int = Field(2_000_000, description="ADC/DAC sample rate in SPS", examples=[2000000])
    bandwidth: int = Field(2_000_000, description="Analog RF filter bandwidth in Hz", examples=[2000000])
    tx_gain: int = Field(-1, description="TX attenuation gain in dB (-89 to 0)", examples=[-1])
    rx_gain: int = Field(56, description="RX hardware gain in dB (0 to 73)", examples=[56])
    rx_gain_mode: str = Field("manual", description="RX AGC mode: manual, slow_attack, or fast_attack", examples=["manual"])


class ModulationConfigSchema(BaseModel):
    """Digital modem modulation settings."""

    mode: str = Field("bpsk", description="Digital modulation mode: bpsk or qpsk", examples=["bpsk"])


class AppConfigSchema(BaseModel):
    """Global application configuration."""

    radio: RadioConfigSchema = Field(default_factory=RadioConfigSchema)
    modulation: ModulationConfigSchema = Field(default_factory=ModulationConfigSchema)
    mtu: int = Field(600, description="TUN interface MTU size", examples=[600])
    simulation_mode: bool = Field(False, description="Whether software simulation mode is active", examples=[False])


class ConfigUpdateSchema(BaseModel):
    """Parameters to update in radio configuration."""

    center_frequency: Optional[int] = Field(None, description="Carrier frequency in Hz", examples=[2400000000])
    sample_rate: Optional[int] = Field(None, description="Sample rate in SPS", examples=[2000000])
    bandwidth: Optional[int] = Field(None, description="Bandwidth in Hz", examples=[2000000])
    tx_gain: Optional[int] = Field(None, description="TX attenuation in dB (-89 to 0)", examples=[-1])
    rx_gain: Optional[int] = Field(None, description="RX gain in dB (0 to 73)", examples=[56])
    modulation: Optional[str] = Field(None, description="Modulation mode (bpsk/qpsk)", examples=["bpsk"])
    uri: Optional[str] = Field(None, description="Pluto URI override", examples=["ip:192.168.99.240"])


class RFMetricsSchema(BaseModel):
    """Physical layer spectrum and RF signal quality measurements."""

    rssi_dbfs: float = Field(..., description="Received Signal Strength Indicator in dBFS", examples=[-32.4])
    snr_db: float = Field(..., description="Estimated Signal-to-Noise Ratio in dB", examples=[28.5])
    evm_pct: float = Field(..., description="Error Vector Magnitude percentage", examples=[2.1])
    papr_db: float = Field(..., description="Peak-to-Average Power Ratio in dB", examples=[3.8])
    noise_floor_dbfs: float = Field(..., description="Estimated noise floor in dBFS", examples=[-68.2])
    carrier_freq_hz: int = Field(..., description="Carrier frequency at time of measurement", examples=[2400000000])
    sample_rate: int = Field(..., description="Sampling rate in SPS", examples=[2000000])
    timestamp: float = Field(..., description="Epoch timestamp of measurement", examples=[1726074000.0])


class StartLinkRequest(BaseModel):
    """Parameters for launching the IP Link transceiver bridging TUN with SDR."""

    ip_cidr: str = Field("192.168.30.1/24", description="IP address and subnet CIDR for local virtual radio0 interface", examples=["192.168.30.1/24"])
    peer_ip: Optional[str] = Field("192.168.30.2", description="Peer node IP address", examples=["192.168.30.2"])
    freq: int = Field(2_400_000_000, description="Base carrier frequency in Hz (2.4 GHz recommended for stock antennas)", examples=[2400000000])
    tx_freq: Optional[int] = Field(None, description="Explicit TX carrier frequency override in Hz (0 or null for auto FDD calculation)")
    rx_freq: Optional[int] = Field(None, description="Explicit RX carrier frequency override in Hz (0 or null for auto FDD calculation)")
    fdd: bool = Field(True, description="Enable FDD Full-Duplex (split TX/RX channels with 2 MHz separation)", examples=[True])
    tx_gain: int = Field(-1, description="TX attenuation in dB (0 is max power, -1 recommended)", examples=[-1])
    rx_gain: int = Field(56, description="RX hardware gain in dB (56 recommended for high sensitivity)", examples=[56])
    modulation: str = Field("bpsk", description="Digital modulation mode: bpsk or qpsk", examples=["bpsk"])
    mtu: int = Field(600, description="Virtual TUN network MTU", examples=[600])
    uri: Optional[str] = Field(None, description="Pluto SDR URI (e.g. ip:192.168.2.1 or ip:192.168.99.240)", examples=["ip:192.168.2.1"])
    simulation: bool = Field(False, description="Run in software simulation mode without physical SDR", examples=[False])


class LinkStatusSchema(BaseModel):
    """Active status of the TUN network interface and SDR digital packet modem."""

    is_running: bool = Field(..., description="True if IP radio link transceiver is active", examples=[True])
    interface_name: Optional[str] = Field(None, description="Virtual network interface name (e.g. radio0 or utun3)", examples=["radio0"])
    local_ip: Optional[str] = Field(None, description="Configured local IP address", examples=["192.168.30.1"])
    peer_ip: Optional[str] = Field(None, description="Peer node IP address", examples=["192.168.30.2"])
    node_id: Optional[int] = Field(None, description="Local SDR node ID", examples=[1])
    peer_node_id: Optional[int] = Field(None, description="Peer SDR node ID", examples=[2])
    tx_freq_hz: Optional[int] = Field(None, description="Active TX frequency in Hz", examples=[2400000000])
    rx_freq_hz: Optional[int] = Field(None, description="Active RX frequency in Hz", examples=[2402000000])
    duplex_mode: Optional[str] = Field(None, description="Duplex mode: FDD or TDD", examples=["FDD (Full Duplex - Split Freq)"])
    modulation: Optional[str] = Field(None, description="Active modulation scheme", examples=["BPSK"])
    device_uri: Optional[str] = Field(None, description="Pluto SDR URI in use", examples=["ip:192.168.2.1"])
    mode: str = Field("IDLE", description="Operational mode: HARDWARE, SIMULATION, or IDLE", examples=["HARDWARE"])


class TelemetrySchema(BaseModel):
    """Real-time packet statistics, error rates, and RF metrics."""

    tx_packets: int = Field(..., description="Total IP packets transmitted over RF", examples=[42])
    rx_packets: int = Field(..., description="Total valid IP packets received and delivered to TUN", examples=[39])
    crc_errors: int = Field(..., description="Total corrupted packet bursts rejected by CRC32", examples=[0])
    per_pct: float = Field(..., description="Packet Error Rate in percent", examples=[0.0])
    tx_bytes: int = Field(..., description="Total payload bytes transmitted", examples=[3528])
    rx_bytes: int = Field(..., description="Total payload bytes received", examples=[3276])
    throughput_kbps: float = Field(..., description="Instantaneous throughput in kbps", examples=[12.4])
    rssi_dbfs: float = Field(..., description="Latest RSSI in dBFS", examples=[-33.5])
    snr_db: float = Field(..., description="Latest SNR in dB", examples=[27.8])
    cfo_hz: float = Field(..., description="Carrier Frequency Offset in Hz", examples=[2380.5])
    evm_pct: float = Field(..., description="Error Vector Magnitude in percent", examples=[2.1])
    raw_telemetry_text: str = Field(..., description="Standardized telemetry text banner")


class PingRequest(BaseModel):
    """Parameters for running an ICMP IP ping test through the virtual radio0 interface."""

    target: str = Field("192.168.30.2", description="Target IP address to ping", examples=["192.168.30.2"])
    count: int = Field(4, description="Number of ICMP echo request packets to transmit", ge=1, le=50, examples=[4])
    interval: float = Field(0.5, description="Interval between packets in seconds", ge=0.2, le=5.0, examples=[0.5])
    timeout_sec: float = Field(6.0, description="Overall command timeout in seconds", examples=[6.0])


class PingResponse(BaseModel):
    """Result of ICMP ping test over the SDR IP link."""

    success: bool = Field(..., description="True if at least one ICMP reply was received", examples=[True])
    target: str = Field(..., description="Ping target IP address", examples=["192.168.30.2"])
    transmitted: int = Field(..., description="Packets transmitted", examples=[4])
    received: int = Field(..., description="Packets received", examples=[4])
    packet_loss_pct: float = Field(..., description="Packet loss percentage", examples=[0.0])
    rtt_min_ms: Optional[float] = Field(None, description="Minimum Round-Trip Time in ms", examples=[368.5])
    rtt_avg_ms: Optional[float] = Field(None, description="Average Round-Trip Time in ms", examples=[412.3])
    rtt_max_ms: Optional[float] = Field(None, description="Maximum Round-Trip Time in ms", examples=[460.1])
    rtt_mdev_ms: Optional[float] = Field(None, description="Standard deviation of RTT in ms", examples=[34.2])
    raw_output: str = Field(..., description="Raw output from system ping command")


class ToneTxRequest(BaseModel):
    """Parameters for transmitting a continuous CW RF tone for spectrum test / antenna tuning."""

    carrier_freq_hz: int = Field(2_400_000_000, description="Carrier frequency in Hz", examples=[2400000000])
    tone_freq_hz: float = Field(100_000.0, description="Baseband offset frequency in Hz", examples=[100000.0])
    gain_db: int = Field(-1, description="TX attenuation in dB (0 is max)", examples=[-1])
    amplitude: float = Field(0.8, description="Normalized tone amplitude (0.0 to 1.0)", examples=[0.8])
    uri: Optional[str] = Field(None, description="Pluto SDR URI override")
    simulation: bool = Field(False, description="Simulation mode")


class ActionResponse(BaseModel):
    """Standard operation success/failure response."""

    status: str = Field(..., description="Status string: 'ok' or 'error'", examples=["ok"])
    message: str = Field(..., description="Descriptive result message", examples=["IP Radio link started successfully"])
    details: Optional[dict[str, Any]] = Field(None, description="Additional contextual information")
