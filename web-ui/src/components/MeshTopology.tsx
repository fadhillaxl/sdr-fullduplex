"use client";

import React from "react";
import { 
  Server, 
  Laptop, 
  Radio, 
  ArrowRightLeft, 
  Send, 
  CheckCircle, 
  ShieldCheck, 
  WifiHigh,
  Zap
} from "lucide-react";
import { LinkStatus } from "@/types/api";

interface MeshTopologyProps {
  linkStatus: LinkStatus | null;
  selectedNodeUrl: string;
  onSelectNode: (url: string) => void;
  onQuickPing: (targetIp: string) => void;
}

interface NodeMeta {
  id: number;
  name: string;
  role: string;
  ip: string;
  apiUrl: string;
  type: "gateway" | "relay" | "ground";
  desc: string;
}

const MESH_NODES: NodeMeta[] = [
  {
    id: 1,
    name: "Raspi 5",
    role: "Gateway & Master Router",
    ip: "192.168.30.1",
    apiUrl: "http://raspi5.local:8000",
    type: "gateway",
    desc: "Host route gateway with Pluto+ SDR on USB 3.0",
  },
  {
    id: 2,
    name: "Raspi 2W",
    role: "Wireless Edge / Relay",
    ip: "192.168.30.2",
    apiUrl: "http://raspi2w.local:8000",
    type: "relay",
    desc: "Pluto SDR embedded node on USB OTG",
  },
  {
    id: 3,
    name: "Ground Station Mac",
    role: "Controller & SDR Host",
    ip: "192.168.30.3",
    apiUrl: "http://localhost:8000",
    type: "ground",
    desc: "Client node using macOS utun virtual interface",
  },
];

export const MeshTopology: React.FC<MeshTopologyProps> = ({
  linkStatus,
  selectedNodeUrl,
  onSelectNode,
  onQuickPing,
}) => {
  const isRunning = linkStatus?.is_running ?? false;
  const activeLocalIp = linkStatus?.local_ip || "192.168.30.3";
  const activePeerIp = linkStatus?.peer_ip || "192.168.30.1";

  return (
    <div className="glass-panel p-5 relative overflow-hidden border border-white/10">
      {/* Background glow effects */}
      <div className="absolute -top-24 -right-24 w-60 h-60 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-60 h-60 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold tracking-wide text-white font-sans">
              TRI-NODE MESH TOPOLOGY
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-mono-code">
              2.4 GHz RF Carrier
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono-code mt-0.5">
            Full-Duplex IP Radio Overlay • TUN Network Subnet: 192.168.30.0/24
          </p>
        </div>

        {/* Live Link Duplex Info Badge */}
        <div className="flex items-center gap-2 text-xs font-mono-code px-3 py-1.5 rounded-lg bg-black/40 border border-white/10">
          <ArrowRightLeft className={`w-3.5 h-3.5 ${isRunning ? "text-emerald-400 animate-pulse" : "text-slate-500"}`} />
          <span className="text-slate-400">Mode:</span>
          <span className={isRunning ? "text-white font-semibold" : "text-slate-500"}>
            {linkStatus?.duplex_mode || "TDD / FDD"}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">Modem:</span>
          <span className="text-cyan-400 font-semibold">{linkStatus?.modulation || "BPSK"}</span>
        </div>
      </div>

      {/* Visual Mesh Topology Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
        {MESH_NODES.map((node) => {
          const isSelected = selectedNodeUrl === node.apiUrl;
          const isCurrentActiveLocal = isRunning && activeLocalIp === node.ip;
          const isCurrentPeer = isRunning && activePeerIp === node.ip;

          return (
            <div
              key={node.id}
              className={`p-4 rounded-xl transition-all duration-300 relative border flex flex-col justify-between ${
                isSelected
                  ? "bg-blue-950/40 border-blue-500/60 shadow-[0_0_20px_rgba(59,130,246,0.25)]"
                  : "bg-black/30 border-white/10 hover:border-white/20"
              }`}
            >
              {/* Top Row: Icon & Status */}
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className={`p-2 rounded-lg ${
                      node.type === "gateway"
                        ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                        : node.type === "relay"
                        ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}>
                      {node.type === "gateway" ? (
                        <Server className="w-5 h-5" />
                      ) : node.type === "relay" ? (
                        <Radio className="w-5 h-5" />
                      ) : (
                        <Laptop className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <h3 className="text-sm font-bold text-white font-sans">{node.name}</h3>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/10 text-slate-300 font-mono-code">
                          Node {node.id}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono-code">{node.role}</p>
                    </div>
                  </div>

                  {/* Active Indicator */}
                  {isSelected && (
                    <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/40 font-mono-code font-bold">
                      <Zap className="w-2.5 h-2.5 text-blue-400" /> ACTIVE UI
                    </span>
                  )}
                </div>

                {/* Network IP & Details */}
                <div className="mt-3.5 space-y-1.5 font-mono-code text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-black/50 border border-white/5">
                    <span className="text-slate-400 text-[11px]">TUN Virtual IP:</span>
                    <span className="text-emerald-400 font-semibold">{node.ip}</span>
                  </div>

                  <div className="flex items-center justify-between px-2 py-1 text-[11px]">
                    <span className="text-slate-400">Endpoint:</span>
                    <span className="text-slate-300 truncate max-w-[150px]">{node.apiUrl}</span>
                  </div>

                  <p className="text-[11px] text-slate-400 line-clamp-2 px-1 pt-1 opacity-80">
                    {node.desc}
                  </p>
                </div>
              </div>

              {/* Bottom Actions */}
              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between gap-2">
                <button
                  onClick={() => onSelectNode(node.apiUrl)}
                  className={`flex-1 py-1.5 px-2.5 rounded-lg text-xs font-mono-code transition-colors flex items-center justify-center gap-1.5 ${
                    isSelected
                      ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                      : "bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5 opacity-70" />
                  <span>{isSelected ? "Selected" : "Switch Node"}</span>
                </button>

                <button
                  onClick={() => onQuickPing(node.ip)}
                  className="py-1.5 px-2.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 text-xs font-mono-code transition-colors flex items-center gap-1"
                  title={`Test ping to ${node.ip}`}
                >
                  <Send className="w-3 h-3" />
                  <span>Ping</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* RF Active Link Over-the-air Status Ribbon */}
      <div className="mt-4 p-2.5 rounded-xl bg-gradient-to-r from-blue-950/40 via-cyan-950/30 to-blue-950/40 border border-cyan-500/20 flex flex-wrap items-center justify-between text-xs font-mono-code gap-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isRunning ? "bg-cyan-400 opacity-75" : "bg-slate-500"}`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${isRunning ? "bg-cyan-500" : "bg-slate-600"}`}></span>
          </span>
          <span className="text-slate-300 font-medium">RF Physical Carrier:</span>
          <span className="text-cyan-400 font-bold">
            {linkStatus?.tx_freq_hz ? `${(linkStatus.tx_freq_hz / 1e6).toFixed(1)} MHz` : "2,400.0 MHz"}
          </span>
        </div>

        <div className="flex items-center gap-3 text-slate-400 text-[11px]">
          <span>Interface: <strong className="text-white">{linkStatus?.interface_name || "radio0 / utun"}</strong></span>
          <span>•</span>
          <span>Peer Node: <strong className="text-emerald-400">{activePeerIp}</strong></span>
          <span>•</span>
          <span>Status: <strong className={isRunning ? "text-emerald-400" : "text-slate-400"}>{linkStatus?.mode || "IDLE"}</strong></span>
        </div>
      </div>
    </div>
  );
};
