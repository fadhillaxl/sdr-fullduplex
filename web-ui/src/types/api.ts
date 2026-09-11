export interface LinkStatus {
  is_running: boolean;
  interface_name?: string | null;
  local_ip?: string | null;
  peer_ip?: string | null;
  node_id?: number | null;
  peer_node_id?: number | null;
  tx_freq_hz?: number | null;
  rx_freq_hz?: number | null;
  duplex_mode?: string | null;
  modulation?: string | null;
  device_uri?: string | null;
  mode: "HARDWARE" | "SIMULATION" | "IDLE" | string;
}

export interface Telemetry {
  tx_packets: number;
  rx_packets: number;
  crc_errors: number;
  per_pct: number;
  tx_bytes: number;
  rx_bytes: number;
  throughput_kbps: number;
  rssi_dbfs: number;
  snr_db: number;
  cfo_hz: number;
  evm_pct: number;
  raw_telemetry_text?: string;
}

export interface DeviceInfo {
  status: "CONNECTED" | "NOT FOUND" | "SIMULATION" | string;
  uri: string;
  model: string;
  tx_channels: string;
  rx_channels: string;
  sample_rate: string;
  error_message?: string | null;
  troubleshooting?: string | null;
}

export interface DetectResponse {
  status: string;
  message: string;
  details?: {
    candidate_uris?: string[];
    detected_uri?: string | null;
    status?: string;
    model?: string;
  };
}

export interface StartLinkPayload {
  ip_cidr: string;
  peer_ip?: string;
  freq: number;
  tx_freq?: number | null;
  rx_freq?: number | null;
  fdd: boolean;
  tx_gain: number;
  rx_gain: number;
  modulation: string;
  mtu: number;
  uri?: string;
  simulation: boolean;
}

export interface PingResponse {
  success: boolean;
  target: string;
  transmitted: number;
  received: number;
  packet_loss_pct: number;
  rtt_min_ms?: number | null;
  rtt_avg_ms?: number | null;
  rtt_max_ms?: number | null;
  rtt_mdev_ms?: number | null;
  raw_output: string;
}

export interface AntennaScanPoint {
  freq_hz: number;
  freq_label: string;
  band_name: string;
  rssi_dbfs: number;
  snr_db: number;
  noise_floor_dbfs: number;
}

export interface AntennaScanResponse {
  status: string;
  result_text: string;
  antenna_type: string;
  confidence_pct: number;
  summary: string;
  recommendation: string;
  measurements: AntennaScanPoint[];
  timestamp: number;
}

export interface ActionResponse {
  status: string;
  message: string;
  details?: Record<string, any>;
}
