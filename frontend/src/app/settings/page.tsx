"use client";

import React, { useState, useEffect } from "react";
import Header from "@/components/Header";
import {
  Settings,
  Sliders,
  Cpu,
  Video,
  ShieldCheck,
  Save,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Sparkles
} from "lucide-react";

interface ConfigState {
  model: {
    yolo_weights: string;
    confidence_threshold: number;
    iou_threshold: number;
    classes: number[];
  };
  tracker: {
    max_age: number;
    n_init: number;
    nn_budget: number;
  };
  anpr: {
    ocr_language: string[];
    confidence_threshold: number;
  };
  camera: {
    sources: string[];
    fps: number;
  };
  violations: {
    speed_limit_kmh: number;
    pixels_per_meter: number;
    stop_line_y: number;
    signal_red_seconds: number;
    signal_green_seconds: number;
    helmet_edge_density_threshold: number;
  };
  ratg_oc: {
    enabled: boolean;
    weights: number[];
    tau_d: number;
    tau_z: number;
    tau_l: number;
    tau_c: number;
    stability_margin: number;
    k_max: number;
    cache_limit: number;
    hysteresis_delta: number;
    alpha: number;
    lambda_param: number;
    zone_distance: number;
  };
}

const defaultConfig: ConfigState = {
  model: {
    yolo_weights: "weights/yolov8n.pt",
    confidence_threshold: 0.25,
    iou_threshold: 0.45,
    classes: [2, 3, 5, 7],
  },
  tracker: {
    max_age: 30,
    n_init: 3,
    nn_budget: 100,
  },
  anpr: {
    ocr_language: ["en"],
    confidence_threshold: 0.6,
  },
  camera: {
    sources: ["rtsp://camera1.local/stream", "rtsp://camera2.local/stream"],
    fps: 30,
  },
  violations: {
    speed_limit_kmh: 40.0,
    pixels_per_meter: 10.0,
    stop_line_y: 250,
    signal_red_seconds: 10.0,
    signal_green_seconds: 10.0,
    helmet_edge_density_threshold: 0.12,
  },
  ratg_oc: {
    enabled: true,
    weights: [0.25, 0.20, 0.25, 0.15, 0.15],
    tau_d: 0.5,
    tau_z: 0.7,
    tau_l: 100.0,
    tau_c: 2.0,
    stability_margin: 0.5,
    k_max: 4,
    cache_limit: 10,
    hysteresis_delta: 0.05,
    alpha: 1.0,
    lambda_param: 0.5,
    zone_distance: 150.0,
  },
};

