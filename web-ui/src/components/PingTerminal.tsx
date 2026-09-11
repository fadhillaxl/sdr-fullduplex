"use client";

import React, { useState } from "react";
import { 
  Terminal, 
  Send, 
  CheckCircle2, 
  XCircle, 
  Trash2, 
  Copy, 
  Clock, 
  Radio, 
  RefreshCw,
  TrendingDown
} from "lucide-react";
import { PingResponse } from "@/types/api";
import { sendPing } from "@/lib/api";

interface PingTerminalProps {
  baseUrl: string;
  quickTarget?: string | null;
}

export const PingTerminal: React.FC<PingTerminalProps> = ({
  baseUrl,
  quickTarget,
}) => {
  const [target, setTarget] = useState<string>("192.168.30.1");
  const [count, setCount] = useState<number>(4);
  const [timeoutSec, setTimeoutSec] = useState<number>(6.0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [logs, setLogs] = useState<string[]>([
    "// ICMP Over-the-Air Diagnostic Subsystem Ready",
    "// Packets will route through local TUN interface and transmit via 2.4 GHz RF Carrier",
  ]);
  const [lastResult, setLastResult] = useState<PingResponse | null>(null);

  // Update target when quickTarget is clicked from MeshTopology
  React.useEffect(() => {
    if (quickTarget) {
      setTarget(quickTarget);
    }
  }, [quickTarget]);

  const handleRunPing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!target.trim()) return;

    setIsRunning(true);
    const startTimestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [
      ...prev,
      `\n[${startTimestamp}] > ping -c ${count} ${target.trim()} (Transmitting over RF mesh...)`,
    ]);

    try {
      const res = await sendPing(baseUrl, target.trim(), count, 0.5, timeoutSec);
      setLastResult(res);

      const finishTimestamp = new Date().toLocaleTimeString();
      if (res.success) {
        setLogs((prev) => [
          ...prev,
          res.raw_output.trim(),
          `[${finishTimestamp}] [OK] ${res.received}/${res.transmitted} packets received (${res.packet_loss_pct}% loss) • Avg RTT: ${res.rtt_avg_ms ?? "---"} ms`,
        ]);
      } else {
        setLogs((prev) => [
          ...prev,
          res.raw_output ? res.raw_output.trim() : "Ping timeout: 100% packet loss. No response from remote peer.",
          `[${finishTimestamp}] [FAIL] Host unreachable over radio link. Check SDR frequency & gains.`,
        ]);
      }
    } catch (err: any) {
      setLogs((prev) => [
        ...prev,
        `[ERROR] ${err.message || "Failed to execute ICMP ping command"}`,
      ]);
    } finally {
      setIsRunning(false);
    }
  };

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join("\n"));
  };

  return (
    <div className="glass-panel p-5 border border-white/10 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-600/20 border border-emerald-500/30 text-emerald-400">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white font-sans">
              OVER-THE-AIR ICMP DIAGNOSTIC
            </h2>
            <p className="text-xs text-slate-400 font-mono-code">
              Active Mesh IP Latency & Packet Loss Verification
            </p>
          </div>
        </div>

        {/* Quick Targets */}
        <div className="flex items-center gap-1.5 font-mono-code text-xs">
          <span className="text-slate-400 text-[11px]">Targets:</span>
          {[
            { label: "GW (.1)", ip: "192.168.30.1" },
            { label: "Relay (.2)", ip: "192.168.30.2" },
            { label: "Mac (.3)", ip: "192.168.30.3" },
          ].map((item) => (
            <button
              key={item.ip}
              type="button"
              onClick={() => setTarget(item.ip)}
              className={`px-2 py-1 rounded-md text-[11px] border transition-colors ${
                target === item.ip
                  ? "bg-emerald-600/30 text-emerald-300 border-emerald-500/50 font-bold"
                  : "bg-white/5 text-slate-400 border-white/10 hover:text-white"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Controls */}
      <form onSubmit={handleRunPing} className="grid grid-cols-1 sm:grid-cols-12 gap-3 font-mono-code text-xs">
        <div className="sm:col-span-6">
          <label className="text-slate-400 text-[11px]">Target IP Address</label>
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="192.168.30.1"
            className="w-full bg-black/60 border border-white/15 rounded-lg px-3 py-2 text-slate-100 mt-1 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="sm:col-span-2">
          <label className="text-slate-400 text-[11px]">Packet Count</label>
          <input
            type="number"
            min="1"
            max="30"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-full bg-black/60 border border-white/15 rounded-lg px-2.5 py-2 text-slate-100 mt-1 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="sm:col-span-4 flex items-end">
          <button
            type="submit"
            disabled={isRunning}
            className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            {isRunning ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-white" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            <span>{isRunning ? "TRANSMITTING..." : "TRANSMIT PING (OTA)"}</span>
          </button>
        </div>
      </form>

      {/* Live Terminal Output Window */}
      <div className="rounded-xl bg-[#06080E] border border-white/10 overflow-hidden font-mono-code text-xs shadow-inner">
        {/* Terminal Header */}
        <div className="px-3 py-2 bg-black/80 border-b border-white/10 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
            </div>
            <span className="text-slate-400">radio0-diagnostic-shell</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyLogs}
              className="hover:text-white p-1 rounded hover:bg-white/5 transition-colors"
              title="Copy Output"
            >
              <Copy className="w-3 h-3" />
            </button>
            <button
              onClick={() => setLogs([])}
              className="hover:text-white p-1 rounded hover:bg-white/5 transition-colors"
              title="Clear Terminal"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Terminal Screen */}
        <div className="p-4 h-48 overflow-y-auto space-y-1 text-emerald-400 text-[11.5px] leading-relaxed select-text">
          {logs.map((line, idx) => (
            <div key={idx} className={line.startsWith("[ERROR]") || line.includes("[FAIL]") ? "text-rose-400" : line.startsWith("[OK]") ? "text-cyan-300 font-bold" : ""}>
              {line}
            </div>
          ))}
          {isRunning && (
            <div className="flex items-center gap-2 text-cyan-400 animate-pulse">
              <span>Transmitting RF burst packets over airwaves...</span>
              <span className="inline-block w-2 h-3.5 bg-cyan-400 animate-pulse" />
            </div>
          )}
        </div>
      </div>

      {/* Ping Stats Summary Metrics */}
      {lastResult && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono-code text-xs pt-1">
          <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
            <span className="text-slate-400 text-[10px]">Min RTT:</span>
            <p className="text-emerald-400 font-bold text-sm mt-0.5">
              {lastResult.rtt_min_ms ? `${lastResult.rtt_min_ms} ms` : "---"}
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
            <span className="text-slate-400 text-[10px]">Avg RTT:</span>
            <p className="text-cyan-400 font-bold text-sm mt-0.5">
              {lastResult.rtt_avg_ms ? `${lastResult.rtt_avg_ms} ms` : "---"}
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
            <span className="text-slate-400 text-[10px]">Max RTT:</span>
            <p className="text-purple-400 font-bold text-sm mt-0.5">
              {lastResult.rtt_max_ms ? `${lastResult.rtt_max_ms} ms` : "---"}
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
            <span className="text-slate-400 text-[10px]">Packet Loss:</span>
            <p className={`font-bold text-sm mt-0.5 ${lastResult.packet_loss_pct === 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {lastResult.packet_loss_pct}%
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
