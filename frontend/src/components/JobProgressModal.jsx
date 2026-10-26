import React, { useEffect, useRef } from 'react';
import { Loader2, CheckCircle2, AlertCircle, X } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 font-mono select-none">
      <div className="bg-white border-2 border-black w-full max-w-2xl shadow-brutal overflow-hidden flex flex-col max-h-[85vh]">
        {/* Terminal Header */}
        <div className="px-5 py-3.5 bg-black border-b border-black text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {isRunning && <Loader2 className="h-4 w-4 text-acid animate-spin" />}
            {isCompleted && <CheckCircle2 className="h-4 w-4 text-acid" />}
            {isFailed && <AlertCircle className="h-4 w-4 text-red-500" />}
            <div>
              <h3 className="font-bold text-white text-xs uppercase tracking-wider">
                {job.job_type.replace('_', ' ')} // TELEMETRY
              </h3>
              <p className="text-[10px] text-neutral-400">TASK_ID: {job.id}</p>
            </div>
          </div>
          {(isCompleted || isFailed) && (
            <button
              onClick={onClose}
              className="p-1 border border-neutral-700 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 hover:text-white transition"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Progress Bar & Current Step */}
        <div className="px-5 py-3 bg-neutral-100 border-b border-black space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-black uppercase text-[11px]">
              {job.current_step || (isRunning ? 'Processing...' : job.status)}
            </span>
            <span className="font-bold text-black">{Math.round(job.progress || 0)}%</span>
          </div>
          <div className="w-full bg-neutral-300 h-2 border border-black p-0">
            <div
              className={`h-full transition-all duration-300 ${
                isFailed ? 'bg-red-600' : 'bg-black'
              }`}
              style={{ width: `${job.progress || 0}%` }}
            ></div>
          </div>
        </div>

        {/* Streaming Logs Viewport */}
        <div className="p-4 bg-neutral-950 flex-1 overflow-hidden flex flex-col min-h-[220px]">
          <div className="text-[10px] uppercase tracking-widest text-neutral-400 font-bold mb-2 pb-1 border-b border-neutral-800 flex items-center justify-between">
            <span>CONSOLE_STDOUT</span>
            <span className="text-acid">{isRunning ? 'STREAMING...' : 'HALTED'}</span>
          </div>
          <div
            ref={terminalRef}
            className="flex-1 overflow-y-auto font-mono text-[11px] text-neutral-300 space-y-1 pr-2"
          >
            {job.logs && job.logs.length > 0 ? (
              job.logs.map((log, idx) => (
                <div key={idx} className="leading-snug">
                  <span className="text-neutral-600 mr-2 select-none">[{idx + 1}]</span>
                  <span className={log.includes('ERROR') || log.includes('failed') ? 'text-red-400' : 'text-neutral-200'}>
                    {log}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-neutral-600 italic">Awaiting worker thread handshake...</div>
            )}
          </div>
        </div>

        {/* Footer actions */}
        <div className="px-5 py-3 bg-white border-t border-black flex items-center justify-between">
          <span className="text-[10px] text-neutral-600 uppercase">
            STATUS: <strong className="text-black">{job.status}</strong>
          </span>
          {(isCompleted || isFailed) && (
            <button
              onClick={onClose}
              className="px-5 py-1.5 bg-black hover:bg-neutral-800 text-white font-mono text-xs font-bold uppercase tracking-wider border border-black shadow-brutal-sm"
            >
              Close Telemetry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
