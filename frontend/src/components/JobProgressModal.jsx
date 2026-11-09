import React, { useState, useEffect, useRef } from 'react';
import { Loader2, CheckCircle2, AlertCircle, X, StopCircle, RefreshCw, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';

export default function JobProgressModal({ job, onClose, onCancel }) {
  const terminalRef = useRef(null);
  const [showConfirmCancel, setShowConfirmCancel] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [job?.logs]);

  if (!job) return null;

  const isCompleted = job.status === 'COMPLETED';
  const isFailed = job.status === 'FAILED';
  const isCancelled = job.status === 'CANCELLED';
  const isCancellationRequested = job.status === 'CANCELLATION_REQUESTED';
  const isRunning = job.status === 'RUNNING' || job.status === 'PENDING' || job.status === 'QUEUED';
  const isTerminal = isCompleted || isFailed || isCancelled;

  const handleCancelClick = () => {
    setShowConfirmCancel(true);
  };

  const handleConfirmCancel = async () => {
    setIsCancelling(true);
    setCancelError(null);
    try {
      if (onCancel) {
        await onCancel(job.id);
      } else {
        await api.cancelJob(job.id);
      }
      setShowConfirmCancel(false);
    } catch (err) {
      setCancelError(err.message || 'Failed to request cancellation');
    } finally {
      setIsCancelling(false);
    }
  };

  const telemetry = job.current_telemetry || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 font-mono select-none">
      <div className="bg-white border-2 border-black w-full max-w-2xl shadow-brutal overflow-hidden flex flex-col max-h-[90vh]">
        {/* Terminal Header */}
        <div className="px-5 py-3.5 bg-black border-b border-black text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {isRunning && <Loader2 className="h-4 w-4 text-acid animate-spin" />}
            {isCancellationRequested && <Loader2 className="h-4 w-4 text-amber-400 animate-spin" />}
            {isCompleted && <CheckCircle2 className="h-4 w-4 text-acid" />}
            {isCancelled && <StopCircle className="h-4 w-4 text-amber-400" />}
            {isFailed && <AlertCircle className="h-4 w-4 text-red-500" />}
            <div>
              <h3 className="font-bold text-white text-xs uppercase tracking-wider">
                {(job.job_type || 'TASK').replace(/_/g, ' ')} // TELEMETRY
              </h3>
              <p className="text-[10px] text-neutral-400">JOB_ID: {job.id}</p>
            </div>
          </div>
          {isTerminal && (
            <button
              onClick={onClose}
              className="p-1 border border-neutral-700 bg-neutral-900 hover:bg-neutral-800 text-neutral-300 hover:text-white transition"
              title="Close Modal"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Status & Cancellation Alert Banner */}
        {isCancellationRequested && (
          <div className="px-5 py-2.5 bg-amber-500 text-black font-bold text-xs flex items-center justify-between border-b border-black animate-pulse">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>HALT IN PROGRESS: Waiting for active PyTorch batch to complete safely...</span>
            </div>
          </div>
        )}

        {isCancelled && (
          <div className="px-5 py-2.5 bg-amber-100 text-amber-950 font-bold text-xs flex items-center justify-between border-b border-black">
            <div className="flex items-center space-x-2">
              <StopCircle className="h-4 w-4 text-amber-700 shrink-0" />
              <span>OPERATION CANCELLED: Staging cleared. Previous checkpoints preserved.</span>
            </div>
          </div>
        )}

        {isFailed && (
          <div className="px-5 py-2.5 bg-red-100 text-red-950 font-bold text-xs flex items-center justify-between border-b border-black">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-red-700 shrink-0" />
              <span>EXECUTION FAILED: {job.error || 'Encountered unrecoverable exception'}</span>
            </div>
          </div>
        )}

        {/* Progress Bar & Current Step */}
        <div className="px-5 py-3 bg-neutral-100 border-b border-black space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-black uppercase text-[11px] truncate max-w-[80%]">
              {job.current_step || (isCancelled ? 'Execution Halting Complete' : isRunning ? 'Processing...' : job.status)}
            </span>
            <span className="font-bold text-black">{Math.round(job.progress || 0)}%</span>
          </div>
          <div className="w-full bg-neutral-300 h-2 border border-black p-0">
            <div
              className={`h-full transition-all duration-300 ${
                isFailed ? 'bg-red-600' : isCancelled ? 'bg-amber-500' : isCancellationRequested ? 'bg-amber-400' : 'bg-black'
              }`}
              style={{ width: `${job.progress || 0}%` }}
            ></div>
          </div>
        </div>

        {/* Live Batch / Epoch Telemetry Grid if present */}
        {(telemetry.epoch !== undefined || telemetry.batch !== undefined) && (
          <div className="px-5 py-2.5 bg-neutral-900 border-b border-black grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] text-neutral-300">
            <div>
              <span className="text-neutral-500 block uppercase">Epoch</span>
              <span className="text-white font-bold">{telemetry.epoch}/{telemetry.total_epochs || '?'}</span>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase">Batch</span>
              <span className="text-white font-bold">{telemetry.batch}/{telemetry.total_batches || '?'}</span>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase">Batch Loss</span>
              <span className="text-acid font-bold">{telemetry.batch_loss != null ? telemetry.batch_loss.toFixed(4) : '--'}</span>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase">Elapsed</span>
              <span className="text-white font-bold">{telemetry.elapsed_seconds != null ? `${telemetry.elapsed_seconds.toFixed(1)}s` : '--'}</span>
            </div>
          </div>
        )}

        {/* Streaming Logs Viewport */}
        <div className="p-4 bg-neutral-950 flex-1 overflow-hidden flex flex-col min-h-[220px]">
          <div className="text-[10px] uppercase tracking-widest text-neutral-400 font-bold mb-2 pb-1 border-b border-neutral-800 flex items-center justify-between">
            <span>CONSOLE_STDOUT</span>
            <span className={isRunning ? 'text-acid' : isCancelled ? 'text-amber-400' : isFailed ? 'text-red-400' : 'text-neutral-500'}>
              {isRunning ? 'STREAMING...' : isCancellationRequested ? 'HALT REQUESTED' : isCancelled ? 'INTERRUPTED' : isCompleted ? 'DONE' : 'HALTED'}
            </span>
          </div>
          <div
            ref={terminalRef}
            className="flex-1 overflow-y-auto font-mono text-[11px] text-neutral-300 space-y-1 pr-2"
          >
            {job.logs && job.logs.length > 0 ? (
              job.logs.map((log, idx) => (
                <div key={idx} className="leading-snug">
                  <span className="text-neutral-600 mr-2 select-none">[{idx + 1}]</span>
                  <span
                    className={
                      log.includes('ERROR') || log.includes('failed')
                        ? 'text-red-400'
                        : log.includes('CANCEL') || log.includes('halt')
                        ? 'text-amber-300'
                        : log.includes('COMPLETE') || log.includes('SUCCESS')
                        ? 'text-acid'
                        : 'text-neutral-200'
                    }
                  >
                    {log}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-neutral-600 italic">Awaiting worker thread handshake...</div>
            )}
          </div>
        </div>

        {/* Confirmation Overlay for Cancel */}
        {showConfirmCancel && (
          <div className="p-4 bg-neutral-100 border-t-2 border-black space-y-3">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-xs">
                <p className="font-bold text-black uppercase">Confirm Abort Operation</p>
                <p className="text-neutral-700 mt-1">
                  The worker thread will stop execution at the current batch boundary. Any temporary staging files will be discarded, and existing checkpoints will remain unmodified.
                </p>
                {cancelError && <p className="text-red-600 mt-1 font-bold">{cancelError}</p>}
              </div>
            </div>
            <div className="flex justify-end space-x-2 pt-1">
              <button
                onClick={() => setShowConfirmCancel(false)}
                disabled={isCancelling}
                className="px-3 py-1.5 bg-neutral-200 hover:bg-neutral-300 text-black text-xs font-bold uppercase border border-black"
              >
                Continue Running
              </button>
              <button
                onClick={handleConfirmCancel}
                disabled={isCancelling}
                className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold uppercase border border-black flex items-center space-x-1"
              >
                {isCancelling ? <RefreshCw className="h-3 w-3 animate-spin" /> : <StopCircle className="h-3 w-3" />}
                <span>{isCancelling ? 'Halting...' : 'Yes, Stop Computation'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Footer actions */}
        <div className="px-5 py-3 bg-white border-t border-black flex items-center justify-between">
          <span className="text-[10px] text-neutral-600 uppercase">
            STATUS: <strong className="text-black">{job.status}</strong>
          </span>

          <div className="flex items-center space-x-2">
            {(isRunning && !isCancellationRequested && !showConfirmCancel) && (
              <button
                onClick={handleCancelClick}
                className="px-4 py-1.5 bg-neutral-100 hover:bg-red-50 text-red-600 hover:text-red-700 font-mono text-xs font-bold uppercase tracking-wider border border-red-300 hover:border-red-500 flex items-center space-x-1 transition"
              >
                <StopCircle className="h-3.5 w-3.5" />
                <span>Cancel Job</span>
              </button>
            )}

            {isTerminal && (
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
    </div>
  );
}