export default function SettingsPage() {
  const [config, setConfig] = useState<ConfigState>(defaultConfig);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/config");
        if (res.ok) {
          const data = await res.json();
          setConfig((prev) => ({
            ...prev,
            ...data,
            ratg_oc: { ...prev.ratg_oc, ...(data.ratg_oc || {}) },
            model: { ...prev.model, ...(data.model || {}) },
            tracker: { ...prev.tracker, ...(data.tracker || {}) },
            violations: { ...prev.violations, ...(data.violations || {}) },
            camera: { ...prev.camera, ...(data.camera || {}) },
          }));
        }
      } catch (err) {
        console.warn("Could not load /api/config, using default configuration:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveStatus(null);

    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (res.ok) {
        setSaveStatus("SUCCESS");
        setTimeout(() => setSaveStatus(null), 4000);
      } else {
        setSaveStatus("ERROR");
      }
    } catch (err) {
      console.error("Save error:", err);
      setSaveStatus("ERROR");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#07090e]">
      <Header
        title="System Parameters & RATG-OC Governance"
        subtitle="Operational Pipeline Configuration"
      />

      <div className="flex-1 p-5 overflow-y-auto space-y-6">
        <form onSubmit={handleSave} className="space-y-6 max-w-5xl">
          {/* RATG-OC Research Paper Parameters Panel */}
          <div className="glass-panel rounded-xl p-5 border border-cyan-500/30 shadow-lg shadow-cyan-500/5">
            <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <div>
                  <h3 className="text-sm font-mono font-bold text-white tracking-wider uppercase">
                    RATG-OC Scheduling & Consensus Governance (Paper Specification)
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                    Controls the supervisory risk governor ($r_t$) and track-level voting buffer ($C_i$).
                  </p>
                </div>
              </div>
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">
                Section III-A & III-B
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  RATG Gating Mode
                </label>
                <select
                  value={config.ratg_oc.enabled ? "true" : "false"}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, enabled: e.target.value === "true" },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-cyan-300 font-semibold focus:outline-none focus:border-cyan-500"
                >
                  <option value="true">Enabled (Adaptive Mode)</option>
                  <option value="false">Disabled (Full Fixed-Rate Baseline)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Risk Threshold (&tau;<sub>D</sub>)
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="1.0"
                  value={config.ratg_oc.tau_d}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, tau_d: parseFloat(e.target.value) || 0.5 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Boundary Override (&tau;<sub>Z</sub>)
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="1.0"
                  value={config.ratg_oc.tau_z}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, tau_z: parseFloat(e.target.value) || 0.7 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Max Propagate Frames (K<sub>max</sub>)
                </label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  value={config.ratg_oc.k_max}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, k_max: parseInt(e.target.value) || 4 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Laplacian Blur Gate (&tau;<sub>L</sub>)
                </label>
                <input
                  type="number"
                  step="10"
                  min="10"
                  value={config.ratg_oc.tau_l}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, tau_l: parseFloat(e.target.value) || 100.0 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Consensus Lock Weight (&tau;<sub>C</sub>)
                </label>
                <input
                  type="number"
                  step="0.2"
                  min="0.5"
                  value={config.ratg_oc.tau_c}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, tau_c: parseFloat(e.target.value) || 2.0 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Stability Margin (m)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={config.ratg_oc.stability_margin}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, stability_margin: parseFloat(e.target.value) || 0.5 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1.5 uppercase">
                  Voting Cache Size (B)
                </label>
                <input
                  type="number"
                  min="2"
                  max="30"
                  value={config.ratg_oc.cache_limit}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ratg_oc: { ...config.ratg_oc, cache_limit: parseInt(e.target.value) || 10 },
                    })
                  }
                  className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>

          {/* Model Weights & Tracker Parameters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* YOLOv8 Model Panel */}
            <div className="glass-panel rounded-xl p-5 border border-white/10">
              <div className="flex items-center gap-2 pb-3 border-b border-white/10 mb-4">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-mono font-bold text-white tracking-wider uppercase">
                  YOLOv8 Detection Weights
                </h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 font-semibold mb-1.5">
                    Model Checkpoint Path
                  </label>
                  <input
                    type="text"
                    value={config.model.yolo_weights}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        model: { ...config.model, yolo_weights: e.target.value },
                      })
                    }
                    className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-mono text-slate-400 font-semibold mb-1.5">
                      Confidence Threshold
                    </label>
                    <input
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="0.9"
                      value={config.model.confidence_threshold}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          model: { ...config.model, confidence_threshold: parseFloat(e.target.value) || 0.25 },
                        })
                      }
                      className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-mono text-slate-400 font-semibold mb-1.5">
                      IOU Threshold
                    </label>
                    <input
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="0.9"
                      value={config.model.iou_threshold}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          model: { ...config.model, iou_threshold: parseFloat(e.target.value) || 0.45 },
                        })
                      }
                      className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* DeepSORT Tracking Panel */}
            <div className="glass-panel rounded-xl p-5 border border-white/10">
              <div className="flex items-center gap-2 pb-3 border-b border-white/10 mb-4">
                <Sliders className="w-4 h-4 text-purple-400" />
                <h3 className="text-xs font-mono font-bold text-white tracking-wider uppercase">
                  DeepSORT Tracking Hyperparameters
                </h3>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-mono text-slate-400 font-semibold mb-1.5">
                      Track Max Age (Frames)
                    </label>
                    <input
                      type="number"
                      min="5"
                      max="100"
                      value={config.tracker.max_age}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          tracker: { ...config.tracker, max_age: parseInt(e.target.value) || 30 },
                        })
                      }
                      className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-mono text-slate-400 font-semibold mb-1.5">
                      Track Confirm (N-Init)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={config.tracker.n_init}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          tracker: { ...config.tracker, n_init: parseInt(e.target.value) || 3 },
                        })
                      }
                      className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-slate-400 font-semibold mb-1.5">
                    Speed Limit (km/h)
                  </label>
                  <input
                    type="number"
                    step="5"
                    min="20"
                    max="150"
                    value={config.violations.speed_limit_kmh}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        violations: { ...config.violations, speed_limit_kmh: parseFloat(e.target.value) || 40.0 },
                      })
                    }
                    className="w-full bg-slate-900 border border-white/10 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between p-4 rounded-xl glass-panel border border-white/10">
            <div className="flex items-center gap-2">
              {saveStatus === "SUCCESS" && (
                <span className="flex items-center gap-1.5 text-xs font-mono text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Configuration saved and synced to backend (default.yaml)!
                </span>
              )}
              {saveStatus === "ERROR" && (
                <span className="flex items-center gap-1.5 text-xs font-mono text-rose-400 font-semibold">
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                  Failed to connect to backend server.
                </span>
              )}
              {!saveStatus && (
                <span className="text-xs font-mono text-slate-400">
                  Changes will be merged in-place into backend/configs/default.yaml
                </span>
              )}
            </div>

            <button
              type="submit"
              disabled={saving}
              className="py-2.5 px-6 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-mono text-xs font-bold tracking-wider transition-colors shadow-lg shadow-cyan-600/25 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? "SAVING..." : "SAVE ALL CONFIGURATIONS"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
