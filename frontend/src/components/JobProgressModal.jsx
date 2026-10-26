import React, { useEffect, useRef } from 'react';
import { Loader2, CheckCircle2, AlertCircle, Terminal, X } from 'lucide-react';

export default function JobProgressModal({ job, onClose }) {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [job?.logs]);

  if (!job) return null;

  const isCompleted = job.status === 'COMPLETED';
  const isFailed = job.status === 'FAILED';
  const isRunning = job.status === 'RUNNING' || job.status === 'PENDING';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-teal-950/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-white border border-teal-850/30 rounded-3xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Retro-futuristic Deep Teal Header */}
        <div className="px-6 py-4 bg-teal-950 border-b border-teal-850 text-teal-100 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {isRunning && <Loader2 className="h-5 w-5 text-teal-300 animate-spin" />}
            {isCompleted && <CheckCircle2 className="h-5 w-5 text-teal-300" />}
            {isFailed && <AlertCircle className="h-5 w-5 text-rose-400" />}
            <div>
              <h3 className="font-bold text-teal-100 text-sm tracking-wide">
                {job.job_type.replace('_', ' ')} Pipeline Telemetry
              </h3>
              <p className="text-[11px] text-teal-400 font-mono">TASK_ID: {job.id}</p>
            </div>
          </div>
          {(isCompleted || isFailed) && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl hover:bg-teal-900 text-teal-300 hover:text-white transition"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Progress Bar & Current Step */}
        <div className="px-6 py-3.5 bg-teal-50 border-b border-teal-850/15 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-teal-950 font-mono">
              {job.current_step || (isRunning ? 'Processing...' : job.status)}
            </span>
            <span className="font-mono font-bold text-teal-800">{Math.round(job.progress || 0)}%</span>
          </div>
          <div className="w-full bg-teal-200/60 h-2 rounded-full overflow-hidden p-0.5">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                isFailed ? 'bg-rose-500' : 'bg-teal-700'
              }`}
              style={{ width: `${job.progress || 0}%` }}
            ></div>
          </div>
        </div>

        {/* Console / Log Terminal */}
        <div className="flex-1 p-4 bg-teal-950 text-teal-100 overflow-y-auto font-mono text-xs max-h-80" ref={terminalRef}>
          <div className="flex items-center space-x-2 text-teal-400 text-[10px] pb-2 mb-2 border-b border-teal-900 uppercase tracking-widest">
            <Terminal className="h-3 w-3" />
            <span>Telemetry Standard Output Stream</span>
          </div>
          <pre className="whitespace-pre-wrap leading-relaxed text-teal-200/90 text-[11px]">
            {job.logs || 'Connecting to daemon stream...\n'}
          </pre>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-white border-t border-teal-850/15 flex justify-end">
          <button
            onClick={onClose}
            disabled={isRunning}
            className={`px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition ${
              isRunning
                ? 'bg-teal-100 text-teal-400 cursor-not-allowed'
                : 'bg-teal-900 hover:bg-teal-850 text-teal-100 shadow-tactile'
            }`}
          >
            {isRunning ? 'Pipeline Active' : 'Close Console'}
          </button>
        </div>
      </div>
    </div>
  );
}
