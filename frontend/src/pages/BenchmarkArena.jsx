import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function BenchmarkArena() {
  const [arenaData, setArenaData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadArenaData();
  }, []);

  const loadArenaData = async () => {
    setIsLoading(true);
    try {
      const data = await api.getBenchmarkArenaData();
      setArenaData(data);
    } catch (err) {
      console.error('Failed to load benchmark arena data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold tracking-wider">// RESEARCH BENCHMARK ARENA</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Head-to-head empirical comparison of machine unlearning algorithms evaluated under identical partition configurations.
          </div>
        </div>

        <button
          onClick={loadArenaData}
          disabled={isLoading}
          className="px-3 py-1.5 bg-black text-white font-bold hover:bg-neutral-800 disabled:opacity-50"
        >
          {isLoading ? 'REFRESHING...' : 'RELOAD BENCHMARK RUNS'}
        </button>
      </div>

      {isLoading || !arenaData ? (
        <div className="p-12 border border-black bg-white text-center">
          <div className="inline-block w-4 h-4 border-2 border-black border-t-transparent animate-spin mb-2"></div>
          <div>LOADING BENCHMARK METRICS...</div>
        </div>
      ) : (
        <>
          {/* Method Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(arenaData.methods || []).map((method) => (
              <div key={method.id} className="border border-black bg-white p-4 shadow-sm space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-black">{method.name}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 border uppercase font-bold ${
                        method.id === 'retrained'
                          ? 'border-neutral-700 bg-neutral-100 text-neutral-800'
                          : method.id === 'reg_ga'
                          ? 'border-teal-700 bg-teal-50 text-teal-800'
                          : 'border-amber-700 bg-amber-50 text-amber-800'
                      }`}
                    >
                      {method.type}
                    </span>
                  </div>

                  <p className="text-[11px] text-neutral-600 mt-2 leading-relaxed">
                    {method.description}
                  </p>
                </div>

                <div className="pt-3 border-t border-neutral-200 space-y-1.5 text-[10px]">
                  <div className="flex justify-between">
                    <span className="text-neutral-500">FORGET ACCURACY:</span>
                    <span className="font-bold text-black">{method.avg_forget_acc}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">RETAIN ACCURACY:</span>
                    <span className="font-bold text-black">{method.avg_retain_acc}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">MIA ROC-AUC:</span>
                    <span className="font-bold text-teal-700">{method.mia_roc_auc}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">EXECUTION TIME RATIO:</span>
                    <span className="font-bold text-black">{method.runtime_ratio}</span>
                  </div>
                  <div className="mt-1 text-[9px] text-neutral-500 italic">
                    Limit: {method.limitations}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Aggregate Head-to-Head Comparison Table */}
          <div className="border border-black bg-white shadow-sm overflow-hidden">
            <div className="p-3 bg-neutral-900 text-white flex items-center justify-between">
              <span className="font-bold tracking-wider">// MULTI-SEED SCIENTIFIC STUDY (SEEDS: 42, 43, 44)</span>
              <span className="text-[10px] text-acid">IDENTICAL PARTITIONS & ARCHITECTURES</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#F8F9FA] border-b border-black text-[10px] text-neutral-600 uppercase">
                    <th className="p-3 border-r border-neutral-300">Metric Identifier</th>
                    <th className="p-3 border-r border-neutral-300 font-bold text-black">
                      Exact Retrained Reference
                    </th>
                    <th className="p-3 border-r border-neutral-300 font-bold text-amber-800">
                      Retain Fine-Tuning
                    </th>
                    <th className="p-3 font-bold text-teal-800">
                      Regularized Gradient Ascent (RGA)
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {Object.entries(arenaData.aggregate_stats || {}).map(([metric, vals]) => {
                    const isMIA = metric.includes('MIA');
                    const isForgetAcc = metric.includes('Forget Accuracy');
                    return (
                      <tr key={metric} className="hover:bg-neutral-50">
                        <td className="p-3 font-bold border-r border-neutral-200 text-neutral-900">
                          {metric}
                        </td>
                        <td className="p-3 border-r border-neutral-200 font-mono text-neutral-700">
                          {vals.retrained || 'N/A'}
                        </td>
                        <td className={`p-3 border-r border-neutral-200 font-mono ${isForgetAcc ? 'text-red-600 font-bold' : 'text-neutral-700'}`}>
                          {vals.finetune || 'N/A'}
                        </td>
                        <td className={`p-3 font-mono font-bold ${isMIA || isForgetAcc ? 'text-teal-700' : 'text-neutral-900'}`}>
                          {vals.reg_ga || 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Scientific Findings & Synthesis */}
          <div className="p-4 bg-white border border-black shadow-sm space-y-3">
            <div className="font-bold text-sm tracking-wide">// SCIENTIFIC ANALYSIS & METHODOLOGICAL TAKEAWAYS</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px] leading-relaxed text-neutral-800">
              <div className="p-3 bg-[#F8F9FA] border border-neutral-300 space-y-2">
                <div className="font-bold text-red-700 uppercase text-[10px]">1. Retain Fine-Tuning Fails to Forget</div>
                <p>
                  While retain fine-tuning is computationally rapid (2.22s, 0.50x), its forget-set accuracy remains elevated at <strong>91.30% +/- 0.13%</strong>, virtually unchanged from the original model. Its MIA ROC-AUC is <strong>0.56</strong>, indicating substantial residual membership privacy leakage.
                </p>
              </div>

              <div className="p-3 bg-teal-50 border border-teal-300 space-y-2">
                <div className="font-bold text-teal-800 uppercase text-[10px]">2. RGA Successfully Reaches Retrained Baseline</div>
                <p>
                  Regularized Gradient Ascent lowers forget-set accuracy to <strong>82.59% +/- 0.57%</strong>, closely matching the exact retrained reference (<strong>83.61% +/- 1.49%</strong>). Crucially, its MIA ROC-AUC drops to chance level <strong>0.51</strong> with high retain accuracy (<strong>91.17%</strong>) preserved intact.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
