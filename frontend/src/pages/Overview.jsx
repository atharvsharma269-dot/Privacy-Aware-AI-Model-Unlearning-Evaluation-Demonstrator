import React from 'react';
import {
  ArrowRight,
  Database,
  Trophy,
  GitCompare,
  Terminal,
} from 'lucide-react';

export default function Overview({ onNavigate, activeExperiment }) {
  return (
    <div className="space-y-12 max-w-6xl mx-auto pb-16">
      {/* Editorial Brutalist Hero Section - Breathing canvas with massive typography */}
      <div className="pt-4 pb-8 border-b-2 border-black space-y-6">
        <div className="inline-flex items-center space-x-2 border border-black bg-white px-3 py-1 font-mono text-[11px] font-bold uppercase tracking-widest text-black shadow-brutal-sm">
          <span className="h-2 w-2 bg-acid inline-block"></span>
          <span>NEURIPS BENCHMARK // GDPR ARTICLE 17 COMPLIANT</span>
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-sans font-black tracking-tighter text-black uppercase leading-[0.95]">
          Privacy-Aware <br />
          <span className="font-serif italic font-normal tracking-normal text-neutral-800">
            AI Model Unlearning
          </span> <br />
          Evaluation Demonstrator
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          <p className="md:col-span-2 font-mono text-xs sm:text-sm text-neutral-800 leading-relaxed bg-white border border-black p-4 shadow-brutal-sm">
            Deleting raw records from a database does not erase their statistical parameters from a deep neural network. 
            This research terminal evaluates exact retraining baselines against approximate unlearning algorithms, measuring 
            empirical privacy erasure, utility retention, and compute speedup under rigorous Membership Inference Attacks (MIA).
          </p>

          <div className="space-y-2 border border-black bg-neutral-100 p-4 font-mono text-xs shadow-brutal-sm flex flex-col justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-neutral-500 font-bold">
                SYSTEM SPECIFICATION
              </div>
              <div className="mt-2 text-neutral-900 font-bold">
                CORE: PyTorch 2.x + FastAPI
              </div>
              <div className="text-neutral-700 text-[11px] mt-1">
                BENCHMARKS: Fashion-MNIST / TOFU / Real F1 Facts
              </div>
            </div>
            <div className="pt-2 border-t border-neutral-300 text-[10px] text-neutral-500">
              AUDITED PROTOCOL // 24/24 TESTS PASSED
            </div>
          </div>
        </div>

        {/* Action Buttons: Stark black boxes with hover invert and moving arrows */}
        <div className="flex flex-wrap gap-3 pt-3">
          <button
            onClick={() => onNavigate('live-demo')}
            className="group px-6 py-3.5 bg-black hover:bg-neutral-900 text-white font-mono text-xs font-bold uppercase tracking-wider border border-black shadow-brutal transition-all flex items-center space-x-2 active:translate-x-0.5 active:translate-y-0.5"
          >
            <Trophy className="h-4 w-4 text-acid" />
            <span>Launch Live F1 Demo</span>
            <span className="group-hover:translate-x-1 transition-transform">&rarr;</span>
          </button>

          <button
            onClick={() => onNavigate('training')}
            className="group px-6 py-3.5 bg-white hover:bg-neutral-100 text-black font-mono text-xs font-bold uppercase tracking-wider border border-black shadow-brutal transition-all flex items-center space-x-2 active:translate-x-0.5 active:translate-y-0.5"
          >
            <span>Train Neural Model</span>
            <span className="group-hover:translate-x-1 transition-transform">&rarr;</span>
          </button>

          <button
            onClick={() => onNavigate('dataset')}
            className="px-6 py-3.5 bg-neutral-200 hover:bg-neutral-300 text-black font-mono text-xs font-bold uppercase tracking-wider border border-black shadow-brutal transition-all flex items-center space-x-2 active:translate-x-0.5 active:translate-y-0.5"
          >
            <Database className="h-4 w-4 text-neutral-700" />
            <span>Inspect Datasets</span>
          </button>
        </div>
      </div>

      {/* Three Fundamental Research Inquiries - Stark Editorial Cards with Faded Large Numbers */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-black pb-2">
          <div className="font-mono text-xs font-bold uppercase tracking-widest text-black flex items-center space-x-2">
            <span>// 03_FUNDAMENTAL_RESEARCH_INQUIRIES</span>
          </div>
          <span className="font-mono text-[10px] text-neutral-500 uppercase">THEORETICAL_FRAMEWORK</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          {/* Inquiry 01 */}
          <div className="relative border border-black bg-white p-6 shadow-brutal overflow-hidden flex flex-col justify-between">
            <span className="absolute -top-4 -right-2 font-mono text-8xl font-black text-neutral-200 select-none pointer-events-none">
              01
            </span>
            <div className="relative z-10 space-y-3">
              <div className="font-mono text-[10px] font-bold uppercase tracking-wider bg-black text-white px-2 py-0.5 inline-block">
                INQUIRY // PRIVACY_ERASURE
              </div>
              <h3 className="font-sans font-bold text-lg text-black uppercase leading-tight pt-1">
                Empirical Forgetting Verification
              </h3>
              <p className="font-mono text-xs text-neutral-700 leading-relaxed">
                Does the approximate unlearning algorithm genuinely eliminate statistical knowledge of the target data, as verified by elevated forget loss and resistance to Membership Inference Attacks (MIA)?
              </p>
            </div>
            <div className="relative z-10 mt-6 pt-3 border-t border-neutral-200 font-mono text-[11px] font-bold text-black flex items-center justify-between">
              <span>METRIC: MIA ROC-AUC + LOSS</span>
              <span>&rarr;</span>
            </div>
          </div>

          {/* Inquiry 02 */}
          <div className="relative border border-black bg-white p-6 shadow-brutal overflow-hidden flex flex-col justify-between">
            <span className="absolute -top-4 -right-2 font-mono text-8xl font-black text-neutral-200 select-none pointer-events-none">
              02
            </span>
            <div className="relative z-10 space-y-3">
              <div className="font-mono text-[10px] font-bold uppercase tracking-wider bg-black text-white px-2 py-0.5 inline-block">
                INQUIRY // UTILITY_RETENTION
              </div>
              <h3 className="font-sans font-bold text-lg text-black uppercase leading-tight pt-1">
                Preserved Knowledge Utility
              </h3>
              <p className="font-mono text-xs text-neutral-700 leading-relaxed">
                How much classification accuracy and predictive generalization does the unlearned model preserve on unaffected retained data partitions and independent test sets without catastrophic collapse?
              </p>
            </div>
            <div className="relative z-10 mt-6 pt-3 border-t border-neutral-200 font-mono text-[11px] font-bold text-black flex items-center justify-between">
              <span>METRIC: RETAIN & TEST ACC</span>
              <span>&rarr;</span>
            </div>
          </div>

          {/* Inquiry 03 */}
          <div className="relative border border-black bg-white p-6 shadow-brutal overflow-hidden flex flex-col justify-between">
            <span className="absolute -top-4 -right-2 font-mono text-8xl font-black text-neutral-200 select-none pointer-events-none">
              03
            </span>
            <div className="relative z-10 space-y-3">
              <div className="font-mono text-[10px] font-bold uppercase tracking-wider bg-black text-white px-2 py-0.5 inline-block">
                INQUIRY // COMPUTE_ROI
              </div>
              <h3 className="font-sans font-bold text-lg text-black uppercase leading-tight pt-1">
                Computational Speedup Factor
              </h3>
              <p className="font-mono text-xs text-neutral-700 leading-relaxed">
                What is the measured wall-clock runtime speedup achieved by approximate unlearning relative to retraining the golden reference baseline from scratch on the retained training partition?
              </p>
            </div>
            <div className="relative z-10 mt-6 pt-3 border-t border-neutral-200 font-mono text-[11px] font-bold text-black flex items-center justify-between">
              <span>METRIC: TIME_RETRAIN / TIME_UNLEARN</span>
              <span>&rarr;</span>
            </div>
          </div>
        </div>
      </div>

      {/* Experimental Pipeline Protocol - Sharp 4-Stage Blocks */}
      <div className="border border-black bg-white p-6 shadow-brutal space-y-6">
        <div className="flex items-center justify-between border-b border-black pb-3">
          <div className="flex items-center space-x-2 font-mono text-xs font-bold uppercase tracking-widest text-black">
            <GitCompare className="h-4 w-4 text-black" />
            <span>EXPERIMENTAL PROTOCOL // 4-STAGE PIPELINE</span>
          </div>
          <span className="font-mono text-[11px] bg-black text-white px-2 py-0.5 uppercase font-bold">
            RIGOROUS EVALUATION
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Step 1 */}
          <div className="border border-black p-4 bg-neutral-50 space-y-2">
            <div className="flex items-center justify-between font-mono">
              <span className="text-[10px] font-bold uppercase bg-black text-white px-1.5 py-0.5">
                [ STAGE_A ]
              </span>
              <span className="text-xs font-bold text-neutral-500">01</span>
            </div>
            <h4 className="font-sans font-bold text-sm text-black uppercase pt-1">Original Training</h4>
            <p className="font-mono text-[11px] text-neutral-700 leading-normal">
              Train neural network on complete training data D_train. Save original checkpoint and record baseline metrics.
            </p>
          </div>

          {/* Step 2 */}
          <div className="border border-black p-4 bg-neutral-50 space-y-2">
            <div className="flex items-center justify-between font-mono">
              <span className="text-[10px] font-bold uppercase bg-black text-white px-1.5 py-0.5">
                [ STAGE_B ]
              </span>
              <span className="text-xs font-bold text-neutral-500">02</span>
            </div>
            <h4 className="font-sans font-bold text-sm text-black uppercase pt-1">Deletion Request</h4>
            <p className="font-mono text-[11px] text-neutral-700 leading-normal">
              Partition training set into strictly disjoint Retain and Forget subsets (Random, Class-based, or Index-targeted).
            </p>
          </div>

          {/* Step 3 */}
          <div className="border border-black p-4 bg-neutral-50 space-y-2">
            <div className="flex items-center justify-between font-mono">
              <span className="text-[10px] font-bold uppercase bg-black text-white px-1.5 py-0.5">
                [ STAGE_C+D ]
              </span>
              <span className="text-xs font-bold text-neutral-500">03</span>
            </div>
            <h4 className="font-sans font-bold text-sm text-black uppercase pt-1">Retrain vs Unlearn</h4>
            <p className="font-mono text-[11px] text-neutral-700 leading-normal">
              Retrain golden baseline on D_retain from scratch. In parallel, run approximate unlearning from original checkpoint.
            </p>
          </div>

          {/* Step 4 */}
          <div className="border border-black p-4 bg-neutral-50 space-y-2">
            <div className="flex items-center justify-between font-mono">
              <span className="text-[10px] font-bold uppercase bg-black text-white px-1.5 py-0.5">
                [ STAGE_E ]
              </span>
              <span className="text-xs font-bold text-neutral-500">04</span>
            </div>
            <h4 className="font-sans font-bold text-sm text-black uppercase pt-1">3-Model Evaluation</h4>
            <p className="font-mono text-[11px] text-neutral-700 leading-normal">
              Conduct side-by-side verification: MIA ROC-AUC, prediction agreement, probability KL divergence, and speedup.
            </p>
          </div>
        </div>
      </div>

      {/* Active Experiment Readout Banner */}
      {activeExperiment && (
        <div className="border-2 border-black bg-black text-white p-6 shadow-brutal flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-[11px] text-acid font-bold uppercase">
              <span className="h-2 w-2 bg-acid inline-block"></span>
              <span>ACTIVE_EXPERIMENT_LOADED</span>
            </div>
            <h3 className="font-sans font-bold text-xl text-white uppercase tracking-tight">{activeExperiment.name}</h3>
            <p className="text-neutral-400 text-xs">
              DATASET: <span className="text-white font-bold">{activeExperiment.dataset_name}</span> | ARCH: <span className="text-white font-bold">{activeExperiment.model_name.toUpperCase()}</span> | STATUS: <span className="text-acid font-bold">{activeExperiment.status}</span>
            </p>
          </div>
          <button
            onClick={() => onNavigate('evaluation')}
            className="px-5 py-2.5 bg-acid text-black font-mono text-xs font-bold uppercase tracking-wider hover:bg-white transition flex items-center space-x-2 border border-black shadow-brutal-sm"
          >
            <span>Inspect Benchmark Matrix</span>
            <span>&rarr;</span>
          </button>
        </div>
      )}
    </div>
  );
}
