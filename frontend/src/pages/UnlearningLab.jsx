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
} from 'lucide-react';
import { api } from '../services/api';

export default function UnlearningLab({ activeExperiment, onExperimentUpdated, onStartJob, onNavigate }) {
  const [algorithm, setAlgorithm] = useState('retain_fine_tuning');
  const [unlearnEpochs, setUnlearnEpochs] = useState(3);
  const [learningRate, setLearningRate] = useState(0.0003);
  const [alphaAscent, setAlphaAscent] = useState(0.4);
  const [betaProximity, setBetaProximity] = useState(0.01);
  const [maxForgetLoss, setMaxForgetLoss] = useState(2.35);

  const [retrainEpochs, setRetrainEpochs] = useState(5);
  const [isSubmittingUnlearn, setIsSubmittingUnlearn] = useState(false);
  const [isSubmittingRetrain, setIsSubmittingRetrain] = useState(false);
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
          {hasOriginal && hasPartition && (
            <span className="px-4 py-2 rounded-xl bg-teal-100 border border-teal-300 text-teal-950 text-xs flex items-center space-x-1.5 font-bold shadow-sm font-mono">
              <CheckCircle2 className="h-4 w-4 text-teal-800" />
              <span>PIPELINE READY</span>
            </span>
          )}
        </div>
      </div>

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
                onClick={() => setAlgorithm('retain_fine_tuning')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  algorithm === 'retain_fine_tuning'
                    ? 'border-teal-750 bg-teal-100/70 shadow-sm text-teal-950'
                    : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                }`}
              >
                <div className="font-bold text-xs text-teal-950 flex items-center space-x-1.5 font-mono">
                  <ShieldCheck className="h-4 w-4 text-teal-800" />
                  <span>Retain Fine-Tuning</span>
                </div>
                <p className="text-[10px] text-teal-700 mt-1 leading-relaxed font-medium">
                  Fine-tune original model strictly on Retain samples with reduced learning rate.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setAlgorithm('gradient_ascent')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  algorithm === 'gradient_ascent'
                    ? 'border-teal-750 bg-teal-100/70 shadow-sm text-teal-950'
                    : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                }`}
              >
                <div className="font-bold text-xs text-teal-950 flex items-center space-x-1.5 font-mono">
                  <Flame className="h-4 w-4 text-amber-700" />
                  <span>Gradient Ascent</span>
                </div>
                <p className="text-[10px] text-teal-700 mt-1 leading-relaxed font-medium">
                  Bounded loss maximization on forget set regularized by retain set cross-entropy.
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
      {(hasUnlearned || hasRetrained) && (
        <div className="p-6 rounded-3xl bg-teal-950 text-teal-100 border border-teal-850 shadow-tactile flex items-center justify-between">
          <div className="space-y-1">
            <h4 className="text-base font-bold text-white font-serif">Models Ready for Comprehensive Benchmark</h4>
            <p className="text-xs text-teal-200/80">
              Run the full 3-way evaluation suite (MIA attacks, KL-divergence, test degradation, and speedup ratios).
            </p>
          </div>
          <button
            onClick={() => onNavigate('evaluation')}
            className="px-6 py-3 rounded-xl bg-teal-300 hover:bg-teal-200 text-teal-950 font-bold text-xs uppercase tracking-wider transition shadow-tactile shrink-0"
          >
            Launch Evaluation Suite &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
