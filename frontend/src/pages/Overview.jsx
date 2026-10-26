import React from 'react';
import {
  ShieldAlert,
  ArrowRight,
  Sparkles,
  GitCompare,
  Database,
  Trophy,
  Terminal,
  Activity,
  CheckCircle2,
} from 'lucide-react';

export default function Overview({ onNavigate, activeExperiment, experimentsCount, hardware }) {
  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Editorial Research Hero Card */}
      <div className="p-8 md:p-10 rounded-3xl bg-teal-950 text-teal-100 shadow-tactile border border-teal-850 relative overflow-hidden">
        {/* Subtle geometric grid accent */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-teal-800/20 rounded-full blur-3xl pointer-events-none -mr-16 -mt-16"></div>
        <div className="absolute bottom-0 right-1/4 w-56 h-56 bg-teal-500/10 rounded-full blur-2xl pointer-events-none"></div>

        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-lg bg-teal-900 border border-teal-700/80 text-teal-300 text-[11px] font-mono font-bold tracking-wider uppercase">
            <Sparkles className="h-3.5 w-3.5 text-teal-300" />
            <span>Google NeurIPS Machine Unlearning Benchmark</span>
          </div>

          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white leading-tight font-serif">
            Privacy-Aware AI Model Unlearning Demonstrator
          </h2>

          <p className="text-teal-200/90 text-sm leading-relaxed font-normal">
            When users exercise the Right to be Forgotten (GDPR Article 17), simply deleting database records does not eliminate their statistical influence from a trained neural network. This platform provides an interactive research instrument to evaluate selective machine unlearning algorithms against golden retraining references, quantifying privacy leakage, utility retention, and compute efficiency.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              onClick={() => onNavigate('live-demo')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-teal-300 hover:bg-teal-200 text-teal-950 font-bold text-xs uppercase tracking-wider transition shadow-tactile"
            >
              <Trophy className="h-4 w-4 text-teal-900" />
              <span>Launch Live F1 Demo</span>
            </button>
            <button
              onClick={() => onNavigate('training')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-teal-800 hover:bg-teal-700 text-teal-100 font-bold text-xs uppercase tracking-wider transition border border-teal-700/80 shadow-tactile"
            >
              <span>Train Neural Model</span>
              <ArrowRight className="h-4 w-4 text-teal-300" />
            </button>
            <button
              onClick={() => onNavigate('dataset')}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-teal-900/80 hover:bg-teal-850 text-teal-300 border border-teal-700/60 font-bold text-xs uppercase tracking-wider transition"
            >
              <Database className="h-4 w-4 text-teal-400" />
              <span>Inspect Datasets</span>
            </button>
          </div>
        </div>
      </div>

      {/* 3 Core Research Inquiries - Pale Aqua Geometric Panels */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <div className="h-7 w-7 rounded-lg bg-teal-100 flex items-center justify-center border border-teal-300/60">
            <ShieldAlert className="h-4 w-4 text-teal-800" />
          </div>
          <h3 className="text-base font-extrabold text-teal-950">Three Fundamental Research Inquiries</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Card 1 */}
          <div className="p-6 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile hover:shadow-tactile-hover transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-8 w-8 rounded-lg bg-teal-950 text-teal-300 font-bold text-xs flex items-center justify-center font-mono border border-teal-800">
                  01
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-white/90 text-teal-900 border border-teal-300/60 uppercase">
                  Forgetting Efficacy
                </span>
              </div>
              <h4 className="font-bold text-teal-950 text-sm">Empirical Forgetting Verification</h4>
              <p className="text-xs text-teal-800/90 leading-relaxed">
                Does the approximate unlearning algorithm genuinely eliminate knowledge of forgotten samples, as measured by elevated forget loss and resistance to Membership Inference Attacks (MIA)?
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-teal-800/10 flex items-center text-[11px] font-bold text-teal-900">
              <span>Evaluated via MIA ROC-AUC & Loss</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1 text-teal-700" />
            </div>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile hover:shadow-tactile-hover transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-8 w-8 rounded-lg bg-teal-950 text-teal-300 font-bold text-xs flex items-center justify-center font-mono border border-teal-800">
                  02
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-white/90 text-teal-900 border border-teal-300/60 uppercase">
                  Utility Preservation
                </span>
              </div>
              <h4 className="font-bold text-teal-950 text-sm">Retained Knowledge Utility</h4>
              <p className="text-xs text-teal-800/90 leading-relaxed">
                How much classification accuracy and generalization capacity does the model retain on unaffected data partitions and independent test splits without suffering catastrophic collapse?
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-teal-800/10 flex items-center text-[11px] font-bold text-teal-900">
              <span>Evaluated on Retain & Test Splits</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1 text-teal-700" />
            </div>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-2xl bg-teal-100/70 border border-teal-800/15 shadow-tactile hover:shadow-tactile-hover transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="h-8 w-8 rounded-lg bg-teal-950 text-teal-300 font-bold text-xs flex items-center justify-center font-mono border border-teal-800">
                  03
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-white/90 text-teal-900 border border-teal-300/60 uppercase">
                  Computational Speedup
                </span>
              </div>
              <h4 className="font-bold text-teal-950 text-sm">Computational ROI & Efficiency</h4>
              <p className="text-xs text-teal-800/90 leading-relaxed">
                How much training duration and compute utilization does approximate unlearning save compared to exact retraining from scratch: <code className="text-teal-950 font-bold bg-white/80 px-1 py-0.5 rounded font-mono text-[10px]">Speedup = Retrain / Unlearn</code>?
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-teal-800/10 flex items-center text-[11px] font-bold text-teal-900">
              <span>Measured in Clock Execution Seconds</span>
              <ArrowRight className="h-3.5 w-3.5 ml-1 text-teal-700" />
            </div>
          </div>
        </div>
      </div>

      {/* Experimental Flow Roadmap */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="h-7 w-7 rounded-lg bg-teal-100 flex items-center justify-center border border-teal-300/60">
              <GitCompare className="h-4 w-4 text-teal-800" />
            </div>
            <h3 className="text-base font-extrabold text-teal-950">Experimental Pipeline Protocol</h3>
          </div>
          <span className="text-xs font-mono text-teal-700 font-bold">4-STAGE VERIFICATION CYCLE</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Step 1 */}
          <div className="p-5 rounded-2xl bg-teal-50 border border-teal-850/10 space-y-2.5 hover:border-teal-400 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-teal-950 text-teal-200">
                Stage A
              </span>
              <div className="h-6 w-6 rounded-md bg-teal-200 text-teal-950 flex items-center justify-center font-bold text-xs font-mono">
                1
              </div>
            </div>
            <h5 className="font-bold text-teal-950 text-sm">Original Training</h5>
            <p className="text-xs text-teal-800/80 leading-relaxed">
              Train baseline neural model on the complete training set. Save checkpoint and establish benchmark metrics.
            </p>
          </div>

          {/* Step 2 */}
          <div className="p-5 rounded-2xl bg-teal-50 border border-teal-850/10 space-y-2.5 hover:border-teal-400 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-teal-900 text-teal-200">
                Stage B
              </span>
              <div className="h-6 w-6 rounded-md bg-teal-200 text-teal-950 flex items-center justify-center font-bold text-xs font-mono">
                2
              </div>
            </div>
            <h5 className="font-bold text-teal-950 text-sm">Deletion Request</h5>
            <p className="text-xs text-teal-800/80 leading-relaxed">
              Submit deletion request (Random, Class-based, or Index-specific). Create strictly disjoint Retain and Forget subsets.
            </p>
          </div>

          {/* Step 3 */}
          <div className="p-5 rounded-2xl bg-teal-50 border border-teal-850/10 space-y-2.5 hover:border-teal-400 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-teal-800 text-teal-200">
                Stage C & D
              </span>
              <div className="h-6 w-6 rounded-md bg-teal-200 text-teal-950 flex items-center justify-center font-bold text-xs font-mono">
                3
              </div>
            </div>
            <h5 className="font-bold text-teal-950 text-sm">Retrain vs Unlearn</h5>
            <p className="text-xs text-teal-800/80 leading-relaxed">
              Retrain golden baseline on Retain data from scratch. Execute approximate unlearning (Retain Fine-Tuning or Gradient Ascent).
            </p>
          </div>

          {/* Step 4 */}
          <div className="p-5 rounded-2xl bg-teal-50 border border-teal-850/10 space-y-2.5 hover:border-teal-400 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-teal-700 text-teal-200">
                Stage E
              </span>
              <div className="h-6 w-6 rounded-md bg-teal-200 text-teal-950 flex items-center justify-center font-bold text-xs font-mono">
                4
              </div>
            </div>
            <h5 className="font-bold text-teal-950 text-sm">3-Way Evaluation</h5>
            <p className="text-xs text-teal-800/80 leading-relaxed">
              Compare Original, Retrained, and Unlearned models: evaluate forget loss, MIA ROC-AUC, prediction agreement, and speedup.
            </p>
          </div>
        </div>
      </div>

      {/* Active Experiment Capsule Banner */}
      {activeExperiment && (
        <div className="p-6 rounded-3xl bg-teal-950 text-teal-100 border border-teal-850 shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-teal-300 animate-pulse"></span>
              <span className="text-xs font-bold text-teal-300 uppercase tracking-widest font-mono">Active Experiment Selected</span>
            </div>
            <h4 className="text-xl font-bold text-white font-serif">{activeExperiment.name}</h4>
            <p className="text-xs text-teal-300/80">
              Dataset: <span className="font-mono text-white font-semibold">{activeExperiment.dataset_name}</span> | Model: <span className="font-mono text-white font-semibold">{activeExperiment.model_name.toUpperCase()}</span> | Seed: <span className="font-mono text-white font-semibold">{activeExperiment.seed}</span> | Status: <span className="font-mono text-teal-300 font-bold">{activeExperiment.status}</span>
            </p>
          </div>
          <button
            onClick={() => onNavigate('evaluation')}
            className="px-5 py-2.5 rounded-xl bg-teal-300 hover:bg-teal-200 text-teal-950 font-bold text-xs uppercase tracking-wider transition self-start md:self-auto shrink-0 flex items-center space-x-2 shadow-tactile"
          >
            <span>View Full Evaluation</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
