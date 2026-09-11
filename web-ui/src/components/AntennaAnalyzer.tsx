"use client";

import React, { useState } from "react";
import { 
  Radio, 
  Sparkles, 
  CheckCircle2, 
  ShieldCheck, 
  AlertTriangle, 
  RefreshCw, 
  Activity, 
  Compass, 
  Zap,
  Info
} from "lucide-react";
import { AntennaScanResponse } from "@/types/api";
import { scanAntenna } from "@/lib/api";

interface AntennaAnalyzerProps {
  baseUrl: string;
}

export const AntennaAnalyzer: React.FC<AntennaAnalyzerProps> = ({ baseUrl }) => {
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [gainDb, setGainDb] = useState<number>(60);
  const [profile, setProfile] = useState<string>("auto");
  const [scanResult, setScanResult] = useState<AntennaScanResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleScan = async () => {
    setIsScanning(true);
    setErrorMessage(null);

    const isSimulation = profile !== "auto";
    const simProfile = isSimulation ? profile : undefined;

    try {
      const res = await scanAntenna(baseUrl, isSimulation, gainDb, simProfile);
      setScanResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || "Antenna detection sweep failed");
    } finally {
      setIsScanning(false);
    }
  };

  // Helper to get signal bar height/percentage
  const getBarPct = (rssi: number) => {
    // RSSI from -90 to -20 dBFS
    return Math.min(100, Math.max(8, ((rssi + 90) / 70) * 100));
  };

  const getBarColor = (rssi: number) => {
    if (rssi > -42) return "bg-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.5)]";
    if (rssi > -55) return "bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.4)]";
    if (rssi > -70) return "bg-amber-400";
    return "bg-slate-600";
  };

  return (
    <div className="glass-panel p-5 border border-white/10 space-y-5 relative overflow-hidden">
      {/* Background Radar Line on Scanning */}
      {isScanning && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
          <div className="w-96 h-96 rounded-full border-2 border-dashed border-cyan-400 animate-radar" />
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
            <Radio className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white font-sans">
              PASSIVE MULTI-BAND ANTENNA ANALYZER
            </h2>
            <p className="text-xs text-slate-400 font-mono-code">
              Automated 4-Point Frequency Sweep Classification (433M / 900M / 2.4G / 5.8G)
            </p>
          </div>
        </div>

        {/* Scan Button */}
        <button
          type="button"
          onClick={handleScan}
          disabled={isScanning}
          className="py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-[0_0_15px_rgba(99,102,241,0.4)] transition-all flex items-center gap-2 disabled:opacity-50 font-mono-code"
        >
          {isScanning ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-white" />
          ) : (
            <Sparkles className="w-3.5 h-3.5" />
          )}
          <span>{isScanning ? "SWEEPING SPECTRUM..." : "SCAN & DETECT ANTENNA"}</span>
        </button>
      </div>

      {/* Mode & Gain Selection Bar */}
      <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 font-mono-code text-xs">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <label className="text-slate-400 text-[11px] shrink-0">Sweep Source:</label>
          <select
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            disabled={isScanning}
            className="flex-1 sm:flex-none bg-black/70 border border-white/15 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
          >
            <option value="auto">📡 Real Pluto SDR Hardware Sweep</option>
            <option value="wifi_24">🧪 Simulation: Wi-Fi 2.4 GHz Antenna</option>
            <option value="vhf_uhf">🧪 Simulation: VHF/UHF 433 MHz Antenna</option>
            <option value="lte_multiband">🧪 Simulation: LTE / Cellular Multiband</option>
            <option value="wifi_58">🧪 Simulation: Wi-Fi 5.8 GHz Antenna</option>
            <option value="uwb">🧪 Simulation: UWB / Ultra-Wideband</option>
            <option value="disconnected">🧪 Simulation: Disconnected / No Antenna</option>
          </select>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <span className="text-slate-400 text-[11px] shrink-0">Calibration RX Gain:</span>
          <span className="text-indigo-400 font-bold">{gainDb} dB</span>
          <input
            type="range"
            min="20"
            max="73"
            value={gainDb}
            onChange={(e) => setGainDb(Number(e.target.value))}
            disabled={isScanning}
            className="w-28 accent-indigo-500 cursor-pointer"
          />
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs font-mono-code flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 4-Band Spectral Meter Display */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono-code">
        {[
          { key: 0, label: "433 MHz", band: "VHF / UHF", defaultRssi: -72.0, defaultSnr: 4.2 },
          { key: 1, label: "900 MHz", band: "Cellular Low-Band", defaultRssi: -68.5, defaultSnr: 5.8 },
          { key: 2, label: "2440 MHz", band: "Wi-Fi 2.4 GHz", defaultRssi: -35.2, defaultSnr: 24.5 },
          { key: 3, label: "5800 MHz", band: "Wi-Fi 5.8 GHz", defaultRssi: -78.0, defaultSnr: 2.1 },
        ].map((defaultBand, idx) => {
          const pt = scanResult?.measurements[idx];
          const rssi = pt ? pt.rssi_dbfs : defaultBand.defaultRssi;
          const snr = pt ? pt.snr_db : defaultBand.defaultSnr;
          const isStrong = rssi > -42;

          return (
            <div
              key={defaultBand.label}
              className={`p-3.5 rounded-xl border flex flex-col justify-between transition-all ${
                isStrong
                  ? "bg-indigo-950/30 border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.2)]"
                  : "bg-black/40 border-white/10"
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">{defaultBand.label}</span>
                  {isStrong && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  )}
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">{defaultBand.band}</p>
              </div>

              {/* Spectral Vertical Level Gauge */}
              <div className="my-3 py-2 px-3 rounded-lg bg-black/60 border border-white/5 flex items-end justify-between h-24">
                <div className="flex flex-col justify-between h-full text-[9px] text-slate-500 pb-1">
                  <span>-20</span>
                  <span>-50</span>
                  <span>-80</span>
                </div>

                {/* Level bar */}
                <div className="w-8 bg-slate-800 rounded-t-md h-full flex items-end p-0.5">
                  <div
                    className={`w-full rounded-t transition-all duration-500 ${getBarColor(rssi)}`}
                    style={{ height: `${getBarPct(rssi)}%` }}
                  />
                </div>

                {/* Numbers */}
                <div className="text-right">
                  <div className="text-xs font-bold text-white">{rssi.toFixed(1)}</div>
                  <span className="text-[10px] text-slate-400">dBFS</span>
                </div>
              </div>

              {/* Bottom Metrics */}
              <div className="flex items-center justify-between text-[11px] pt-1 border-t border-white/5">
                <span className="text-slate-400">SNR:</span>
                <span className={snr > 15 ? "text-emerald-400 font-bold" : "text-slate-300"}>
                  {snr.toFixed(1)} dB
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Antenna Classification Hero Result Banner */}
      {scanResult && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/60 via-blue-950/40 to-indigo-950/60 border border-indigo-500/40 space-y-2.5 font-mono-code">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <h3 className="text-sm font-bold text-white tracking-wide">
                {scanResult.result_text}
              </h3>
            </div>

            <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-bold">
              {scanResult.confidence_pct}% Confidence
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {scanResult.summary}
          </p>

          <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-start gap-2 text-[11px] text-indigo-200">
            <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <span>{scanResult.recommendation}</span>
          </div>
        </div>
      )}
    </div>
  );
};
