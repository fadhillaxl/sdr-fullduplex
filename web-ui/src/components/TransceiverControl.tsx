"use client";

import React, { useState } from "react";
import { 
  Play, 
  Square, 
  Sparkles, 
  Radio, 
  Sliders, 
  Wifi, 
  Settings2, 
  CheckCircle2, 
  AlertTriangle,
  RefreshCw,
  Zap,
  Globe
} from "lucide-react";
import { LinkStatus, StartLinkPayload } from "@/types/api";
import { detectDevices, startLink, stopLink } from "@/lib/api";

interface TransceiverControlProps {
  baseUrl: string;
  linkStatus: LinkStatus | null;
  onLinkStateChange: () => void;
}

export const TransceiverControl: React.FC<TransceiverControlProps> = ({
  baseUrl,
  linkStatus,
  onLinkStateChange,
}) => {
  // Form State
  const [deviceMode, setDeviceMode] = useState<"usb" | "ip" | "simulation">("usb");
  const [uri, setUri] = useState<string>("usb:1.4.5");
  const [freqMhz, setFreqMhz] = useState<number>(2400.0);
  const [isFdd, setIsFdd] = useState<boolean>(false);
  const [txGain, setTxGain] = useState<number>(-1);
  const [rxGain, setRxGain] = useState<number>(56);
  const [modulation, setModulation] = useState<string>("bpsk");
  const [ipCidr, setIpCidr] = useState<string>("192.168.30.3/24");
  const [peerIp, setPeerIp] = useState<string>("192.168.30.1");
  const [mtu, setMtu] = useState<number>(600);

  // Status & Feedback State
  const [isDetecting, setIsDetecting] = useState<boolean>(false);
  const [detectResult, setDetectResult] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isRunning = linkStatus?.is_running ?? false;

  // Auto-Detect SDR Devices
  const handleAutoDetect = async () => {
    setIsDetecting(true);
    setDetectResult(null);
    setErrorMessage(null);
    try {
      const res = await detectDevices(baseUrl);
      if (res.details?.detected_uri) {
        setUri(res.details.detected_uri);
        if (res.details.detected_uri.startsWith("ip:")) {
          setDeviceMode("ip");
        } else {
          setDeviceMode("usb");
        }
        setDetectResult(`Detected: ${res.details.detected_uri} (${res.details.model || "Pluto"})`);
      } else if (res.details?.candidate_uris && res.details.candidate_uris.length > 0) {
        setUri(res.details.candidate_uris[0]);
        setDetectResult(`Candidate: ${res.details.candidate_uris[0]}`);
      } else {
        setDetectResult("No physical Pluto SDR found on USB or default IPs.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Device detection failed");
    } finally {
      setIsDetecting(false);
    }
  };

  // Start Link Transceiver
  const handleStartLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const payload: StartLinkPayload = {
        ip_cidr: ipCidr,
        peer_ip: peerIp,
        freq: Math.round(freqMhz * 1_000_000),
        fdd: isFdd,
        tx_gain: txGain,
        rx_gain: rxGain,
        modulation: modulation.toLowerCase(),
        mtu: mtu,
        uri: deviceMode === "simulation" ? undefined : uri,
        simulation: deviceMode === "simulation",
      };

      const res = await startLink(baseUrl, payload);
      setSuccessMessage(res.message || "IP Radio link started successfully!");
      onLinkStateChange();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to start IP Radio link");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Stop Link Transceiver
  const handleStopLink = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await stopLink(baseUrl);
      setSuccessMessage(res.message || "IP Radio link disengaged.");
      onLinkStateChange();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to stop link");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel p-5 border border-white/10 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white font-sans">
              TRANSCEIVER LINK CONTROLLER
            </h2>
            <p className="text-xs text-slate-400 font-mono-code">
              Configure Pluto SDR Physical Carrier, RF Front-End & Virtual TUN
            </p>
          </div>
        </div>

        {/* Current status pill */}
        <div className="flex items-center gap-2">
          {isRunning ? (
            <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-mono-code flex items-center gap-1.5 font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              ONLINE ({linkStatus?.interface_name})
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 border border-white/10 text-xs font-mono-code flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-500" />
              STANDBY
            </span>
          )}
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="mb-4 p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs font-mono-code flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-xs font-mono-code flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Control Form */}
      <form onSubmit={handleStartLink} className="space-y-4 font-mono-code text-xs">
        
        {/* SDR Target & Hardware Probe Row */}
        <div className="p-4 rounded-xl bg-black/40 border border-white/10 space-y-3">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <span className="text-slate-300 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-blue-400" /> SDR Device Selection
            </span>
            
            {/* Auto-detect button */}
            <button
              type="button"
              onClick={handleAutoDetect}
              disabled={isDetecting || isRunning}
              className="px-3 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 text-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isDetecting ? "animate-spin text-cyan-400" : ""}`} />
              <span>{isDetecting ? "Scanning..." : "⚡ Auto-Detect SDR"}</span>
            </button>
          </div>

          {/* Mode Tabs */}
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => { setDeviceMode("usb"); if (!uri.startsWith("usb:")) setUri("usb:1.4.5"); }}
              className={`py-2 px-3 rounded-lg border text-center transition-all ${
                deviceMode === "usb"
                  ? "bg-blue-600/30 border-blue-500 text-white font-semibold"
                  : "bg-black/30 border-white/10 text-slate-400 hover:text-slate-200"
              }`}
            >
              USB Hardware
            </button>
            <button
              type="button"
              onClick={() => { setDeviceMode("ip"); if (!uri.startsWith("ip:")) setUri("ip:192.168.2.1"); }}
              className={`py-2 px-3 rounded-lg border text-center transition-all ${
                deviceMode === "ip"
                  ? "bg-blue-600/30 border-blue-500 text-white font-semibold"
                  : "bg-black/30 border-white/10 text-slate-400 hover:text-slate-200"
              }`}
            >
              IP Network
            </button>
            <button
              type="button"
              onClick={() => setDeviceMode("simulation")}
              className={`py-2 px-3 rounded-lg border text-center transition-all ${
                deviceMode === "simulation"
                  ? "bg-purple-600/30 border-purple-500 text-white font-semibold"
                  : "bg-black/30 border-white/10 text-slate-400 hover:text-slate-200"
              }`}
            >
              Simulation Mode
            </button>
          </div>

          {/* URI Input Field */}
          {deviceMode !== "simulation" ? (
            <div className="space-y-1">
              <label className="text-slate-400 text-[11px]">Pluto SDR Device URI</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={uri}
                  onChange={(e) => setUri(e.target.value)}
                  disabled={isRunning}
                  placeholder={deviceMode === "usb" ? "usb:1.4.5" : "ip:192.168.2.1"}
                  className="flex-1 bg-black/60 border border-white/15 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setUri(deviceMode === "usb" ? "usb:1.4.5" : "ip:192.168.99.240")}
                  disabled={isRunning}
                  className="px-2.5 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-slate-400 border border-white/10 text-[11px]"
                  title="Preset URI"
                >
                  Preset
                </button>
              </div>
              {detectResult && (
                <p className="text-[11px] text-cyan-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-cyan-400" /> {detectResult}
                </p>
              )}
            </div>
          ) : (
            <div className="p-2.5 rounded-lg bg-purple-950/20 border border-purple-500/20 text-purple-300 text-[11px]">
              Virtual Software Modem loopback. No physical SDR or antenna required.
            </div>
          )}
        </div>

        {/* RF Carrier & Duplex Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          
          {/* Frequency & Presets */}
          <div className="p-3.5 rounded-xl bg-black/30 border border-white/10 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-slate-300 font-semibold text-[11px]">RF Carrier Frequency</label>
              <span className="text-cyan-400 font-bold">{freqMhz.toFixed(1)} MHz</span>
            </div>
            <input
              type="number"
              step="0.1"
              value={freqMhz}
              onChange={(e) => setFreqMhz(Number(e.target.value))}
              disabled={isRunning}
              className="w-full bg-black/60 border border-white/15 rounded-lg px-3 py-1.5 text-slate-100 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
            {/* Quick frequency presets */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {[
                { label: "2.4 GHz", val: 2400.0 },
                { label: "915 MHz", val: 915.0 },
                { label: "433 MHz", val: 433.0 },
                { label: "5.8 GHz", val: 5800.0 },
              ].map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => setFreqMhz(preset.val)}
                  disabled={isRunning}
                  className={`px-2 py-0.5 rounded text-[10px] border ${
                    freqMhz === preset.val
                      ? "bg-blue-600/40 text-blue-300 border-blue-500/50"
                      : "bg-white/5 text-slate-400 border-white/10 hover:text-white"
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Duplex Mode & Modulation */}
          <div className="p-3.5 rounded-xl bg-black/30 border border-white/10 space-y-2">
            <label className="text-slate-300 font-semibold text-[11px]">Duplex & Modulation</label>
            
            <div className="grid grid-cols-2 gap-2 pt-1">
              {/* Duplex switch */}
              <button
                type="button"
                onClick={() => setIsFdd(!isFdd)}
                disabled={isRunning}
                className={`py-1.5 px-2 rounded-lg border text-center transition-all text-xs ${
                  isFdd
                    ? "bg-cyan-600/30 border-cyan-500 text-cyan-300 font-semibold"
                    : "bg-black/40 border-white/10 text-slate-400"
                }`}
              >
                {isFdd ? "FDD (Split Freq)" : "TDD (Single Freq)"}
              </button>

              {/* Modulation */}
              <select
                value={modulation}
                onChange={(e) => setModulation(e.target.value)}
                disabled={isRunning}
                className="bg-black/60 border border-white/15 rounded-lg px-2 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500 text-xs disabled:opacity-50 uppercase"
              >
                <option value="bpsk">BPSK (Robust)</option>
                <option value="qpsk">QPSK (2x Speed)</option>
              </select>
            </div>

            <p className="text-[10px] text-slate-500 pt-1">
              {isFdd ? "FDD provides full duplex with 2 MHz separation." : "TDD shares carrier frequency for low-complexity links."}
            </p>
          </div>
        </div>

        {/* Hardware Gain Sliders Row */}
        <div className="p-3.5 rounded-xl bg-black/30 border border-white/10 space-y-3">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300 font-semibold">RF Front-End Gain Calibration</span>
            <span className="text-slate-400">Pluto Hardware Dynamic Range</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* TX Attenuation */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400">TX Attenuation:</span>
                <span className="text-cyan-400 font-bold">{txGain} dB (0 is max)</span>
              </div>
              <input
                type="range"
                min="-89"
                max="0"
                value={txGain}
                onChange={(e) => setTxGain(Number(e.target.value))}
                disabled={isRunning}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            {/* RX Gain */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400">RX Hardware Gain:</span>
                <span className="text-emerald-400 font-bold">{rxGain} dB</span>
              </div>
              <input
                type="range"
                min="0"
                max="73"
                value={rxGain}
                onChange={(e) => setRxGain(Number(e.target.value))}
                disabled={isRunning}
                className="w-full accent-emerald-500 cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* TUN Network IP Configuration */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-black/30 border border-white/10">
          <div>
            <label className="text-slate-400 text-[11px]">Local IP / CIDR</label>
            <input
              type="text"
              value={ipCidr}
              onChange={(e) => setIpCidr(e.target.value)}
              disabled={isRunning}
              className="w-full bg-black/60 border border-white/15 rounded-lg px-2.5 py-1.5 text-slate-200 mt-1 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
          </div>

          <div>
            <label className="text-slate-400 text-[11px]">Peer Target IP</label>
            <input
              type="text"
              value={peerIp}
              onChange={(e) => setPeerIp(e.target.value)}
              disabled={isRunning}
              className="w-full bg-black/60 border border-white/15 rounded-lg px-2.5 py-1.5 text-slate-200 mt-1 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
          </div>

          <div>
            <label className="text-slate-400 text-[11px]">Interface MTU</label>
            <input
              type="number"
              value={mtu}
              onChange={(e) => setMtu(Number(e.target.value))}
              disabled={isRunning}
              className="w-full bg-black/60 border border-white/15 rounded-lg px-2.5 py-1.5 text-slate-200 mt-1 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />
          </div>
        </div>

        {/* Action Buttons: Engage / Disengage */}
        <div className="pt-2 flex items-center gap-3">
          {!isRunning ? (
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(59,130,246,0.4)] transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Play className="w-4 h-4 fill-white" />
              )}
              <span>ENGAGE RF TRANSCEIVER LINK</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleStopLink}
              disabled={isSubmitting}
              className="flex-1 py-3 px-4 rounded-xl bg-rose-600/90 hover:bg-rose-500 text-white font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(239,68,68,0.4)] transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Square className="w-4 h-4 fill-white" />
              )}
              <span>DISENGAGE RF LINK</span>
            </button>
          )}
        </div>
      </form>
    </div>
  );
};
