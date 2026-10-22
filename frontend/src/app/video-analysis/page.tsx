"use client";

import React, { useState, useEffect, useRef } from "react";
import Header from "@/components/Header";
import {
  UploadCloud,
  FileCheck,
  Download,
  AlertCircle,
  Clock,
  Car,
  ShieldAlert,
  CheckCircle2,
  Filter,
  RefreshCw,
  FileSpreadsheet
} from "lucide-react";

interface UploadJob {
  id: string;
  filename: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  progress: number;
  thumbnail_url?: string;
  vehicles_detected: number;
  violations_flagged: number;
  timestamp?: string;
}

interface JobResultItem {
  id: number;
  track_id: number;
  vehicle_class: string;
  confidence: number;
  plate_number: string;
  plate_confidence?: number;
  violation_type: string | null;
  speed_kmh?: number;
  timestamp?: string;
}

export default function VideoAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [currentJob, setCurrentJob] = useState<UploadJob | null>(null);
  const [allJobs, setAllJobs] = useState<UploadJob[]>([]);
  const [results, setResults] = useState<JobResultItem[]>([]);
  const [loadingResults, setLoadingResults] = useState<boolean>(false);
  const [filterType, setFilterType] = useState<string>("ALL");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch all jobs on load
  const fetchJobs = async () => {
    try {
      const res = await fetch("/api/jobs?limit=20");
      if (res.ok) {
        const data = await res.json();
        setAllJobs(data);
        if (!currentJob && data.length > 0) {
          selectJob(data[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching jobs:", err);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  // Poll active job progress
  useEffect(() => {
    if (!currentJob || currentJob.status === "COMPLETED" || currentJob.status === "FAILED") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${currentJob.id}`);
        if (res.ok) {
          const updated = await res.json();
          setCurrentJob(updated);
          if (updated.status === "COMPLETED") {
            fetchResults(updated.id);
            fetchJobs();
          }
        }
      } catch (err) {
        console.error("Error polling job status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentJob]);

  // Fetch results for a job
  const fetchResults = async (jobId: string) => {
    setLoadingResults(true);
    try {
      const res = await fetch(`/api/jobs/${jobId}/results`);
      if (res.ok) {
        const data = await res.json();
        setResults(data);
      }
    } catch (err) {
      console.error("Error fetching results:", err);
    } finally {
      setLoadingResults(false);
    }
  };

  const selectJob = (job: UploadJob) => {
    setCurrentJob(job);
    if (job.status === "COMPLETED") {
      fetchResults(job.id);
    } else {
      setResults([]);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload_video", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        const newJob: UploadJob = {
          id: data.job_id,
          filename: data.filename,
          status: "PENDING",
          progress: 0,
          vehicles_detected: 0,
          violations_flagged: 0,
        };
        setCurrentJob(newJob);
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        fetchJobs();
      } else {
        alert("Upload failed. Ensure backend is running.");
      }
    } catch (err) {
      console.error("Upload error:", err);
      alert("Failed to connect to backend server.");
    } finally {
      setUploading(false);
    }
  };

  const downloadCSV = () => {
    if (!currentJob) return;
    window.open(`/api/jobs/${currentJob.id}/report.csv`, "_blank");
  };

  const filteredResults = results.filter((r) => {
    if (filterType === "VIOLATIONS_ONLY") return !!r.violation_type;
    if (filterType === "CLEAN_ONLY") return !r.violation_type;
    return true;
  });

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#07090e]">
      <Header
        title="Offline Video Analysis & Evidence Processing"
        subtitle="Batch RATG-OC Inspection Engine"
      />

      <div className="flex-1 p-5 overflow-y-auto space-y-5">
        {/* Top: Upload Card & Active Job Banner */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Upload Dropzone Form (5 cols) */}
          <div className="lg:col-span-5 glass-panel rounded-xl p-5 border border-white/10 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <UploadCloud className="w-5 h-5 text-cyan-400" />
                <h2 className="text-sm font-mono font-bold text-white tracking-wide uppercase">
                  Upload Surveillance Footage
                </h2>
              </div>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed font-sans">
                Upload MP4, AVI, or MOV intersection footage to evaluate through the complete
                RATG-OC pipeline (YOLOv8 + DeepSORT + EasyOCR + Violation checks).
              </p>

              <form onSubmit={handleUpload} className="space-y-4">
                <label className="border-2 border-dashed border-white/15 hover:border-cyan-500/50 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-colors bg-black/20">
                  <UploadCloud className="w-8 h-8 text-slate-400 mb-2" />
                  <span className="text-xs font-mono text-slate-300">
                    {file ? file.name : "Drag & drop video or click to browse"}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-1 font-mono">
                    H.264 / MP4 Recommended (up to 500 MB)
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </label>

                <button
                  type="submit"
                  disabled={!file || uploading}
                  className="w-full py-2.5 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-mono text-xs font-semibold tracking-wider transition-colors shadow-lg shadow-cyan-600/20 flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>UPLOADING TO PIPELINE...</span>
                    </>
                  ) : (
                    <>
                      <FileCheck className="w-4 h-4" />
                      <span>DISPATCH VIDEO FOR ANALYSIS</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Active Job Progress & Summary (7 cols) */}
          <div className="lg:col-span-7 glass-panel rounded-xl p-5 border border-white/10 flex flex-col justify-between">
            {currentJob ? (
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                      Selected Job Evaluation
                    </span>
                    <h3 className="text-sm font-mono font-bold text-white truncate max-w-md">
                      {currentJob.filename}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-mono px-2.5 py-1 rounded-md font-bold uppercase ${
                        currentJob.status === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : currentJob.status === "PROCESSING"
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 animate-pulse"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {currentJob.status}
                    </span>
                    {currentJob.status === "COMPLETED" && (
                      <button
                        onClick={downloadCSV}
                        className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-semibold transition-colors shadow-md shadow-emerald-600/20"
                      >
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                        <span>Export CSV</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress bar if processing */}
                {currentJob.status === "PROCESSING" && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
                      <span>RATG-OC Batch Execution</span>
                      <span className="text-cyan-400 font-bold">{Math.floor(currentJob.progress)}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                        style={{ width: `${currentJob.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Job KPI cards */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
                    <div className="text-[10px] font-mono text-slate-400 uppercase">Vehicles Detected</div>
                    <div className="text-xl font-bold font-mono text-white mt-1">
                      {currentJob.vehicles_detected}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
                    <div className="text-[10px] font-mono text-slate-400 uppercase">Infractions Flagged</div>
                    <div className="text-xl font-bold font-mono text-rose-400 mt-1">
                      {currentJob.violations_flagged}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
                    <div className="text-[10px] font-mono text-slate-400 uppercase">Infraction Rate</div>
                    <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                      {currentJob.vehicles_detected > 0
                        ? `${Math.round((currentJob.violations_flagged / currentJob.vehicles_detected) * 100)}%`
                        : "0%"}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs font-mono text-slate-400">
                Select an uploaded job below or upload new video footage to inspect findings.
              </div>
            )}
          </div>
        </div>

        {/* Results Data Table */}
        <div className="glass-panel rounded-xl p-5 border border-white/10 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-white/10">
            <div className="flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-mono font-bold text-white tracking-wider uppercase">
                Detailed Vehicle & Violation Registry
              </h3>
            </div>

            {/* Filter buttons */}
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setFilterType("ALL")}
                className={`px-3 py-1 rounded text-xs font-mono font-semibold transition-colors ${
                  filterType === "ALL"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:bg-white/5"
                }`}
              >
                All Records ({results.length})
              </button>
              <button
                onClick={() => setFilterType("VIOLATIONS_ONLY")}
                className={`px-3 py-1 rounded text-xs font-mono font-semibold transition-colors ${
                  filterType === "VIOLATIONS_ONLY"
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                    : "text-slate-400 hover:bg-white/5"
                }`}
              >
                Violations ({results.filter((r) => r.violation_type).length})
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 text-[10px] uppercase">
                  <th className="pb-2.5">Track ID</th>
                  <th className="pb-2.5">Classification</th>
                  <th className="pb-2.5">License Plate</th>
                  <th className="pb-2.5">Plate Conf</th>
                  <th className="pb-2.5">Speed</th>
                  <th className="pb-2.5">Infraction Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredResults.map((item, idx) => (
                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                    <td className="py-2.5 text-slate-300 font-semibold">#{item.track_id}</td>
                    <td className="py-2.5 text-slate-300">{item.vehicle_class}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded font-semibold text-xs ${
                          item.plate_number && item.plate_number !== "UNKNOWN"
                            ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                            : "text-slate-400"
                        }`}
                      >
                        {item.plate_number || "UNKNOWN"}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-400">
                      {item.plate_confidence ? `${Math.round(item.plate_confidence * 100)}%` : "—"}
                    </td>
                    <td className="py-2.5 text-slate-300">
                      {item.speed_kmh ? `${item.speed_kmh} km/h` : "—"}
                    </td>
                    <td className="py-2.5">
                      {item.violation_type ? (
                        <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-semibold text-[10px]">
                          {item.violation_type}
                        </span>
                      ) : (
                        <span className="text-emerald-400 text-[10px] flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> COMPLIANT
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredResults.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-400 font-mono text-xs">
                      {loadingResults ? "Loading job records..." : "No records matching current filter."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Upload Jobs History List */}
        <div className="glass-panel rounded-xl p-5 border border-white/10 space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <h3 className="text-xs font-mono font-bold text-white tracking-wider uppercase">
              Surveillance Batch Catalog
            </h3>
            <button
              onClick={fetchJobs}
              className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {allJobs.map((job) => (
              <div
                key={job.id}
                onClick={() => selectJob(job)}
                className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                  currentJob?.id === job.id
                    ? "bg-cyan-500/15 border-cyan-500 shadow-md shadow-cyan-500/10"
                    : "bg-slate-900/50 border-white/5 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-slate-400">ID: {job.id.slice(0, 8)}...</span>
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold uppercase ${
                      job.status === "COMPLETED"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : job.status === "PROCESSING"
                        ? "bg-cyan-500/20 text-cyan-300 animate-pulse"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {job.status}
                  </span>
                </div>
                <div className="text-xs font-mono text-white font-medium truncate mb-2">
                  {job.filename}
                </div>
                <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
                  <span>{job.vehicles_detected} vehicles</span>
                  <span className="text-rose-400">{job.violations_flagged} violations</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
