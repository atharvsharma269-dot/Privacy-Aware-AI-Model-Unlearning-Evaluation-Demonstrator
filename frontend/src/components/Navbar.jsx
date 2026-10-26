import React from 'react';
import { ShieldCheck, Cpu, RefreshCw } from 'lucide-react';

export default function Navbar({ activeExperiment, hardware, onRefresh, isRefreshing }) {
  return (
    <header className="h-16 border-b border-teal-850/20 bg-teal-100/70 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30 shadow-tactile">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-teal-900 border border-teal-700/60 flex items-center justify-center shadow-sm">
            <ShieldCheck className="h-5 w-5 text-teal-300" />
          </div>
          <div>
            <h1 className="font-bold text-teal-950 text-sm md:text-base leading-tight tracking-tight flex items-center space-x-2">
              <span className="font-serif tracking-tight">Privacy-Aware AI Model Unlearning</span>
              <span className="text-[10px] bg-teal-900 text-teal-200 border border-teal-700 px-2 py-0.5 rounded-md font-mono font-bold tracking-wider">
                AUDITED v1.0
              </span>
            </h1>
            <p className="text-[11px] text-teal-700 font-medium">Responsible AI & Empirical Privacy Demonstrator</p>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Active Experiment Badge */}
        {activeExperiment && (
          <div className="hidden lg:flex items-center space-x-2 bg-teal-950 text-teal-100 border border-teal-800 px-3.5 py-1.5 rounded-xl text-xs shadow-panel">
            <span className="h-2 w-2 rounded-full bg-teal-300 animate-pulse"></span>
            <span className="text-teal-400 font-mono text-[10px] uppercase">EXP:</span>
            <span className="font-semibold text-teal-100 max-w-[150px] truncate">{activeExperiment.name}</span>
            <span className="text-teal-700">|</span>
            <span className="font-mono text-teal-300 text-[10px] font-bold">{activeExperiment.status}</span>
          </div>
        )}

        {/* Hardware Status */}
        {hardware && (
          <div className="hidden md:flex items-center space-x-2 text-xs bg-white/80 border border-teal-800/15 px-3 py-1.5 rounded-xl text-teal-900 font-medium shadow-panel">
            <Cpu className="h-3.5 w-3.5 text-teal-700" />
            <span className="font-mono text-[11px]">{hardware.cuda_available ? hardware.cuda_device_name : 'CPU Accelerator'}</span>
            <span className="text-teal-400">•</span>
            <span className="font-mono text-[11px]">{hardware.ram_available_gb} GB Free</span>
          </div>
        )}

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-2 rounded-xl bg-white/90 hover:bg-teal-200/60 border border-teal-800/20 text-teal-900 transition shadow-panel disabled:opacity-50"
          title="Refresh application and experiment state"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-teal-700' : ''}`} />
        </button>
      </div>
    </header>
  );
}
