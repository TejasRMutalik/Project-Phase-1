"use client";

import React, { useEffect, useState, useRef } from "react";
import Header from "@/components/Header";
import {
  Car,
  Bike,
  Bus,
  Truck,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Terminal,
  UploadCloud,
  Layers,
  Zap,
  Play,
  RotateCcw
} from "lucide-react";

interface Vehicle {
  track_id: string | number;
  vehicle_class: string;
  confidence: number;
  plate_number?: string;
  plate_confidence?: number;
  plate_locked?: boolean;
  speed_kmh?: number;
  violations?: string[];
  ocr_invoked?: boolean;
}

interface ViolationItem {
  id?: number | string;
  plate_number: string;
  vehicle_class: string;
  confidence: number;
  violation_type?: string | null;
  speed_kmh?: number;
  time: string;
}

interface LogEntry {
  id: string;
  time: string;
  source: "YOLOv8" | "DeepSORT" | "EasyOCR" | "RATG-OC" | "SYSTEM";
  message: string;
}

interface UploadJob {
  id: string;
  filename: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  progress: number;
  thumbnail_url: string;
  vehicles_detected: number;
  violations_flagged: number;
}

export default function DashboardPage() {
  // Stats
  const [totalDetected, setTotalDetected] = useState<number>(1402);
  const [activeTracks, setActiveTracks] = useState<number>(14);
  const [platesRead, setPlatesRead] = useState<number>(1185);
  const [flaggedViolations, setFlaggedViolations] = useState<number>(87);

  // Live Telemetry
  const [fps, setFps] = useState<number>(30.0);
  const [ratgMode, setRatgMode] = useState<"PRIMARY" | "PROPAGATE">("PRIMARY");
  const [riskScore, setRiskScore] = useState<number>(0.28);
  const [violationAlert, setViolationAlert] = useState<string | null>(null);

  // Logs & Tables
  const [logs, setLogs] = useState<LogEntry[]>([
    { id: "1", time: "00:00:01", source: "SYSTEM", message: "Booting RATG-OC Traffic Surveillance System v2.1..." },
    { id: "2", time: "00:00:02", source: "SYSTEM", message: "Supervisory risk governor active (tau_D=0.5, K_max=4)." },
    { id: "3", time: "00:00:03", source: "RATG-OC", message: "Primary Mode: YOLOv8 vehicle detector active." }
  ]);
  const [tableRows, setTableRows] = useState<ViolationItem[]>([]);
  const [recentUploads, setRecentUploads] = useState<UploadJob[]>([]);

  // Camera Selection
  const [activeCamIndex, setActiveCamIndex] = useState<number>(0);
  const cameras = [
    { id: "CAM-01", name: "K.R. PURAM (MAIN)", video: "/assets/videos/sample_traffic.mp4" },
    { id: "CAM-02", name: "SILK BOARD", video: "https://assets.mixkit.co/videos/preview/mixkit-traffic-in-an-urban-avenue-41144-large.mp4" },
    { id: "CAM-03", name: "MAJESTIC", video: "https://assets.mixkit.co/videos/preview/mixkit-highway-traffic-during-sunset-41139-large.mp4" },
    { id: "CAM-04", name: "MG ROAD", video: "" },
    { id: "CAM-05", name: "HEBBAL", video: "" }
  ];

  const logEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Load Recent Uploads
  const fetchRecentUploads = async () => {
    try {
      const res = await fetch("/api/jobs?limit=4");
      if (res.ok) {
        const data = await res.json();
        const normalized = (data || []).map((j: any) => ({
          ...j,
          id: String(j.id || j.job_id || Math.random()),
        }));
        setRecentUploads(normalized);
      }
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    fetchRecentUploads();
    const interval = setInterval(fetchRecentUploads, 5000);
    return () => clearInterval(interval);
  }, []);

  // Connect WebSocket to real FastAPI backend
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: NodeJS.Timeout;

    function connect() {
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/live`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setLogs(prev => [
            ...prev.slice(-40),
            { id: String(Date.now()), time: new Date().toLocaleTimeString(), source: "SYSTEM", message: "WebSocket live feed connected to FastAPI backend." }
          ]);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const vehicles: Vehicle[] = data.vehicles || [];
            const violations: any[] = data.violations || [];

            if (data.fps) setFps(data.fps);
            if (data.ratg_mode) setRatgMode(data.ratg_mode);
            if (typeof data.risk_score === "number") setRiskScore(data.risk_score);

            setTotalDetected(prev => prev + vehicles.length);
            setActiveTracks(vehicles.length);

            let newPlates = 0;
            vehicles.forEach(v => {
              if (v.plate_number && v.plate_number !== "UNKNOWN") {
                newPlates++;
              }
            });
            if (newPlates > 0) setPlatesRead(prev => prev + newPlates);
            if (violations.length > 0) setFlaggedViolations(prev => prev + violations.length);

            // Add logs & table items
            vehicles.forEach(v => {
              const nowTime = new Date().toLocaleTimeString();
              const hasViolations = v.violations && v.violations.length > 0;
              const violType = hasViolations ? v.violations![0] : null;

              if (hasViolations) {
                setViolationAlert(`${violType} DETECTED`);
                setTimeout(() => setViolationAlert(null), 3000);
              }

              // Prepend to table
              setTableRows(prev => [
                {
                  id: String(Date.now() + Math.random()),
                  plate_number: v.plate_number || "UNKNOWN",
                  vehicle_class: v.vehicle_class,
                  confidence: Math.round(v.confidence * 100),
                  violation_type: violType,
                  speed_kmh: v.speed_kmh || 0,
                  time: nowTime
                },
                ...prev.slice(0, 49)
              ]);

              // Add logs
              const newLogs: LogEntry[] = [];
              if (data.ratg_mode === "PRIMARY") {
                newLogs.push({
                  id: String(Date.now() + 1),
                  time: nowTime,
                  source: "YOLOv8",
                  message: `Detected ${v.vehicle_class} (Conf: ${v.confidence})`
                });
              }
              if (v.plate_number && v.plate_number !== "UNKNOWN") {
                newLogs.push({
                  id: String(Date.now() + 2),
                  time: nowTime,
                  source: "EasyOCR",
                  message: `Plate Read: ${v.plate_number} ${v.plate_locked ? "[LOCKED]" : ""}`
                });
              }
              if (newLogs.length > 0) {
                setLogs(prev => [...prev.slice(-30), ...newLogs]);
              }
            });
          } catch (err) {
            console.error("WebSocket message parse error:", err);
          }
        };

        ws.onclose = () => {
          reconnectTimer = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (err) {
        reconnectTimer = setTimeout(connect, 4000);
      }
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  const getVehicleIcon = (cls: string) => {
    switch (cls.toLowerCase()) {
      case "motorcycle":
      case "two-wheeler":
        return <Bike className="w-4 h-4 text-emerald-400" />;
      case "bus":
        return <Bus className="w-4 h-4 text-amber-400" />;
      case "truck":
        return <Truck className="w-4 h-4 text-purple-400" />;
      default:
        return <Car className="w-4 h-4 text-cyan-400" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#07090e]">
      <Header
        title="Live Traffic Analytics & Adaptive Scheduling"
        subtitle="RATG-OC Surveillance Control Room"
      />

      <div className="flex-1 p-5 overflow-y-auto space-y-5">
        {/* Top KPI Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel rounded-xl p-4 border border-white/5 relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
                Total Vehicles Detected
              </span>
              <Car className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {totalDetected.toLocaleString()}
            </div>
            <div className="text-[11px] text-cyan-400 font-mono mt-1 flex items-center gap-1">
              <Zap className="w-3 h-3" /> YOLOv8 + DeepSORT
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 border border-white/5 relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
                Active DeepSORT Tracks
              </span>
              <Layers className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-cyan-400 tracking-tight">
              {activeTracks}
            </div>
            <div className="text-[11px] text-slate-400 font-mono mt-1">
              Kalman motion projected
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 border border-white/5 relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
                Plates Resolved (Consensus)
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
              {platesRead.toLocaleString()}
            </div>
            <div className="text-[11px] text-emerald-500 font-mono mt-1">
              Track-Level OCR Consensus
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 border border-white/5 relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono tracking-wider text-slate-400 uppercase font-semibold">
                Flagged Infractions
              </span>
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-rose-400 tracking-tight">
              {flaggedViolations}
            </div>
            <div className="text-[11px] text-rose-500 font-mono mt-1">
              Speed / Signal / Helmet
            </div>
          </div>
        </div>

        {/* Main Surveillance Hub */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          {/* Left: Video Player & Sub-Cams (7 Cols on XL) */}
          <div className="xl:col-span-7 space-y-4">
            <div className="glass-panel rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
                  <span className="text-xs font-mono font-bold tracking-wider text-white">
                    LIVE CAMERA FEED // {cameras[activeCamIndex].id}
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  {cameras[activeCamIndex].name}
                </span>
              </div>

              {/* Video Player Container */}
              <div className="relative aspect-video rounded-lg overflow-hidden bg-black border border-white/10 shadow-2xl">
                <video
                  ref={videoRef}
                  src={cameras[activeCamIndex].video || "/assets/videos/sample_traffic.mp4"}
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                />

                {/* Overlays */}
                {/* REC Indicator */}
                <div className="absolute top-3 left-3 flex items-center gap-2 px-2.5 py-1 rounded bg-black/60 backdrop-blur-md border border-rose-500/30 text-rose-400 text-xs font-mono font-medium">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                  REC
                </div>

                {/* RATG Mode Dynamic Badge */}
                <div
                  className={`absolute top-3 right-28 flex items-center gap-2 px-3 py-1 rounded-md text-xs font-mono font-bold backdrop-blur-md border transition-all ${
                    ratgMode === "PRIMARY"
                      ? "bg-cyan-950/80 text-cyan-300 border-cyan-500/40 shadow-lg shadow-cyan-500/20"
                      : "bg-emerald-950/80 text-emerald-300 border-emerald-500/40 shadow-lg shadow-emerald-500/20"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      ratgMode === "PRIMARY" ? "bg-cyan-400 animate-pulse" : "bg-emerald-400"
                    }`}
                  />
                  <span>RATG: {ratgMode}</span>
                  <span className="text-[10px] opacity-80">(r={riskScore.toFixed(2)})</span>
                </div>

                {/* FPS Display */}
                <div className="absolute top-3 right-3 px-2.5 py-1 rounded bg-black/60 backdrop-blur-md border border-emerald-500/30 text-emerald-400 text-xs font-mono font-medium">
                  {fps.toFixed(1)} FPS
                </div>

                {/* Violation Flash Banner */}
                {violationAlert && (
                  <div className="absolute inset-x-0 bottom-4 mx-auto w-max max-w-[85%] px-5 py-2.5 rounded-lg bg-rose-950/90 border border-rose-500 text-rose-300 text-sm font-mono font-bold tracking-wider flex items-center gap-2 shadow-2xl animate-bounce">
                    <AlertTriangle className="w-5 h-5 text-rose-400 animate-spin" />
                    <span>{violationAlert}</span>
                  </div>
                )}
              </div>

              {/* Sub-Camera Selector Strip */}
              <div className="grid grid-cols-5 gap-2 mt-3">
                {cameras.map((cam, idx) => (
                  <button
                    key={cam.id}
                    onClick={() => setActiveCamIndex(idx)}
                    className={`p-2 rounded-lg border text-left transition-all ${
                      activeCamIndex === idx
                        ? "bg-cyan-500/15 border-cyan-500 text-white shadow-md shadow-cyan-500/10"
                        : "bg-slate-900/40 border-white/5 text-slate-400 hover:bg-white/5 hover:text-slate-200"
                    }`}
                  >
                    <div className="text-[10px] font-mono font-semibold">{cam.id}</div>
                    <div className="text-[9px] font-mono truncate text-slate-400">{cam.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Recent Uploads Panel */}
            <div className="glass-panel rounded-xl p-4 border border-white/10">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-bold tracking-wider text-white uppercase flex items-center gap-2">
                  <UploadCloud className="w-4 h-4 text-cyan-400" />
                  Recent Video Uploads & Batch Jobs
                </span>
                <span className="text-[11px] font-mono text-slate-400">Live DB Polling</span>
              </div>

              {recentUploads.length === 0 ? (
                <div className="p-6 text-center text-xs font-mono text-slate-400 border border-dashed border-white/10 rounded-lg">
                  No video upload jobs yet. Upload videos from the Video Analysis page.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {recentUploads.map((job) => (
                    <div
                      key={job.id}
                      className="p-3 rounded-lg bg-slate-900/60 border border-white/5 flex gap-3 items-center"
                    >
                      <div className="w-16 h-12 rounded bg-black flex-shrink-0 overflow-hidden relative border border-white/10">
                        {job.thumbnail_url ? (
                          <img
                            src={job.thumbnail_url}
                            alt={job.filename}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-400 text-xs">
                            🎥
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-mono text-white truncate font-medium">
                          {job.filename}
                        </div>
                        <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                          {job.vehicles_detected} vehicles ·{" "}
                          <span className="text-rose-400">{job.violations_flagged} violations</span>
                        </div>
                        <div className="mt-1 flex items-center gap-2">
                          <span
                            className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                              job.status === "COMPLETED"
                                ? "bg-emerald-500/20 text-emerald-400"
                                : job.status === "PROCESSING"
                                ? "bg-cyan-500/20 text-cyan-300 animate-pulse"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {job.status === "PROCESSING" ? `${Math.floor(job.progress)}%` : job.status}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Live Telemetry Logs & Detections Table (5 Cols on XL) */}
          <div className="xl:col-span-5 space-y-4 flex flex-col">
            {/* Live Telemetry Terminal */}
            <div className="glass-panel rounded-xl p-4 border border-white/10 flex-1 flex flex-col min-h-[260px]">
              <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-mono font-bold tracking-wider text-white uppercase">
                    Pipeline Telemetry Log
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setLogs([])}
                    className="text-[10px] font-mono text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded bg-white/5"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="flex-1 terminal-window rounded-lg p-3 text-xs overflow-y-auto space-y-1.5 max-h-[220px]">
                {logs.map((log) => {
                  const badgeColor =
                    log.source === "YOLOv8"
                      ? "text-cyan-400 bg-cyan-950/50"
                      : log.source === "DeepSORT"
                      ? "text-purple-400 bg-purple-950/50"
                      : log.source === "EasyOCR"
                      ? "text-emerald-400 bg-emerald-950/50"
                      : log.source === "RATG-OC"
                      ? "text-amber-400 bg-amber-950/50"
                      : "text-slate-400 bg-slate-900";

                  return (
                    <div key={log.id} className="leading-relaxed flex items-start gap-2">
                      <span className="text-[10px] text-slate-400 flex-shrink-0">{log.time}</span>
                      <span className={`text-[10px] px-1 py-0.2 rounded font-mono font-semibold flex-shrink-0 ${badgeColor}`}>
                        [{log.source}]
                      </span>
                      <span className="text-slate-300 font-mono break-words">{log.message}</span>
                    </div>
                  );
                })}
                <div ref={logEndRef} />
              </div>
            </div>

            {/* Real-time Tracking & Infractions Table */}
            <div className="glass-panel rounded-xl p-4 border border-white/10 flex-1 flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
                <span className="text-xs font-mono font-bold tracking-wider text-white uppercase flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  Real-Time Verified Track Stream
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {tableRows.length} Events
                </span>
              </div>

              <div className="flex-1 overflow-x-auto max-h-[300px]">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 text-[10px] uppercase">
                      <th className="pb-2">Vehicle</th>
                      <th className="pb-2">Plate No.</th>
                      <th className="pb-2">Speed</th>
                      <th className="pb-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {tableRows.slice(0, 15).map((row) => (
                      <tr key={row.id} className="hover:bg-white/5 transition-colors">
                        <td className="py-2 flex items-center gap-1.5 text-slate-300">
                          {getVehicleIcon(row.vehicle_class)}
                          <span>{row.vehicle_class}</span>
                        </td>
                        <td className="py-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                              row.plate_number !== "UNKNOWN"
                                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                                : "text-slate-400"
                            }`}
                          >
                            {row.plate_number}
                          </span>
                        </td>
                        <td className="py-2 text-slate-300">
                          {row.speed_kmh ? `${row.speed_kmh} km/h` : "—"}
                        </td>
                        <td className="py-2">
                          {row.violation_type ? (
                            <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-semibold text-[10px]">
                              {row.violation_type}
                            </span>
                          ) : (
                            <span className="text-emerald-400 text-[10px] flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> CLEAR
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {tableRows.length === 0 && (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-slate-400 font-mono text-xs">
                          Waiting for incoming vehicle tracks from pipeline...
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
