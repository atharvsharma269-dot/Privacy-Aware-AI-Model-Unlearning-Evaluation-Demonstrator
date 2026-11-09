import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function SystemSettings({ hardware }) {
  const [healthData, setHealthData] = useState(null);
  const [isResetting, setIsResetting] = useState(false);
  const [resetStatus, setResetStatus] = useState(null);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealthData(data);
    } catch (err) {
      console.error('Failed to load health info:', err);
    }
  };

  const handleResetBenchmark = async () => {
    if (!window.confirm('Reset the active knowledge store back to the pristine TOFU benchmark?')) return;
    setIsResetting(true);
    setResetStatus(null);
    try {
      const res = await api.resetTOFUDemo();
      setResetStatus(res.message);
    } catch (err) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold tracking-wider">// SYSTEM_SETTINGS & ENVIRONMENT CONFIGURATION</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Render Free-Tier operational constraints, inference provider selection, and hardware diagnostics.
          </div>
        </div>

        <button
          onClick={loadHealth}
          className="px-3 py-1.5 bg-neutral-100 border border-black font-bold hover:bg-neutral-200"
        >
          REFRESH HEALTH
        </button>
      </div>

      {resetStatus && (
        <div className="p-3 bg-emerald-50 border border-emerald-500 text-emerald-800 font-bold">
          {resetStatus}
        </div>
      )}

      {/* Render Free Environment Card */}
      <div className="border border-black bg-white p-5 shadow-sm space-y-4">
        <div className="pb-2 border-b border-black font-bold flex items-center justify-between">
          <span>// RENDER_FREE_TIER_DEPLOYMENT_PROFILE</span>
          <span className="px-2 py-0.5 bg-acid text-black text-[10px] font-bold border border-black">
            OPTIMIZED_ACTIVE
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[11px]">
          <div className="p-3 bg-[#F8F9FA] border border-neutral-300">
            <span className="text-neutral-500 text-[10px]">EXECUTION RUNTIME:</span>
            <div className="font-bold text-black mt-1">CPU-Optimized (Torch CPU Wheels)</div>
            <div className="text-neutral-500 text-[10px] mt-1">Bundle Size: ~160MB vs 2.5GB CUDA</div>
          </div>

          <div className="p-3 bg-[#F8F9FA] border border-neutral-300">
            <span className="text-neutral-500 text-[10px]">MEMORY CONSTRAINTS:</span>
            <div className="font-bold text-black mt-1">512 MB Free Tier Limit</div>
            <div className="text-neutral-500 text-[10px] mt-1">Peak Memory: ~180MB (Safe margin)</div>
          </div>

          <div className="p-3 bg-[#F8F9FA] border border-neutral-300">
            <span className="text-neutral-500 text-[10px]">EPHEMERAL STORAGE:</span>
            <div className="font-bold text-black mt-1">Self-Healing Cold-Start</div>
            <div className="text-neutral-500 text-[10px] mt-1">Pre-bundled TOFU cache (~3.5MB)</div>
          </div>
        </div>

        <div className="p-3 bg-neutral-50 border border-neutral-300 text-[11px] leading-relaxed text-neutral-700">
          <strong>Render Commands:</strong><br />
          <code>Build Command: pip install -r requirements.txt</code><br />
          <code>Start Command: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT</code>
        </div>
      </div>

      {/* Hardware Diagnostics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-black bg-white p-5 shadow-sm space-y-3">
          <div className="pb-2 border-b border-black font-bold">// HARDWARE_DIAGNOSTICS</div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
              <span className="text-neutral-500">PLATFORM DEVICE:</span>
              <span className="font-bold text-black">{hardware?.device || 'cpu'}</span>
            </div>
            <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
              <span className="text-neutral-500">CPU CORE COUNT:</span>
              <span className="font-bold text-black">{hardware?.cpu_count || 4} Threads</span>
            </div>
            <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
              <span className="text-neutral-500">SYSTEM MEMORY TOTAL:</span>
              <span className="font-bold text-black">{hardware?.ram_total_gb ? `${hardware.ram_total_gb} GB` : 'Available'}</span>
            </div>
            <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
              <span className="text-neutral-500">PYTHON RUNTIME:</span>
              <span className="font-mono text-neutral-800 truncate max-w-xs">{healthData?.python_version || 'Python 3.11'}</span>
            </div>
          </div>
        </div>

        {/* Reset & Maintenance */}
        <div className="border border-black bg-white p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <div className="pb-2 border-b border-black font-bold">// BENCHMARK_RESET_CONTROL</div>
            <p className="text-[11px] text-neutral-600 mt-2 leading-relaxed">
              Resets the in-memory working knowledge store back to the pristine locuslab/TOFU benchmark (200 authors, 4,000 QA pairs). All redacted and unlearned author records will be restored to their active state.
            </p>
          </div>

          <div>
            <button
              onClick={handleResetBenchmark}
              disabled={isResetting}
              className="w-full py-2.5 bg-red-600 text-white font-bold border border-black hover:bg-red-700 disabled:opacity-50"
            >
              {isResetting ? 'RESTORING BENCHMARK...' : 'RESTORE PRISTINE TOFU BENCHMARK STORE'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
