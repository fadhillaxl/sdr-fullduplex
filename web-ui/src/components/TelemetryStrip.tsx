"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Activity, 
  TrendingUp, 
  Wifi, 
  ShieldAlert, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Gauge, 
  Play, 
  Pause,
  RotateCcw
} from "lucide-react";
import { Telemetry } from "@/types/api";

interface TelemetryStripProps {
  telemetry: Telemetry | null;
  isRunning: boolean;
}

interface TelemetryPoint {
  time: string;
  rssi: number;
  snr: number;
  throughput: number;
}

export const TelemetryStrip: React.FC<TelemetryStripProps> = ({
  telemetry,
  isRunning,
}) => {
  const [history, setHistory] = useState<TelemetryPoint[]>([]);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const maxPoints = 35;

  // Append data point when telemetry changes
  useEffect(() => {
    if (!telemetry || isPaused) return;

    const newPoint: TelemetryPoint = {
      time: new Date().toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      rssi: telemetry.rssi_dbfs ?? -60,
      snr: telemetry.snr_db ?? 0,
      throughput: telemetry.throughput_kbps ?? 0,
    };

    setHistory((prev) => {
      const updated = [...prev, newPoint];
      if (updated.length > maxPoints) {
        return updated.slice(updated.length - maxPoints);
      }
      return updated;
    });
  }, [telemetry, isPaused]);

  // SVG Chart Dimensions
  const svgWidth = 700;
  const svgHeight = 160;
  const padding = { top: 20, right: 30, bottom: 25, left: 45 };
  const graphWidth = svgWidth - padding.left - padding.right;
  const graphHeight = svgHeight - padding.top - padding.bottom;

  // Scales
  // RSSI typically ranges from -80 to -10 dBFS
  const minRssi = -85;
  const maxRssi = -10;
  // SNR ranges from 0 to 35 dB
  const minSnr = 0;
  const maxSnr = 35;

  const getRssiY = (val: number) => {
    const clamped = Math.max(minRssi, Math.min(maxRssi, val));
    return padding.top + graphHeight - ((clamped - minRssi) / (maxRssi - minRssi)) * graphHeight;
  };

  const getSnrY = (val: number) => {
    const clamped = Math.max(minSnr, Math.min(maxSnr, val));
    return padding.top + graphHeight - ((clamped - minSnr) / (maxSnr - minSnr)) * graphHeight;
  };

  const getX = (index: number) => {
    if (history.length <= 1) return padding.left;
    return padding.left + (index / (maxPoints - 1)) * graphWidth;
  };

  // Generate SVG path strings
  const rssiPoints = history.map((pt, i) => `${getX(i)},${getRssiY(pt.rssi)}`).join(" ");
  const snrPoints = history.map((pt, i) => `${getX(i)},${getSnrY(pt.snr)}`).join(" ");

  // Signal color helper for RSSI
  const getRssiColor = (rssi: number) => {
    if (rssi > -35) return "text-emerald-400";
    if (rssi > -55) return "text-cyan-400";
    if (rssi > -70) return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className="glass-panel p-5 border border-white/10 space-y-5">
      {/* Title & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white font-sans">
              REAL-TIME RF TELEMETRY & SPECTRUM
            </h2>
            <p className="text-xs text-slate-400 font-mono-code">
              Signal Power, Signal-to-Noise Ratio, Packet Error Rate & Throughput
            </p>
          </div>
        </div>

        {/* Chart Play/Pause & Reset */}
        <div className="flex items-center gap-2 font-mono-code text-xs">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`px-3 py-1.5 rounded-lg border text-xs transition-colors flex items-center gap-1.5 ${
              isPaused
                ? "bg-amber-600/20 text-amber-300 border-amber-500/40"
                : "bg-white/5 text-slate-300 border-white/10 hover:bg-white/10 hover:text-white"
            }`}
          >
            {isPaused ? <Play className="w-3 h-3 fill-amber-300" /> : <Pause className="w-3 h-3" />}
            <span>{isPaused ? "Resume Feed" : "Pause Chart"}</span>
          </button>

          <button
            onClick={() => setHistory([])}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white border border-white/10"
            title="Reset Chart Buffer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 6 High-Tech Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 font-mono-code">
        
        {/* RSSI */}
        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>RSSI Power</span>
            <Wifi className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="my-2">
            <span className={`text-xl font-bold tracking-tight ${getRssiColor(telemetry?.rssi_dbfs ?? -70)}`}>
              {telemetry ? `${telemetry.rssi_dbfs.toFixed(1)}` : "---"}
            </span>
            <span className="text-xs text-slate-400 ml-1">dBFS</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div 
              className="bg-cyan-400 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, ((telemetry?.rssi_dbfs ?? -80) + 80) * 1.4))}%` }}
            />
          </div>
        </div>

        {/* SNR */}
        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>SNR Ratio</span>
            <Gauge className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold tracking-tight text-emerald-400">
              {telemetry ? `${telemetry.snr_db.toFixed(1)}` : "---"}
            </span>
            <span className="text-xs text-slate-400 ml-1">dB</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div 
              className="bg-emerald-400 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, (telemetry?.snr_db ?? 0) * 3))}%` }}
            />
          </div>
        </div>

        {/* CFO */}
        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>CFO Offset</span>
            <span className="text-[10px] text-slate-500">Delta</span>
          </div>
          <div className="my-2">
            <span className="text-lg font-bold tracking-tight text-slate-100">
              {telemetry ? `${Math.round(telemetry.cfo_hz)}` : "---"}
            </span>
            <span className="text-xs text-slate-400 ml-1">Hz</span>
          </div>
          <span className="text-[10px] text-slate-500">Carrier Offset</span>
        </div>

        {/* PER & CRC */}
        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Error Rate</span>
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
          </div>
          <div className="my-2">
            <span className={`text-xl font-bold tracking-tight ${telemetry?.per_pct ? "text-rose-400" : "text-slate-100"}`}>
              {telemetry ? `${telemetry.per_pct.toFixed(1)}%` : "0.0%"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500">CRC: {telemetry?.crc_errors ?? 0}</span>
        </div>

        {/* TX / RX Packets */}
        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>IP Packets</span>
            <div className="flex gap-1 text-[10px]">
              <span className="text-blue-400">TX</span>/<span className="text-emerald-400">RX</span>
            </div>
          </div>
          <div className="my-2 text-sm font-bold">
            <span className="text-blue-400">{telemetry?.tx_packets ?? 0}</span>
            <span className="text-slate-600 mx-1">/</span>
            <span className="text-emerald-400">{telemetry?.rx_packets ?? 0}</span>
          </div>
          <span className="text-[10px] text-slate-500">
            {((telemetry?.tx_bytes ?? 0) / 1024).toFixed(1)} KB TX
          </span>
        </div>

        {/* Throughput */}
        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Throughput</span>
            <TrendingUp className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="my-2">
            <span className="text-xl font-bold tracking-tight text-purple-300">
              {telemetry ? `${telemetry.throughput_kbps.toFixed(1)}` : "0.0"}
            </span>
            <span className="text-xs text-slate-400 ml-1">kbps</span>
          </div>
          <span className="text-[10px] text-slate-500">Airwave speed</span>
        </div>
      </div>

      {/* Real-time Rolling Strip Chart */}
      <div className="p-4 rounded-xl bg-black/60 border border-white/10 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono-code">
          <div className="flex items-center gap-4">
            <span className="text-slate-300 font-semibold text-[11px]">ROLLING TIME-SERIES</span>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 bg-cyan-400 inline-block rounded" />
                <span className="text-cyan-400">RSSI ({telemetry?.rssi_dbfs.toFixed(1) || "-"} dBFS)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 bg-emerald-400 inline-block rounded" />
                <span className="text-emerald-400">SNR ({telemetry?.snr_db.toFixed(1) || "-"} dB)</span>
              </span>
            </div>
          </div>

          <span className="text-slate-500 text-[10px]">Buffer: 35 samples • 60 FPS Canvas/SVG</span>
        </div>

        {/* SVG Strip Chart */}
        <div className="w-full overflow-x-auto">
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full h-40 bg-[#07080D] rounded-lg border border-white/5 font-mono-code"
          >
            {/* Horizontal Grid lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const y = padding.top + ratio * graphHeight;
              const rssiVal = Math.round(maxRssi - ratio * (maxRssi - minRssi));
              return (
                <g key={ratio}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={svgWidth - padding.right}
                    y2={y}
                    stroke="rgba(255,255,255,0.06)"
                    strokeDasharray="3 3"
                  />
                  <text
                    x={padding.left - 6}
                    y={y + 3}
                    fill="rgba(255,255,255,0.3)"
                    fontSize="9"
                    textAnchor="end"
                  >
                    {rssiVal}
                  </text>
                </g>
              );
            })}

            {/* Vertical guidelines */}
            {[0.2, 0.4, 0.6, 0.8].map((ratio) => {
              const x = padding.left + ratio * graphWidth;
              return (
                <line
                  key={ratio}
                  x1={x}
                  y1={padding.top}
                  x2={x}
                  y2={padding.top + graphHeight}
                  stroke="rgba(255,255,255,0.04)"
                />
              );
            })}

            {/* RSSI Line */}
            {history.length > 1 && (
              <polyline
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={rssiPoints}
              />
            )}

            {/* SNR Line */}
            {history.length > 1 && (
              <polyline
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={snrPoints}
              />
            )}

            {/* Current point pulses */}
            {history.length > 0 && (
              <g>
                <circle
                  cx={getX(history.length - 1)}
                  cy={getRssiY(history[history.length - 1].rssi)}
                  r="4"
                  fill="#06b6d4"
                  className="animate-ping"
                />
                <circle
                  cx={getX(history.length - 1)}
                  cy={getRssiY(history[history.length - 1].rssi)}
                  r="3.5"
                  fill="#06b6d4"
                />
                <circle
                  cx={getX(history.length - 1)}
                  cy={getSnrY(history[history.length - 1].snr)}
                  r="3.5"
                  fill="#10b981"
                />
              </g>
            )}

            {/* Bottom time labels */}
            {history.length > 0 && (
              <g fill="rgba(255,255,255,0.3)" fontSize="9">
                <text x={padding.left} y={svgHeight - 6} textAnchor="start">
                  {history[0]?.time}
                </text>
                <text x={svgWidth - padding.right} y={svgHeight - 6} textAnchor="end">
                  {history[history.length - 1]?.time}
                </text>
              </g>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
};
