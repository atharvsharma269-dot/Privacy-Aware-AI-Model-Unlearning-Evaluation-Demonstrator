import React from 'react';
import { RefreshCw } from 'lucide-react';

export default function Navbar({ activeExperiment, hardware, onRefresh, isRefreshing }) {
  return (
    <header className="h-14 border-b border-black bg-white px-6 flex items-center justify-between sticky top-0 z-30 font-mono text-xs select-none">
      <div className="flex items-center space-x-4">
        {/* Project Branding */}
        <div className="flex items-center space-x-3">
          <div className="h-6 w-6 bg-black text-white flex items-center justify-center font-bold text-xs tracking-tighter">
            AI
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-sans font-bold text-sm tracking-tight text-black">
                MODEL UNLEARNING RESEARCH TERMINAL
              </span>
              <div className="flex items-center space-x-1.5 px-2 py-0.5 border border-black bg-neutral-100 text-[10px] font-bold">
                <span className="h-1.5 w-1.5 bg-[#00FF66] animate-pulse"></span>
                <span>SYS.STATUS: AUDITED</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Active Experiment Readout */}
        {activeExperiment && (
          <div className="hidden lg:flex items-center space-x-2 border border-black bg-neutral-100 px-2.5 py-1 text-[11px]">
            <span className="text-neutral-500">EXP_ID:</span>
            <span className="font-bold text-black max-w-[140px] truncate">{activeExperiment.name}</span>
            <span className="text-neutral-400">|</span>
            <span className="text-black font-bold uppercase">{activeExperiment.status}</span>
          </div>
        )}

        {/* Hardware Telemetry */}
        {hardware && (
          <div className="hidden md:flex items-center space-x-2 border border-neutral-300 bg-white px-2.5 py-1 text-[11px] text-neutral-700">
            <span>HW:</span>
            <span className="font-bold text-black">{hardware.cuda_available ? hardware.cuda_device_name : 'CPU_HOST'}</span>
            <span className="text-neutral-400">•</span>
            <span>{hardware.ram_available_gb}GB_FREE</span>
          </div>
        )}

        {/* Refresh Action */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="px-2.5 py-1 bg-black hover:bg-neutral-800 text-white border border-black transition text-[11px] font-bold flex items-center space-x-1 disabled:opacity-50"
          title="Refresh Experiment & Telemetry State"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin text-acid' : ''}`} />
          <span className="hidden sm:inline">SYNC</span>
        </button>
      </div>
    </header>
  );
}
