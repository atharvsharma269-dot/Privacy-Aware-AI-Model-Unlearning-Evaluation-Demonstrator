import React, { useState } from 'react';
import {
  BarChart3,
  ShieldAlert,
  PlayCircle,
  GitCompare,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Layers,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
  CartesianGrid,
} from 'recharts';
import MetricCard from '../components/MetricCard';
import { api } from '../services/api';

export default function EvaluationDashboard({ activeExperiment, onExperimentUpdated, onStartJob }) {
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState(null);

  const metrics = activeExperiment?.metrics;
  const orig = metrics?.original_model;
  const unl = metrics?.unlearned_model;
  const ret = metrics?.retrained_model;
  const mia = metrics?.mia;
  const sim = metrics?.behavioral_similarity;
  const speedup = metrics?.speedup_factor;

  const hasCheckpoints = Boolean(
    activeExperiment?.original_checkpoint_path && activeExperiment?.unlearned_checkpoint_path
  );

  const handleRunEvaluation = async () => {
    if (!activeExperiment?.id) return;
    setIsEvaluating(true);
    setError(null);
    try {
      const job = await api.evaluateExperiment(activeExperiment.id);
      onStartJob(job.job_id);
    } catch (err) {
      setError(err.message || 'Failed to start evaluation suite');
    } finally {
      setIsEvaluating(false);
    }
  };

  const partitionChartData = [
    {
      partition: 'Retain Set Acc (%)',
      Original: orig?.retain?.accuracy || 0,
      Retrained: ret?.retain?.accuracy || 0,
      Unlearned: unl?.retain?.accuracy || 0,
    },
    {
      partition: 'Forget Set Acc (%)',
      Original: orig?.forget?.accuracy || 0,
      Retrained: ret?.forget?.accuracy || 0,
      Unlearned: unl?.forget?.accuracy || 0,
    },
    {
      partition: 'Test Set Acc (%)',
      Original: orig?.test?.accuracy || 0,
      Retrained: ret?.test?.accuracy || 0,
      Unlearned: unl?.test?.accuracy || 0,
    },
  ];

  const rocPoints = mia?.unlearned?.roc_curve || [];

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-md bg-teal-900 text-teal-200">
              STAGE E
            </span>
            <span className="text-xs text-teal-800 font-semibold uppercase tracking-wider font-mono">Three-Model Benchmark</span>
          </div>
          <h2 className="text-xl font-bold text-teal-950 mt-1 font-serif">Multi-Faceted Evaluation Dashboard</h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Empirical comparison across forgetting efficacy, generalization retention, MIA vulnerability, and compute speedup.
          </p>
        </div>

        <button
          onClick={handleRunEvaluation}
          disabled={!hasCheckpoints || isEvaluating}
          className="px-6 py-3 rounded-xl bg-teal-950 hover:bg-teal-900 text-teal-100 font-bold text-xs uppercase tracking-wider transition flex items-center space-x-2 shadow-tactile disabled:opacity-50"
        >
          {isEvaluating ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin text-teal-300" />
              <span>Evaluating Models...</span>
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4 text-teal-300" />
              <span>{metrics ? 'Re-Run Evaluation Suite' : 'Execute Full Evaluation'}</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 font-medium">
          <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {metrics ? (
        <>
          {/* Top KPI Cards with Accent Borders */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              title="Retained Utility"
              value={unl?.test?.accuracy}
              unit="%"
              subtitle={`Degradation: ${unl?.utility_degradation_pct || 0}%`}
              variant="emerald"
            />
            <MetricCard
              title="Forget Set Acc"
              value={unl?.forget?.accuracy}
              unit="%"
              subtitle={`Retrained Ref: ${ret?.forget?.accuracy ?? 'N/A'}%`}
              variant="amber"
            />
            <MetricCard
              title="MIA Attack ROC-AUC"
              value={mia?.unlearned?.roc_auc}
              subtitle={`Original AUC: ${mia?.original?.roc_auc ?? 'N/A'}`}
              variant="purple"
            />
            <MetricCard
              title="Compute Speedup"
              value={speedup ? `${speedup}x` : 'N/A'}
              subtitle={`${unl?.unlearning_time_seconds || 0}s vs ${ret?.retraining_time_seconds || 0}s`}
              variant="blue"
            />
          </div>

          {/* Three-Model Master Comparison Table */}
          <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2 font-serif">
                <GitCompare className="h-4 w-4 text-teal-800" />
                <span>Unified 3-Model Empirical Matrix</span>
              </h3>
              <span className="text-xs text-teal-700 font-mono font-medium">Statistical Ground Truth</span>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-teal-850/15">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-teal-950 text-white font-mono">
                    <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Evaluation Dimension</th>
                    <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px] text-teal-300">
                      1. Original Model
                    </th>
                    <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px] text-teal-200 bg-teal-900">
                      2. Retrained Baseline (Reference)
                    </th>
                    <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px] text-teal-100 bg-teal-850">
                      3. Unlearned Model (Approximate)
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-teal-850/15 font-mono text-teal-950 bg-white">
                  <tr className="hover:bg-teal-50/50 transition">
                    <td className="py-3.5 px-4 font-sans font-bold text-teal-950">Retain Set Accuracy</td>
                    <td className="py-3.5 px-4 font-semibold">{orig?.retain?.accuracy}%</td>
                    <td className="py-3.5 px-4 bg-teal-100/50 text-teal-950 font-extrabold">{ret?.retain?.accuracy ?? 'N/A'}%</td>
                    <td className="py-3.5 px-4 bg-teal-200/40 text-teal-900 font-extrabold">{unl?.retain?.accuracy}%</td>
                  </tr>
                  <tr className="hover:bg-teal-50/50 transition">
                    <td className="py-3.5 px-4 font-sans font-bold text-teal-950">Forget Set Accuracy</td>
                    <td className="py-3.5 px-4 text-rose-600 font-semibold">{orig?.forget?.accuracy}% (Memorized)</td>
                    <td className="py-3.5 px-4 bg-teal-100/50 text-teal-950 font-extrabold">{ret?.forget?.accuracy ?? 'N/A'}% (Zero-Knowledge)</td>
                    <td className="py-3.5 px-4 bg-teal-200/40 text-teal-900 font-extrabold">{unl?.forget?.accuracy}%</td>
                  </tr>
                  <tr className="hover:bg-teal-50/50 transition">
                    <td className="py-3.5 px-4 font-sans font-bold text-teal-950">Forget Set Loss</td>
                    <td className="py-3.5 px-4">{orig?.forget?.loss}</td>
                    <td className="py-3.5 px-4 bg-teal-100/50 font-semibold">{ret?.forget?.loss ?? 'N/A'}</td>
                    <td className="py-3.5 px-4 bg-teal-200/40 font-semibold text-teal-900">{unl?.forget?.loss}</td>
                  </tr>
                  <tr className="hover:bg-teal-50/50 transition">
                    <td className="py-3.5 px-4 font-sans font-bold text-teal-950">Test Generalization Acc</td>
                    <td className="py-3.5 px-4">{orig?.test?.accuracy}%</td>
                    <td className="py-3.5 px-4 bg-teal-100/50 font-semibold">{ret?.test?.accuracy ?? 'N/A'}%</td>
                    <td className="py-3.5 px-4 bg-teal-200/40 font-bold text-teal-900">{unl?.test?.accuracy}%</td>
                  </tr>
                  <tr className="hover:bg-teal-50/50 transition">
                    <td className="py-3.5 px-4 font-sans font-bold text-teal-950">MIA Attack ROC-AUC</td>
                    <td className="py-3.5 px-4 text-rose-600 font-bold">{mia?.original?.roc_auc ?? 'N/A'} (High Risk)</td>
                    <td className="py-3.5 px-4 bg-teal-100/50 text-teal-950 font-bold">{mia?.retrained?.roc_auc ?? 'N/A'} (Baseline)</td>
                    <td className="py-3.5 px-4 bg-teal-200/40 text-teal-900 font-bold">{mia?.unlearned?.roc_auc ?? 'N/A'}</td>
                  </tr>
                  <tr className="hover:bg-teal-50/50 transition">
                    <td className="py-3.5 px-4 font-sans font-bold text-teal-950">Execution Duration</td>
                    <td className="py-3.5 px-4">{orig?.training_time_seconds}s</td>
                    <td className="py-3.5 px-4 bg-teal-100/50">{ret?.retraining_time_seconds ?? 'N/A'}s</td>
                    <td className="py-3.5 px-4 bg-teal-200/40 text-teal-900 font-bold">{unl?.unlearning_time_seconds}s ({speedup || 'N/A'}x speedup)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Accuracy Comparison Chart */}
            <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
              <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2 font-serif">
                <BarChart3 className="h-4 w-4 text-teal-800" />
                <span>Partition Accuracy Breakdown</span>
              </h3>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={partitionChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E8EFEA" />
                    <XAxis dataKey="partition" stroke="#155B58" fontSize={11} />
                    <YAxis stroke="#155B58" fontSize={11} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#073D3C',
                        borderColor: '#0B4B49',
                        borderRadius: '0.75rem',
                        color: '#E5F5F1',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Bar dataKey="Original" fill="#72918B" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="Retrained" fill="#3E8F89" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="Unlearned" fill="#073D3C" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* MIA ROC Curve */}
            <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2 font-serif">
                  <ShieldAlert className="h-4 w-4 text-teal-800" />
                  <span>Membership Inference ROC Curve</span>
                </h3>
                <span className="text-xs text-teal-950 font-mono font-bold bg-teal-100 px-3 py-1 rounded-md border border-teal-300">
                  AUC = {mia?.unlearned?.roc_auc} (Adv: {mia?.unlearned?.attack_advantage})
                </span>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={rocPoints} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E8EFEA" />
                    <XAxis dataKey="fpr" stroke="#155B58" fontSize={11} domain={[0, 1]} label={{ value: 'False Positive Rate', position: 'insideBottomRight', offset: -5 }} />
                    <YAxis stroke="#155B58" fontSize={11} domain={[0, 1]} label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#073D3C',
                        borderColor: '#0B4B49',
                        borderRadius: '0.75rem',
                        color: '#E5F5F1',
                        fontSize: '12px',
                      }}
                    />
                    <Line type="monotone" dataKey="tpr" name="Unlearned MIA ROC" stroke="#0B4B49" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Behavioral Similarity Card */}
          {sim && (
            <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
              <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2 font-serif">
                <TrendingUp className="h-4 w-4 text-teal-800" />
                <span>Behavioral Similarity: Unlearned vs Retrained Reference</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Prediction Agreement</span>
                  <span className="font-mono text-xl font-extrabold text-teal-950 mt-1 block">
                    {sim.prediction_agreement_percent}%
                  </span>
                  <span className="text-[10px] text-teal-700 font-medium">Output class match on test set</span>
                </div>
                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Mean KL Divergence</span>
                  <span className="font-mono text-xl font-extrabold text-teal-950 mt-1 block">
                    {sim.mean_kl_divergence}
                  </span>
                  <span className="text-[10px] text-teal-700 font-medium">Distribution shift</span>
                </div>
                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Jensen-Shannon (JS)</span>
                  <span className="font-mono text-xl font-extrabold text-teal-950 mt-1 block">
                    {sim.mean_js_divergence}
                  </span>
                  <span className="text-[10px] text-teal-700 font-medium">Symmetric divergence</span>
                </div>
                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Weight L2 Distance</span>
                  <span className="font-mono text-xl font-extrabold text-teal-950 mt-1 block">
                    {sim.weight_l2_distance}
                  </span>
                  <span className="text-[10px] text-teal-700 font-medium">Parameter space distance</span>
                </div>
              </div>
              <p className="text-[11px] text-teal-800 italic bg-teal-50 p-3.5 rounded-xl border border-teal-850/15 leading-relaxed font-normal font-mono">
                Notice: {sim.caveat}
              </p>
            </div>
          )}

          {/* Class-Wise Performance Breakdown */}
          {metrics?.classes && (
            <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2 font-serif">
                  <Layers className="h-4 w-4 text-teal-800" />
                  <span>Class-Wise Performance & Generalization Metrics (Test Split)</span>
                </h3>
                <span className="text-xs text-teal-700 font-mono font-medium">Precision / Recall / F1-Score</span>
              </div>

              <div className="overflow-x-auto rounded-2xl border border-teal-850/15">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead>
                    <tr className="bg-teal-950 text-white font-bold">
                      <th className="py-3 px-4 font-sans text-[11px] uppercase">Class Category</th>
                      <th className="py-3 px-3 text-[11px] uppercase text-teal-300">Orig F1</th>
                      <th className="py-3 px-3 text-[11px] uppercase text-teal-200 bg-teal-900">Retrain F1</th>
                      <th className="py-3 px-3 text-[11px] uppercase text-teal-100 bg-teal-850">Unlearn F1</th>
                      <th className="py-3 px-3 text-[11px] uppercase text-teal-300">Unlearn Prec</th>
                      <th className="py-3 px-3 text-[11px] uppercase text-teal-300">Unlearn Rec</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-teal-850/15 bg-white text-teal-950">
                    {metrics.classes.map((clsName, idx) => {
                      const oF1 = orig?.test?.class_metrics?.[idx]?.f1 ?? '--';
                      const rF1 = ret?.test?.class_metrics?.[idx]?.f1 ?? '--';
                      const uF1 = unl?.test?.class_metrics?.[idx]?.f1 ?? '--';
                      const uP = unl?.test?.class_metrics?.[idx]?.precision ?? '--';
                      const uR = unl?.test?.class_metrics?.[idx]?.recall ?? '--';
                      return (
                        <tr key={idx} className="hover:bg-teal-50/50 transition">
                          <td className="py-2.5 px-4 font-sans font-bold text-teal-950 flex items-center space-x-2">
                            <span className="h-5 w-5 rounded-md bg-teal-100 flex items-center justify-center text-[10px] text-teal-800 font-mono">
                              {idx}
                            </span>
                            <span>{clsName}</span>
                          </td>
                          <td className="py-2.5 px-3 font-semibold">{oF1}</td>
                          <td className="py-2.5 px-3 bg-teal-100/50 font-bold text-teal-950">{rF1}</td>
                          <td className="py-2.5 px-3 bg-teal-200/40 font-bold text-teal-900">{uF1}</td>
                          <td className="py-2.5 px-3 text-teal-700">{uP}</td>
                          <td className="py-2.5 px-3 text-teal-700">{uR}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="p-12 border-2 border-dashed border-teal-850/20 rounded-3xl flex flex-col items-center justify-center text-teal-700 space-y-3 bg-teal-50/40 shadow-tactile">
          <BarChart3 className="h-10 w-10 text-teal-400" />
          <h4 className="text-base font-bold text-teal-950">No Evaluation Metrics Computed Yet</h4>
          <p className="text-xs text-teal-700/80 max-w-md text-center font-medium">
            Click "Execute Full Evaluation" above to compute the 3-model benchmark matrix, Membership Inference Attack curves, and speedup ratios.
          </p>
        </div>
      )}
    </div>
  );
}
