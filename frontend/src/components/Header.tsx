"use client";

import React, { useEffect, useState } from "react";
import { Clock, Shield, Sparkles } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    function updateClock() {
      const now = new Date();
      setTimeStr(
        now.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric"
        }) + " " + now.toLocaleTimeString("en-GB", { hour12: false })
      );
    }
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="min-h-16 border-b border-white/10 bg-[#0a0e17]/90 backdrop-blur-md px-6 py-3 flex flex-wrap items-center justify-between gap-3 flex-shrink-0 z-10">
      <div className="min-w-0">
        <h1 className="text-base font-bold text-white tracking-wide truncate">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-slate-400 font-mono truncate">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {/* Paper Innovation Tag */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs font-mono text-cyan-300">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>IEEE RATG-OC Engine</span>
        </div>

        {/* Live Clock */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs font-mono text-slate-300">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>{timeStr || "LOADING TIME..."}</span>
        </div>

        {/* System Secure Indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span className="hidden sm:inline">SYSTEM SECURED</span>
        </div>
      </div>
    </header>
  );
}
