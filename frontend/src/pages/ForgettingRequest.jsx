import React, { useState } from 'react';
import { UserX, Sliders, CheckCircle2, AlertCircle, RefreshCw, BarChart2, Hash } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { api } from '../services/api';

const CLASS_NAMES = [
  'T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
  'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot',
];

const TOFU_CLASS_NAMES = [
  'Jaime Vasquez Cohort', 'Chukwu Akabueze Cohort', 'Evelyn Desmet Cohort', 'Anara Yusifova Cohort', 'Jordan Sinclair Cohort',
  'Aurelio Beltrán Cohort', 'Elliot Benson Cohort', 'Alejandro Tomasino Cohort', 'Ingrid Christensen Cohort', 'Simon Makoni Cohort',
];

export default function ForgettingRequest({ activeExperiment, onExperimentUpdated, onNavigate }) {
  const isTofu = activeExperiment?.dataset_name === 'tofu';
  const classNames = isTofu ? TOFU_CLASS_NAMES : CLASS_NAMES;
  const [strategy, setStrategy] = useState('random');
  const [percentage, setPercentage] = useState(10);
  const [targetClass, setTargetClass] = useState(0);
  const [customSampleIds, setCustomSampleIds] = useState('');
  const [groupId, setGroupId] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const manifest = activeExperiment?.partition_manifest;
  const isPartitioned = Boolean(manifest);

  const handleSubmitForgetting = async () => {
    if (!activeExperiment?.id) {
      setError('Please initialize or train an experiment first.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const payload = {
        strategy,
        percentage: strategy === 'random' ? percentage / 100.0 : undefined,
        target_class: strategy === 'class' ? parseInt(targetClass) : undefined,
        group_id: strategy === 'group' ? parseInt(groupId) : undefined,
        sample_ids: strategy === 'sample_ids'
          ? customSampleIds.split(',').map((s) => parseInt(s.trim())).filter((n) => !isNaN(n))
          : undefined,
      };

      const updatedManifest = await api.requestForgetting(activeExperiment.id, payload);
      const fullExp = await api.getExperiment(activeExperiment.id);
      onExperimentUpdated(fullExp);
    } catch (err) {
      setError(err.message || 'Failed to partition forgetting set');
    } finally {
      setIsSubmitting(false);
    }
  };

  const comparisonData = classNames.map((cls, idx) => ({
    name: cls,
    Retain: manifest?.retain_class_distribution?.[idx] || 0,
    Forget: manifest?.forget_class_distribution?.[idx] || 0,
  }));

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-md bg-teal-900 text-teal-200">
              STAGE B
            </span>
            <span className="text-xs text-teal-800 font-semibold uppercase tracking-wider font-mono">GDPR Article 17 Protocol</span>
          </div>
          <h2 className="text-xl font-bold text-teal-950 mt-1 font-serif">Submit Deletion Request & Partition Subsets</h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Specify which training instances the model must mathematically forget. Partitions are guaranteed strictly non-overlapping.
          </p>
        </div>

        {isPartitioned && (
          <div className="flex items-center space-x-2 bg-teal-100 border border-teal-300 text-teal-950 px-4 py-2 rounded-xl text-xs font-bold shadow-sm font-mono">
            <CheckCircle2 className="h-4 w-4 text-teal-800" />
            <span>PARTITION LOCKED & AUDITED</span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 font-medium">
          <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Two Column Layout: Selection Controls & Manifest Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Deletion Strategy Mode */}
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-5 lg:col-span-1">
          <h3 className="text-sm font-bold text-teal-950 flex items-center space-x-2">
            <Sliders className="h-4 w-4 text-teal-800" />
            <span>Deletion Strategy Mode</span>
          </h3>

          <div className="space-y-2.5">
            {[
              { id: 'random', title: 'Uniform Random Deletion', desc: 'Random 1%, 5%, 10%, or 20% sample removal' },
              { id: 'class', title: 'Class-Specific Deletion', desc: 'Remove an entire semantic class (e.g. T-shirt)' },
              { id: 'group', title: 'Synthetic Group Deletion', desc: 'Simulate user/tenant deletion (groups 0-9)' },
              { id: 'sample_ids', title: 'Explicit Sample Identifiers', desc: 'Custom user-specified dataset index list' },
            ].map((opt) => (
              <label
                key={opt.id}
                className={`p-3.5 rounded-2xl border flex flex-col cursor-pointer transition-all ${
                  strategy === opt.id
                    ? 'border-teal-700 bg-teal-100/70 shadow-sm text-teal-950'
                    : 'border-teal-850/15 bg-teal-50/60 text-teal-800 hover:border-teal-400'
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <input
                    type="radio"
                    name="strategy"
                    value={opt.id}
                    checked={strategy === opt.id}
                    onChange={(e) => setStrategy(e.target.value)}
                    className="accent-teal-700"
                  />
                  <span className="font-bold text-xs text-teal-950">{opt.title}</span>
                </div>
                <span className="text-[11px] text-teal-700/80 ml-6 mt-1 font-medium">{opt.desc}</span>
              </label>
            ))}
          </div>

          {/* Dynamic Options */}
          <div className="pt-2 border-t border-teal-850/15 space-y-4 text-xs">
            {strategy === 'random' && (
              <div>
                <div className="flex justify-between mb-1.5">
                  <label className="text-teal-950 font-bold">Deletion Percentage:</label>
                  <span className="font-mono font-bold text-teal-800">{percentage}%</span>
                </div>
                <div className="flex gap-2 mb-2.5">
                  {[1, 5, 10, 20].map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPercentage(p)}
                      className={`flex-1 py-1.5 rounded-xl text-xs font-mono font-bold border transition ${
                        percentage === p
                          ? 'bg-teal-950 text-white border-teal-950 shadow-sm'
                          : 'bg-teal-100/70 text-teal-900 border-teal-300/60 hover:bg-teal-200'
                      }`}
                    >
                      {p}%
                    </button>
                  ))}
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={percentage}
                  onChange={(e) => setPercentage(parseInt(e.target.value))}
                  className="w-full accent-teal-700 cursor-pointer"
                />
              </div>
            )}

            {strategy === 'class' && (
              <div>
                <label className="text-teal-950 block mb-1.5 font-bold">Target Class to Forget:</label>
                <select
                  value={targetClass}
                  onChange={(e) => setTargetClass(parseInt(e.target.value))}
                  className="w-full bg-teal-50 border border-teal-850/20 rounded-xl px-3.5 py-2 text-teal-950 font-medium focus:ring-2 focus:ring-teal-700 focus:outline-none"
                >
                  {classNames.map((cls, idx) => (
                    <option key={idx} value={idx}>
                      Class {idx}: {cls} (Full Class)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {strategy === 'group' && (
              <div>
                <label className="text-teal-950 block mb-1.5 font-bold">Synthetic User Group ID (0-9):</label>
                <select
                  value={groupId}
                  onChange={(e) => setGroupId(parseInt(e.target.value))}
                  className="w-full bg-teal-50 border border-teal-850/20 rounded-xl px-3.5 py-2 text-teal-950 font-medium focus:ring-2 focus:ring-teal-700 focus:outline-none"
                >
                  {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((g) => (
                    <option key={g} value={g}>
                      User Cohort Group #{g} (~10% of samples)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {strategy === 'sample_ids' && (
              <div>
                <label className="text-teal-950 block mb-1.5 font-bold">Comma-Separated Indices:</label>
                <textarea
                  rows="3"
                  value={customSampleIds}
                  onChange={(e) => setCustomSampleIds(e.target.value)}
                  placeholder="e.g. 12, 45, 108, 256, 314"
                  className="w-full bg-teal-50 border border-teal-850/20 rounded-xl p-3 text-teal-950 font-mono text-xs focus:ring-2 focus:ring-teal-700 focus:outline-none"
                ></textarea>
              </div>
            )}
          </div>

          <button
            onClick={handleSubmitForgetting}
            disabled={isSubmitting}
            className="w-full py-3.5 rounded-xl bg-teal-950 hover:bg-teal-900 text-white font-bold text-xs uppercase tracking-wider transition flex items-center justify-center space-x-2 shadow-tactile disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-teal-300" />
                <span>Partitioning Datasets...</span>
              </>
            ) : (
              <>
                <UserX className="h-4 w-4 text-teal-300" />
                <span>{isPartitioned ? 'Re-Partition Forgetting Set' : 'Confirm Deletion Request'}</span>
              </>
            )}
          </button>
        </div>

        {/* Right: Partition Manifest & Class Frequency Graph */}
        <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-6 lg:col-span-2">
          {manifest ? (
            <>
              {/* Manifest Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15 border-l-4 border-l-teal-950">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Retain Set</span>
                  <span className="font-mono text-xl font-extrabold text-teal-950 mt-1 block">
                    {manifest.retain_count.toLocaleString()}
                  </span>
                  <span className="text-[10px] text-teal-700 font-medium">{(100 - manifest.forget_ratio * 100).toFixed(1)}% of pool</span>
                </div>

                <div className="p-4 rounded-2xl bg-rose-50/70 border border-rose-200 border-l-4 border-l-rose-500">
                  <span className="text-rose-700 block text-[10px] font-bold uppercase font-mono">Forget Set</span>
                  <span className="font-mono text-xl font-extrabold text-rose-700 mt-1 block">
                    {manifest.forget_count.toLocaleString()}
                  </span>
                  <span className="text-[10px] text-rose-600 font-medium">{(manifest.forget_ratio * 100).toFixed(1)}% targeted</span>
                </div>

                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15 border-l-4 border-l-teal-800">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Validation Split</span>
                  <span className="font-mono text-xl font-extrabold text-teal-950 mt-1 block">
                    {manifest.val_count.toLocaleString()}
                  </span>
                  <span className="text-[10px] text-teal-700 font-medium">Zero overlap audit</span>
                </div>

                <div className="p-4 rounded-2xl bg-teal-100/70 border border-teal-850/15 border-l-4 border-l-teal-600">
                  <span className="text-teal-700 block text-[10px] font-bold uppercase font-mono">Audit Hash</span>
                  <div className="flex items-center space-x-1 mt-1 font-mono text-teal-950 text-xs font-bold truncate">
                    <Hash className="h-3 w-3 shrink-0 text-teal-700" />
                    <span>{manifest.manifest_hash}</span>
                  </div>
                  <span className="text-[10px] text-teal-700 font-medium">SHA-256 partition</span>
                </div>
              </div>

              {/* Class Balance: Retain vs Forget Chart */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-teal-950 uppercase tracking-wider font-mono flex items-center space-x-2">
                    <BarChart2 className="h-3.5 w-3.5 text-teal-800" />
                    <span>Class Balance: Retain vs Forget</span>
                  </h4>
                  <span className="text-[11px] text-teal-700 font-mono font-medium">Sample counts</span>
                </div>
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E8EFEA" />
                      <XAxis dataKey="name" stroke="#155B58" fontSize={11} angle={-25} textAnchor="end" interval={0} />
                      <YAxis stroke="#155B58" fontSize={11} />
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
                      <Bar dataKey="Retain" fill="#073D3C" radius={[3, 3, 0, 0]} />
                      <Bar dataKey="Forget" fill="#E11D48" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Navigation Action */}
              <div className="pt-4 border-t border-teal-850/15 flex items-center justify-between">
                <span className="text-xs text-teal-700 font-medium">
                  Partition verified. Proceed to Unlearning Lab to execute unlearning and retraining.
                </span>
                <button
                  onClick={() => onNavigate('unlearning')}
                  className="px-5 py-2.5 rounded-xl bg-teal-950 hover:bg-teal-900 text-teal-100 font-bold text-xs uppercase tracking-wider transition shadow-tactile"
                >
                  Proceed to Unlearning Lab &rarr;
                </button>
              </div>
            </>
          ) : (
            <div className="h-72 border-2 border-dashed border-teal-850/20 rounded-2xl flex flex-col items-center justify-center text-teal-700 space-y-2 text-xs bg-teal-50/40">
              <UserX className="h-10 w-10 text-teal-400" />
              <p className="font-semibold text-teal-950">No deletion partition submitted yet.</p>
              <p className="text-[11px] text-teal-700/80">Select a deletion strategy on the left and submit.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
