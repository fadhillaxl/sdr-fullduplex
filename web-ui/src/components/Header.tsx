"use client";

import React, { useState } from "react";
import { 
  Radio, 
  Activity, 
  RefreshCw, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  Wifi, 
  Cpu,
  Layers
} from "lucide-react";
import { LinkStatus } from "@/types/api";

interface HeaderProps {
  selectedNode: string;
  setSelectedNode: (url: string) => void;
  linkStatus: LinkStatus | null;
  latencyMs: number | null;
  isOnline: boolean;
  refreshInterval: number;
  setRefreshInterval: (ms: number) => void;
  onManualRefresh: () => void;
  isRefreshing: boolean;
}

const PRESET_NODES = [
  { name: "Localhost (Mac)", url: "http://localhost:8000", ip: "192.168.30.3" },
  { name: "Raspi 5 (Gateway)", url: "http://raspi5.local:8000", ip: "192.168.30.1" },
  { name: "Raspi 2W (Relay)", url: "http://raspi2w.local:8000", ip: "192.168.30.2" },
];

export const Header: React.FC<HeaderProps> = ({
  selectedNode,
  setSelectedNode,
  linkStatus,
  latencyMs,
  isOnline,
  refreshInterval,
  setRefreshInterval,
  onManualRefresh,
  isRefreshing,
}) => {
  const [customUrl, setCustomUrl] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [presetNodes, setPresetNodes] = useState(PRESET_NODES);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      if (host && host !== "localhost" && host !== "127.0.0.1") {
        setPresetNodes([
          { name: `This Node (${host.split(".")[0]})`, url: `http://${host}:8000`, ip: host },
          { name: "Raspi 5 (GW)", url: "http://raspi5.local:8000", ip: "192.168.30.1" },
          { name: "Raspi 2W", url: "http://raspi2w.local:8000", ip: "192.168.30.2" },
          { name: "Mac", url: "http://localhost:8000", ip: "192.168.30.3" },
        ]);
      }
    }
  }, []);

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customUrl.trim()) {
      let formatted = customUrl.trim();
      if (!formatted.startsWith("http://") && !formatted.startsWith("https://")) {
        formatted = `http://${formatted}`;
      }
      setSelectedNode(formatted);
      setShowCustomInput(false);
    }
  };

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-white/10 px-4 lg:px-8 py-3.5 backdrop-blur-xl bg-[#0B0B10]/90">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
            <Radio className="w-5 h-5 animate-pulse text-cyan-400" />
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isOnline ? 'bg-emerald-400 opacity-75' : 'bg-rose-400 opacity-75'}`}></span>
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isOnline ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-wider text-white font-sans flex items-center gap-2">
                PLUTO+ SDR <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 uppercase font-mono-code">Mesh FUI</span>
              </h1>
              {linkStatus?.is_running ? (
                <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono-code">
                  <CheckCircle2 className="w-3 h-3" /> LINK ENGAGED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-slate-700/30 text-slate-400 border border-white/10 font-mono-code">
                  <AlertCircle className="w-3 h-3" /> IDLE
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-mono-code flex items-center gap-2">
              <span>Short-Range IP Radio</span>
              <span className="text-slate-600">•</span>
              <span className="text-cyan-400">{linkStatus?.device_uri || "usb/ip"}</span>
            </p>
          </div>
        </div>

        {/* Center: Target Node Switcher */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/40 border border-white/10 text-xs font-mono-code">
          {presetNodes.map((node) => {
            const isSelected = selectedNode === node.url;
            return (
              <button
                key={node.url}
                onClick={() => setSelectedNode(node.url)}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-blue-600 text-white font-semibold shadow-[0_0_12px_rgba(59,130,246,0.4)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                <Cpu className="w-3.5 h-3.5 opacity-70" />
                <span>{node.name.split(" ")[0]}</span>
                <span className="text-[10px] opacity-70">({node.ip.split(".").slice(2).join(".")})</span>
              </button>
            );
          })}

          <button
            onClick={() => setShowCustomInput(!showCustomInput)}
            className="px-2 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 text-[11px]"
            title="Custom Endpoint"
          >
            Custom...
          </button>
        </div>

        {/* Right: Telemetry Health & Controls */}
        <div className="flex items-center gap-3">
          {/* Latency badge */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs font-mono-code">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">RTT:</span>
            <span className={latencyMs !== null && latencyMs < 50 ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
              {latencyMs !== null ? `${latencyMs}ms` : "---"}
            </span>
          </div>

          {/* Polling interval selector */}
          <div className="flex items-center gap-1 text-xs font-mono-code text-slate-400">
            <span className="hidden lg:inline text-[11px]">Sync:</span>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="bg-black/60 border border-white/15 text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-blue-500"
            >
              <option value={1000}>1.0s</option>
              <option value={2000}>2.0s</option>
              <option value={5000}>5.0s</option>
              <option value={0}>Pause</option>
            </select>
          </div>

          {/* Manual refresh button */}
          <button
            onClick={onManualRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 transition-colors disabled:opacity-50"
            title="Force Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-blue-400" : ""}`} />
          </button>

          {/* Swagger docs link */}
          <a
            href={`${selectedNode}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 text-xs font-mono-code transition-colors"
          >
            <span>Swagger</span>
            <ExternalLink className="w-3 h-3 opacity-60" />
          </a>
        </div>
      </div>

      {/* Modal / Bar for custom URL */}
      {showCustomInput && (
        <form onSubmit={handleCustomSubmit} className="mt-3 max-w-7xl mx-auto flex items-center gap-2 pt-2 border-t border-white/10">
          <input
            type="text"
            placeholder="http://192.168.30.1:8000"
            value={customUrl}
            onChange={(e) => setCustomUrl(e.target.value)}
            className="flex-1 bg-black/60 border border-white/20 rounded-lg px-3 py-1.5 text-xs font-mono-code text-white focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-500"
          >
            Connect
          </button>
          <button
            type="button"
            onClick={() => setShowCustomInput(false)}
            className="px-3 py-1.5 rounded-lg bg-white/5 text-slate-400 text-xs hover:bg-white/10"
          >
            Cancel
          </button>
        </form>
      )}
    </header>
  );
};
