import {
  ActionResponse,
  AntennaScanResponse,
  DetectResponse,
  DeviceInfo,
  LinkStatus,
  PingResponse,
  StartLinkPayload,
  Telemetry,
} from "@/types/api";

export async function checkHealth(baseUrl: string): Promise<ActionResponse> {
  const res = await fetch(`${baseUrl}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return res.json();
}

export async function fetchLinkStatus(baseUrl: string): Promise<LinkStatus> {
  const res = await fetch(`${baseUrl}/api/link/status`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Status check failed: HTTP ${res.status}`);
  return res.json();
}

export async function fetchTelemetry(baseUrl: string): Promise<Telemetry> {
  const res = await fetch(`${baseUrl}/api/link/telemetry`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Telemetry fetch failed: HTTP ${res.status}`);
  return res.json();
}

export async function fetchDeviceInfo(
  baseUrl: string,
  uri?: string,
  simulation: boolean = false
): Promise<DeviceInfo> {
  const params = new URLSearchParams();
  if (uri) params.append("uri", uri);
  if (simulation) params.append("simulation", "true");

  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${baseUrl}/api/device/info${query}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Device probe failed: HTTP ${res.status}`);
  return res.json();
}

export async function detectDevices(baseUrl: string): Promise<DetectResponse> {
  const res = await fetch(`${baseUrl}/api/device/detect`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Device detection failed: HTTP ${res.status}`);
  return res.json();
}

export async function startLink(
  baseUrl: string,
  payload: StartLinkPayload
): Promise<ActionResponse> {
  const res = await fetch(`${baseUrl}/api/link/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Start link failed with HTTP ${res.status}`);
  }
  return data;
}

export async function stopLink(baseUrl: string): Promise<ActionResponse> {
  const res = await fetch(`${baseUrl}/api/link/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Stop link failed with HTTP ${res.status}`);
  }
  return data;
}

export async function sendPing(
  baseUrl: string,
  target: string,
  count: number = 4,
  interval: number = 0.5,
  timeout_sec: number = 6.0
): Promise<PingResponse> {
  const res = await fetch(`${baseUrl}/api/network/ping`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, count, interval, timeout_sec }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Ping failed with HTTP ${res.status}`);
  }
  return data;
}

export async function scanAntenna(
  baseUrl: string,
  simulation: boolean = false,
  gain_db: number = 60,
  simulated_profile?: string,
  uri?: string
): Promise<AntennaScanResponse> {
  const res = await fetch(`${baseUrl}/api/rf/antenna-scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      simulation,
      gain_db,
      simulated_profile: simulated_profile || null,
      uri: uri || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || `Antenna scan failed with HTTP ${res.status}`);
  }
  return data;
}
