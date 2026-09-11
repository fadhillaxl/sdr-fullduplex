"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/Header";
import { MeshTopology } from "@/components/MeshTopology";
import { TransceiverControl } from "@/components/TransceiverControl";
import { TelemetryStrip } from "@/components/TelemetryStrip";
import { PingTerminal } from "@/components/PingTerminal";
import { AntennaAnalyzer } from "@/components/AntennaAnalyzer";
import { LinkStatus, Telemetry } from "@/types/api";
import { fetchLinkStatus, fetchTelemetry } from "@/lib/api";
import { Radio, ShieldAlert, Cpu } from "lucide-react";

export default function Home() {
  const [selectedNode, setSelectedNode] = useState<string>("http://localhost:8000");
  const [linkStatus, setLinkStatus] = useState<LinkStatus | null>(null);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(2000);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [quickPingTarget, setQuickPingTarget] = useState<string | null>(null);

  // Poll telemetry and status
  const updateData = useCallback(async () => {
    setIsRefreshing(true);
    const start = performance.now();
    try {
      const [statusRes, telemetryRes] = await Promise.all([
        fetchLinkStatus(selectedNode),
        fetchTelemetry(selectedNode).catch(() => null),
      ]);
      const elapsed = Math.round(performance.now() - start);
      setLatencyMs(elapsed);
      setLinkStatus(statusRes);
      if (telemetryRes) setTelemetry(telemetryRes);
      setIsOnline(true);
    } catch (err) {
      setIsOnline(false);
      setLatencyMs(null);
    } finally {
      setIsRefreshing(false);
    }
  }, [selectedNode]);

  // Initial fetch and timer effect
  useEffect(() => {
    updateData();

    if (refreshInterval <= 0) return;
    const interval = setInterval(updateData, refreshInterval);
    return () => clearInterval(interval);
  }, [updateData, refreshInterval]);

  return (
    <div className="min-h-screen flex flex-col justify-between text-slate-100">
      
      {/* Sticky Header */}
      <Header
        selectedNode={selectedNode}
        setSelectedNode={setSelectedNode}
        linkStatus={linkStatus}
        latencyMs={latencyMs}
        isOnline={isOnline}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
        onManualRefresh={updateData}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-6 space-y-6">
        
        {/* Offline Warning Banner */}
        {!isOnline && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono-code flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
              <span>
                Cannot reach Pluto SDR node backend at <strong>{selectedNode}</strong>. Ensure FastAPI server is running with root permissions: <code className="bg-black/50 px-1.5 py-0.5 rounded text-white">sudo .venv/bin/python -m pluto_radio.cli server --host 0.0.0.0 --port 8000</code>
              </span>
            </div>
            <button
              onClick={updateData}
              className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 rounded-lg text-amber-200 border border-amber-500/40 text-xs font-semibold shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        {/* 1. Tri-Node Mesh Topology Map */}
        <MeshTopology
          linkStatus={linkStatus}
          selectedNodeUrl={selectedNode}
          onSelectNode={(url) => setSelectedNode(url)}
          onQuickPing={(ip) => setQuickPingTarget(ip)}
        />

        {/* 2. Real-Time RF Telemetry & Strip Chart */}
        <TelemetryStrip
          telemetry={telemetry}
          isRunning={linkStatus?.is_running ?? false}
        />

        {/* 3. Two-Column Controls Grid: Transceiver + Ping Terminal */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7">
            <TransceiverControl
              baseUrl={selectedNode}
              linkStatus={linkStatus}
              onLinkStateChange={updateData}
            />
          </div>

          <div className="lg:col-span-5">
            <PingTerminal
              baseUrl={selectedNode}
              quickTarget={quickPingTarget}
            />
          </div>
        </div>

        {/* 4. Passive Multi-Band Antenna Analyzer */}
        <AntennaAnalyzer baseUrl={selectedNode} />

      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-6 px-4 lg:px-8 mt-12 bg-[#06070B]/80 font-mono-code text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-blue-500" />
            <span className="text-slate-400">Pluto+ SDR Short-Range IP Radio Mesh Mission Control</span>
            <span className="text-slate-600">•</span>
            <span className="text-cyan-400">Next.js 16 + Tailwind v4 + ui-ux-pro-max</span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <span>Active Target: <strong className="text-slate-300">{selectedNode}</strong></span>
            <span>•</span>
            <a
              href={`${selectedNode}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-cyan-400 underline underline-offset-4"
            >
              Swagger REST Docs
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
