"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Video,
  FileSearch,
  Settings,
  ShieldAlert,
  Cpu,
  Activity,
  Layers
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [governorInfo, setGovernorInfo] = useState<string>("RATG-OC");

  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const data = await res.json();
          setBackendStatus("online");
          if (data.scheduling_governor) {
            setGovernorInfo(data.scheduling_governor);
          }
        } else {
          setBackendStatus("offline");
        }
      } catch (err) {
        setBackendStatus("offline");
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    {
      name: "Live Dashboard",
      href: "/",
      icon: Video,
      badge: "LIVE"
    },
    {
      name: "Video Analysis",
      href: "/video-analysis",
      icon: FileSearch
    },
    {
      name: "System Settings",
      href: "/settings",
      icon: Settings
    }
  ];

  return (
    <aside className="w-64 flex-shrink-0 bg-[#0a0e17] border-r border-white/10 flex flex-col justify-between select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 border-b border-white/10 flex items-center px-5 gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold tracking-wider text-sm text-white flex items-center gap-1.5">
              CITYWATCH
              <span className="text-[10px] bg-cyan-500/20 text-cyan-400 px-1.5 py-0.5 rounded font-mono font-medium">v2.1</span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono tracking-tight">RATG-OC SURVEILLANCE</div>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="p-3">
          <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 px-3 py-2 font-mono">
            Navigation Menu
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10"
                      : "text-slate-300 hover:text-white hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* System Intelligence Panel */}
        <div className="px-3 pt-3">
          <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 px-3 py-1 font-mono">
            Pipeline Architecture
          </div>
          <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" /> Detector
              </span>
              <span className="font-mono text-slate-200">YOLOv8n</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-400" /> Tracking
              </span>
              <span className="font-mono text-slate-200">DeepSORT</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-emerald-400" /> Governor
              </span>
              <span className="font-mono text-emerald-400 font-semibold text-[11px]">RATG-OC</span>
            </div>
          </div>
        </div>
      </div>

      {/* Backend Status Footer */}
      <div className="p-4 border-t border-white/10 bg-[#070b12]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                backendStatus === "online"
                  ? "bg-emerald-400 shadow-[0_0_8px_#10b981]"
                  : backendStatus === "checking"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-rose-500 shadow-[0_0_8px_#ef4444]"
              }`}
            />
            <span className="text-xs font-mono text-slate-300">
              {backendStatus === "online" ? "BACKEND ONLINE" : backendStatus === "checking" ? "CONNECTING..." : "BACKEND OFFLINE"}
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">8000</span>
        </div>
      </div>
    </aside>
  );
}
