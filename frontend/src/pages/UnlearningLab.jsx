import React, { useState } from 'react';
import {
  FlaskConical,
  PlayCircle,
  RotateCcw,
  Sliders,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ShieldCheck,
  Flame,
  Zap,
  StopCircle,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';

export default function UnlearningLab({ activeExperiment, activeJob, onExperimentUpdated, onStartJob, onCancelJob, onNavigate }) {
  const [algorithm, setAlgorithm] = useState('gradient_ascent');
  const [unlearnEpochs, setUnlearnEpochs] = useState(3);
  const [learningRate, setLearningRate] = useState(0.0001);
  const [alphaAscent, setAlphaAscent] = useState(0.4);
  const [betaProximity, setBetaProximity] = useState(0.01);
  const [maxForgetLoss, setMaxForgetLoss] = useState(2.35);

  const [retrainEpochs, setRetrainEpochs] = useState(5);
  const [isSubmittingUnlearn, setIsSubmittingUnlearn] = useState(false);
  const [isSubmittingRetrain, setIsSubmittingRetrain] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [showConfirmCancel, setShowConfirmCancel] = useState(false);
  const [error, setError] = useState(null);

  const hasOriginal = Boolean(activeExperiment?.original_checkpoint_path);
  const hasPartition = Boolean(activeExperiment?.partition_manifest);
  const hasUnlearned = Boolean(activeExperiment?.unlearned_checkpoint_path);
  const hasRetrained = Boolean(activeExperiment?.retrained_checkpoint_path);

  const handleStartUnlearning = async () => {
    if (!activeExperiment?.id) return;
    setIsSubmittingUnlearn(true);
    setError(null);
    try {
      const payload = {
        algorithm,
        epochs: parseInt(unlearnEpochs),
        batch_size: 64,
        learning_rate: parseFloat(learningRate),
        alpha_ascent: parseFloat(alphaAscent),
        beta_proximity: parseFloat(betaProximity),
        max_forget_loss: parseFloat(maxForgetLoss),
      };

      const job = await api.runUnlearning(activeExperiment.id, payload);
      onStartJob(job.job_id);
    } catch (err) {
      setError(err.message || 'Failed to start unlearning job');
    } finally {
      setIsSubmittingUnlearn(false);
    }
  };

  const handleStartRetraining = async () => {
    if (!activeExperiment?.id) return;
    setIsSubmittingRetrain(true);
    setError(null);
    try {
      const payload = {
        epochs: parseInt(retrainEpochs),
        batch_size: 64,
        learning_rate: 0.001,
        optimizer: 'adam',
      };

      const job = await api.retrainModel(activeExperiment.id, payload);
      onStartJob(job.job_id);
    } catch (err) {
      setError(err.message || 'Failed to start exact retraining');
    } finally {
      setIsSubmittingRetrain(false);
    }
  };

  const isRelevantJob = activeJob &&
    activeJob.experiment_id === activeExperiment?.id &&
    (activeJob.job_type.startsWith('UNLEARN') || activeJob.job_type === 'EXACT_RETRAIN');
  const isJobRunning = isRelevantJob && (activeJob.status === 'RUNNING' || activeJob.status === 'QUEUED');
  const isCancellationRequested = isRelevantJob && activeJob.status === 'CANCELLATION_REQUESTED';
  const isCancelled = isRelevantJob && activeJob.status === 'CANCELLED';

  const handleCancel = async () => {
    if (!activeJob?.id) return;
    setIsCancelling(true);
    setError(null);
    try {
      if (onCancelJob) {
        await onCancelJob(activeJob.id);
      } else {
        await api.cancelJob(activeJob.id);
      }
      setShowConfirmCancel(false);
    } catch (err) {
      setError(err.message || 'Failed to cancel active job');
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-md bg-teal-900 text-teal-200">
              STAGE C & D
            </span>
            <span className="text-xs text-teal-800 font-semibold uppercase tracking-wider font-mono">Approximate vs Exact</span>
          </div>
          <h2 className="text-xl font-bold text-teal-950 mt-1 font-serif">Machine Unlearning Laboratory</h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Execute machine unlearning algorithms starting from original model weights, or train the exact golden reference model from scratch on retained data.
          </p>
        </div>

        {/* Readiness Pill */}
        <div className="flex items-center space-x-2">
          {isJobRunning && (
            <div className="flex items-center space-x-2">
              <span className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-amber-100 border border-amber-300 text-amber-950 text-xs font-mono font-bold animate-pulse">
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                <span>{activeJob.job_type} ({Math.round(activeJob.progress || 0)}%)</span>
              </span>
              <button
                onClick={() => setShowConfirmCancel(true)}
                disabled={isCancelling || isCancellationRequested}
                className="px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-mono font-bold uppercase transition flex items-center space-x-1 border border-black shadow-sm"
              >
                <StopCircle className="h-3.5 w-3.5" />
                <span>{isCancellationRequested ? 'Halting...' : 'Cancel'}</span>
              </button>
            </div>
          )}

          {!isJobRunning && isCancelled && (
            <span className="px-3 py-1.5 rounded-xl bg-neutral-200 border border-neutral-400 text-neutral-800 text-xs font-mono font-bold">
              JOB CANCELLED
            </span>
          )}

          {!hasOriginal && (
            <span className="px-3.5 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold font-mono">
              Needs Original Model Checkpoint
            </span>
          )}
          {!hasPartition && (
            <span className="px-3.5 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold font-mono">
              Needs Deletion Partition
            </span>
          )}
          {hasOriginal && hasPartition && !isJobRunning && (
            <span className="px-4 py-2 rounded-xl bg-teal-100 border border-teal-300 text-teal-950 text-xs flex items-center space-x-1.5 font-bold shadow-sm font-mono">
              <CheckCircle2 className="h-4 w-4 text-teal-800" />
              <span>PIPELINE READY</span>
            </span>
          )}
        </div>
      </div>

      {/* Confirmation Modal Banner */}
      {showConfirmCancel && (
        <div className="p-5 rounded-2xl bg-amber-50 border-2 border-amber-400 text-amber-950 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 font-mono text-xs">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
            <div>
              <p className="font-bold uppercase">Confirm Operation Interruption</p>
              <p className="text-[11px] text-amber-900 mt-0.5 font-sans">
                The active computation ({activeJob.job_type}) will halt safely at the next batch boundary. Partial weights in temporary staging will be cleaned up automatically.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => setShowConfirmCancel(false)}
              disabled={isCancelling}
              className="px-3.5 py-1.5 rounded-lg bg-neutral-200 hover:bg-neutral-300 text-black font-bold uppercase"
            >
              Continue Job
            </button>
            <button
              onClick={handleCancel}
              disabled={isCancelling}
              className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold uppercase flex items-center space-x-1"
            >
              {isCancelling ? <RefreshCw className="h-3 w-3 animate-spin" /> : <StopCircle className="h-3 w-3" />}
              <span>{isCancelling ? 'Halting...' : 'Yes, Stop Job'}</span>
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 font-medium">
          <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Two Comparative Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PANEL 1: Approximate Machine Unlearning (Stage D) */}
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-5 border-t-4 border-t-teal-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-9 w-9 rounded-xl bg-teal-100 flex items-center justify-center border border-teal-300/60">
                <FlaskConical className="h-5 w-5 text-teal-800" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-teal-950">Approximate Unlearning (Stage D)</h3>
                <p className="text-[11px] text-teal-700 font-medium">Fast parameter scrubbing without retraining from scratch</p>
              </div>
            </div>
            {hasUnlearned && (
              <span className="text-[10px] font-mono font-bold px-3 py-1 rounded-md bg-teal-100 text-teal-950 border border-teal-300">
                unlearned.pt Ready
              </span>
            )}
          </div>

          {/* Algorithm Mode Selection */}
          <div className="space-y-2.5">
            <label className="text-xs text-teal-950 font-bold block">Unlearning Algorithm:</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => {
                  setAlgorithm('gradient_ascent');
                  setLearningRate(0.0001);
                }}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  algorithm === 'gradient_ascent'
                    ? 'border-teal-750 bg-teal-100/70 shadow-sm text-teal-950'
                    : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-bold text-xs text-teal-950 flex items-center space-x-1.5 font-mono">
                    <Flame className="h-4 w-4 text-amber-700" />
                    <span>Gradient Ascent</span>
                  </div>
                  <span className="text-[9px] font-mono font-bold bg-[#00FF66] text-black px-1.5 py-0.5 border border-black">
                    RECOMMENDED
                  </span>
                </div>
                <p className="text-[10px] text-teal-700 mt-1 leading-relaxed font-medium">
                  Bounded loss maximization on forget set regularized by retain set cross-entropy. Demonstrated unlearning efficacy (Forget Acc ~82%, MIA AUC ~0.51).
                </p>
              </button>

              <button
                type="button"
                onClick={() => {
                  setAlgorithm('retain_fine_tuning');
                  setLearningRate(0.0003);
                }}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  algorithm === 'retain_fine_tuning'
                    ? 'border-teal-750 bg-teal-100/70 shadow-sm text-teal-950'
                    : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-bold text-xs text-teal-950 flex items-center space-x-1.5 font-mono">
                    <ShieldCheck className="h-4 w-4 text-teal-800" />
                    <span>Retain Fine-Tuning</span>
                  </div>
                  <span className="text-[9px] font-mono text-neutral-600 bg-neutral-200 px-1.5 py-0.5 border border-neutral-300">
                    BASELINE
                  </span>
                </div>
                <p className="text-[10px] text-teal-700 mt-1 leading-relaxed font-medium">
                  Fine-tune original model on Retain samples only. Updates weights, but retains high forget accuracy (~95%) and MIA vulnerability (~0.57) on classification.
                </p>
              </button>
            </div>
          </div>

          {/* Hyperparameters Form */}
          <div className="p-4 rounded-2xl bg-teal-50 border border-teal-850/15 space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-teal-800 block mb-1 font-bold">Unlearn Epochs:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={unlearnEpochs}
                  onChange={(e) => setUnlearnEpochs(e.target.value)}
                  className="w-full bg-white border border-teal-850/20 rounded-xl p-2 text-teal-950 font-mono text-xs font-semibold focus:ring-2 focus:ring-teal-700"
                />
              </div>

              <div>
                <label className="text-teal-800 block mb-1 font-bold">Learning Rate:</label>
                <input
                  type="number"
                  step="0.0001"
                  value={learningRate}
                  onChange={(e) => setLearningRate(e.target.value)}
                  className="w-full bg-white border border-teal-850/20 rounded-xl p-2 text-teal-950 font-mono text-xs font-semibold focus:ring-2 focus:ring-teal-700"
                />
              </div>
            </div>

            {algorithm === 'gradient_ascent' && (
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-teal-850/15">
                <div>
                  <label className="text-teal-800 block text-[10px] mb-1 font-bold uppercase font-mono">Ascent (α):</label>
                  <input
                    type="number"
                    step="0.1"
                    value={alphaAscent}
                    onChange={(e) => setAlphaAscent(e.target.value)}
                    className="w-full bg-white border border-teal-850/20 rounded-lg p-1.5 text-teal-950 font-mono text-[11px] font-semibold"
                  />
                </div>
                <div>
                  <label className="text-teal-800 block text-[10px] mb-1 font-bold uppercase font-mono">Proximity (β):</label>
                  <input
                    type="number"
                    step="0.01"
                    value={betaProximity}
                    onChange={(e) => setBetaProximity(e.target.value)}
                    className="w-full bg-white border border-teal-850/20 rounded-lg p-1.5 text-teal-950 font-mono text-[11px] font-semibold"
                  />
                </div>
                <div>
                  <label className="text-teal-800 block text-[10px] mb-1 font-bold uppercase font-mono">Ceiling (τ):</label>
                  <input
                    type="number"
                    step="0.1"
                    value={maxForgetLoss}
                    onChange={(e) => setMaxForgetLoss(e.target.value)}
                    className="w-full bg-white border border-teal-850/20 rounded-lg p-1.5 text-teal-950 font-mono text-[11px] font-semibold"
                  />
                </div>
              </div>
            )}
          </div>

          <button
            onClick={handleStartUnlearning}
            disabled={!hasOriginal || !hasPartition || isSubmittingUnlearn}
            className="w-full py-3.5 rounded-xl bg-teal-900 hover:bg-teal-850 text-white font-bold text-xs uppercase tracking-wider transition flex items-center justify-center space-x-2 shadow-tactile disabled:opacity-50"
          >
            {isSubmittingUnlearn ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-teal-300" />
                <span>Launching Unlearning Job...</span>
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 text-teal-300" />
                <span>Execute Approximate Unlearning</span>
              </>
            )}
          </button>
        </div>

        {/* PANEL 2: Exact Retraining Reference (Stage C) */}
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-5 border-t-4 border-t-teal-950">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-9 w-9 rounded-xl bg-teal-100 flex items-center justify-center border border-teal-300/60">
                <RotateCcw className="h-5 w-5 text-teal-900" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-teal-950">Exact Retraining Reference (Stage C)</h3>
                <p className="text-[11px] text-teal-700 font-medium">The theoretical gold standard: train from scratch on Retain set</p>
              </div>
            </div>
            {hasRetrained && (
              <span className="text-[10px] font-mono font-bold px-3 py-1 rounded-md bg-teal-100 text-teal-950 border border-teal-300">
                retrained.pt Ready
              </span>
            )}
          </div>

          <p className="text-xs text-teal-800 leading-relaxed font-normal">
            In unlearning science, exact retraining serves as the empirical ground truth reference. Because it has never observed the forget set, its weights contain mathematically zero residual information.
          </p>

          <div className="p-4 rounded-2xl bg-teal-50 border border-teal-850/15 space-y-2.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-teal-700 font-medium">Architecture</span>
              <span className="font-mono font-bold text-teal-950">Identical to Original ({activeExperiment?.model_name?.toUpperCase() || 'MLP'})</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-teal-700 font-medium">Training Samples</span>
              <span className="font-mono font-bold text-teal-900">Retain Set Only ({activeExperiment?.partition_manifest?.retain_count || 0})</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-teal-700 font-medium">Random Seed</span>
              <span className="font-mono font-bold text-teal-950">{activeExperiment?.seed || 42} (Deterministic)</span>
            </div>
          </div>

          <button
            onClick={handleStartRetraining}
            disabled={!hasPartition || isSubmittingRetrain}
            className="w-full py-3.5 rounded-xl bg-teal-950 hover:bg-teal-900 text-teal-100 font-bold text-xs uppercase tracking-wider transition flex items-center justify-center space-x-2 shadow-tactile disabled:opacity-50"
          >
            {isSubmittingRetrain ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-teal-300" />
                <span>Launching Retraining Job...</span>
              </>
            ) : (
              <>
                <RotateCcw className="h-4 w-4 text-teal-300" />
                <span>Train Exact Retrained Reference</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Navigation Callout */}
      {hasUnlearned && hasRetrained && (
        <div className="p-6 rounded-3xl bg-neutral-900 text-white border border-black shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-[#00FF66] animate-pulse"></span>
              <h4 className="text-sm font-bold font-mono uppercase text-white">All Checkpoints Ready for 3-Way Benchmark</h4>
            </div>
            <p className="text-xs text-neutral-300">
              Original, Unlearned, and Exact Retrained models are present. You can now execute the full scientific evaluation (Forget/Retain accuracy, MIA attack ROC-AUC, behavioral KL-divergence, and speedup factor).
            </p>
          </div>
          <button
            onClick={() => onNavigate('evaluation')}
            className="px-6 py-3 rounded-xl bg-[#00FF66] hover:bg-[#00dd55] text-black font-bold text-xs uppercase tracking-wider transition font-mono border border-black shrink-0"
          >
            Launch Full 3-Way Evaluation &rarr;
          </button>
        </div>
      )}

      {hasUnlearned && !hasRetrained && (
        <div className="p-6 rounded-3xl bg-amber-50 text-amber-950 border border-amber-300 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-amber-900 font-bold font-mono text-xs">
              <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
              <span>NOTICE: RETRAINED REFERENCE MODEL NOT YET EXECUTED</span>
            </div>
            <p className="text-xs text-amber-800">
              Your unlearned model is ready. However, the exact retrained reference has not been trained yet. If you evaluate now, retrained metrics will show N/A and speedup / behavioral similarity cannot be calculated. We strongly recommend running <strong>Train Exact Retrained Reference</strong> above.
            </p>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handleStartRetraining}
              disabled={isSubmittingRetrain}
              className="px-4 py-2.5 rounded-xl bg-amber-900 hover:bg-amber-800 text-white font-bold text-xs font-mono uppercase transition"
            >
              Train Reference First
            </button>
            <button
              onClick={() => onNavigate('evaluation')}
              className="px-4 py-2.5 rounded-xl bg-white hover:bg-neutral-100 text-neutral-900 font-bold text-xs font-mono border border-neutral-300 uppercase transition"
            >
              Evaluate Anyway &rarr;
            </button>
          </div>
        </div>
      )}

      {!hasUnlearned && hasRetrained && (
        <div className="p-5 rounded-2xl bg-neutral-100 border border-neutral-300 text-neutral-800 text-xs flex items-center justify-between font-mono">
          <span>Retrained reference model is ready. Execute an unlearning algorithm above to create the unlearned model.</span>
        </div>
      )}
    </div>
  );
}
