"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { MeshTopology } from "@/components/MeshTopology";
import { TransceiverControl } from "@/components/TransceiverControl";
import { TelemetryStrip } from "@/components/TelemetryStrip";
import { PingTerminal } from "@/components/PingTerminal";
import { AntennaAnalyzer } from "@/components/AntennaAnalyzer";
import { LinkStatus, Telemetry } from "@/types/api";
import { fetchLinkStatus, fetchTelemetry } from "@/lib/api";
import { Radio, ShieldAlert, Zap } from "lucide-react";

export default function Home() {
  const [selectedNode, setSelectedNode] = useState<string>("");
  const [linkStatus, setLinkStatus] = useState<LinkStatus | null>(null);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(2000);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [quickPingTarget, setQuickPingTarget] = useState<string | null>(null);
  const [currentHost, setCurrentHost] = useState<string>("");

  // Select node with localStorage persistence
  const handleSelectNode = useCallback((url: string) => {
    setSelectedNode(url);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("pluto_selected_node", url);
      } catch (_) {}
    }
  }, []);

  // Initialize node target on client mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      setCurrentHost(hostname);

      let initialTarget = "";
      try {
        const saved = localStorage.getItem("pluto_selected_node");
        if (saved) initialTarget = saved;
      } catch (_) {}

      if (!initialTarget) {
        // If accessed on remote IP or hostname, default to that host's port 8000!
        if (hostname && hostname !== "localhost" && hostname !== "127.0.0.1") {
          initialTarget = `http://${hostname}:8000`;
        } else {
          initialTarget = "http://localhost:8000";
        }
      }

      setSelectedNode(initialTarget);
    }
  }, []);

  // Poll telemetry and status
  const updateData = useCallback(async () => {
    if (!selectedNode) return;
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

  // Initial fetch and timer effect when selectedNode is ready
  useEffect(() => {
    if (!selectedNode) return;
    updateData();

    if (refreshInterval <= 0) return;
    const interval = setInterval(updateData, refreshInterval);
    return () => clearInterval(interval);
  }, [selectedNode, updateData, refreshInterval]);

  return (
    <div className="min-h-screen flex flex-col justify-between text-slate-100">
      
      {/* Sticky Header */}
      <Header
        selectedNode={selectedNode || "http://localhost:8000"}
        setSelectedNode={handleSelectNode}
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
        
        {/* Offline Warning Banner with Quick Switch Helper */}
        {!isOnline && selectedNode && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono-code flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-amber-200">
                  Cannot connect to Pluto SDR backend at <code className="bg-black/60 px-1.5 py-0.5 rounded text-white">{selectedNode}</code>
                </p>
                <p className="text-slate-400 text-[11px] mt-1">
                  Ensure the FastAPI server is running with root privileges on the target node, or switch to an active node below.
                </p>
              </div>
            </div>

            {/* Quick Action Switch Buttons */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              {currentHost && selectedNode !== `http://${currentHost}:8000` && (
                <button
                  onClick={() => handleSelectNode(`http://${currentHost}:8000`)}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all shadow-[0_0_12px_rgba(59,130,246,0.3)] flex items-center gap-1.5"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>Connect to This Node ({currentHost}:8000)</span>
                </button>
              )}
              <button
                onClick={() => handleSelectNode("http://raspi2w.local:8000")}
                className="px-2.5 py-1.5 bg-white/10 hover:bg-white/15 text-slate-200 rounded-lg text-xs transition-colors"
              >
                Raspi 2W (:8000)
              </button>
              <button
                onClick={() => handleSelectNode("http://raspi5.local:8000")}
                className="px-2.5 py-1.5 bg-white/10 hover:bg-white/15 text-slate-200 rounded-lg text-xs transition-colors"
              >
                Raspi 5 (:8000)
              </button>
              <button
                onClick={updateData}
                className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 rounded-lg text-xs font-semibold"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* 1. Tri-Node Mesh Topology Map */}
        <MeshTopology
          linkStatus={linkStatus}
          selectedNodeUrl={selectedNode}
          onSelectNode={(url) => handleSelectNode(url)}
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
              baseUrl={selectedNode || "http://localhost:8000"}
              linkStatus={linkStatus}
              onLinkStateChange={updateData}
            />
          </div>

          <div className="lg:col-span-5">
            <PingTerminal
              baseUrl={selectedNode || "http://localhost:8000"}
              quickTarget={quickPingTarget}
            />
          </div>
        </div>

        {/* 4. Passive Multi-Band Antenna Analyzer */}
        <AntennaAnalyzer baseUrl={selectedNode || "http://localhost:8000"} />

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
