import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function ImpactAnalysis({ onNavigate }) {
  const [scopeType, setScopeType] = useState('AUTHOR');
  const [targetId, setTargetId] = useState('TOFU-000');
  const [authors, setAuthors] = useState([]);
  const [impactData, setImpactData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionNotice, setActionNotice] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);

  useEffect(() => {
    loadAuthors();
  }, []);

  useEffect(() => {
    runImpactCalculation();
  }, [scopeType, targetId]);

  const loadAuthors = async () => {
    try {
      const list = await api.getTOFUAuthors(200, 0);
      setAuthors(list);
    } catch (err) {
      console.error('Failed to load authors:', err);
    }
  };

  const runImpactCalculation = async () => {
    setIsLoading(true);
    setActionNotice(null);
    try {
      const res = await api.computeImpactAnalysis(scopeType, targetId);
      setImpactData(res);
    } catch (err) {
      console.error('Impact calculation failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecuteUnlearning = async () => {
    if (!window.confirm(`Are you sure you want to execute destructive unlearning for scope ${scopeType}: ${targetId}?`)) {
      return;
    }
    setIsExecuting(true);
    try {
      let res;
      if (scopeType === 'AUTHOR') {
        res = await api.forgetTOFUAuthor(targetId);
      } else if (scopeType === 'QA') {
        res = await api.forgetTOFUQuestion(targetId.split('-')[0] || 'TOFU-000', targetId);
      } else if (scopeType === 'ATTRIBUTE') {
        res = await api.forgetTOFUAttribute('TOFU-000', targetId);
      } else if (scopeType === 'GROUP') {
        const cohortMatch = targetId.match(/\d+/);
        res = await api.forgetTOFUGroup(cohortMatch ? parseInt(cohortMatch[0]) : 0);
      }
      setActionNotice({
        type: 'SUCCESS',
        message: res.message || 'Unlearning successfully executed.',
      });
      runImpactCalculation();
    } catch (err) {
      setActionNotice({
        type: 'ERROR',
        message: `Execution failed: ${err.message}`,
      });
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold tracking-wider">// FORGETTING IMPACT ANALYSIS</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Pre-flight computational estimation of dataset scope, feature representations, and model checkpoints before deletion.
          </div>
        </div>

        <button
          onClick={runImpactCalculation}
          disabled={isLoading}
          className="px-3 py-1.5 bg-black text-white font-bold hover:bg-neutral-800 disabled:opacity-50"
        >
          {isLoading ? 'CALCULATING...' : 'RECALCULATE IMPACT'}
        </button>
      </div>

      {actionNotice && (
        <div
          className={`p-3 border font-bold ${
            actionNotice.type === 'SUCCESS'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-500'
              : 'bg-red-50 text-red-800 border-red-500'
          }`}
        >
          {actionNotice.message}
        </div>
      )}

      {/* Scope Selector */}
      <div className="border border-black bg-white p-5 shadow-sm space-y-4">
        <div className="pb-2 border-b border-black font-bold">// CONFIGURE PROPOSED DELETION SCOPE</div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-[10px] text-neutral-500 font-bold uppercase">Deletion Scope Type:</label>
            <div className="grid grid-cols-4 gap-1">
              {['AUTHOR', 'QA', 'ATTRIBUTE', 'GROUP'].map((type) => (
                <button
                  key={type}
                  onClick={() => {
                    setScopeType(type);
                    if (type === 'AUTHOR') setTargetId('TOFU-000');
                    if (type === 'QA') setTargetId('TOFU-QA-0000');
                    if (type === 'ATTRIBUTE') setTargetId('fact_1');
                    if (type === 'GROUP') setTargetId('Cohort 0');
                  }}
                  className={`py-1.5 text-center font-bold border ${
                    scopeType === type ? 'bg-black text-white border-black' : 'bg-neutral-100 text-neutral-800 border-neutral-300'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] text-neutral-500 font-bold uppercase">Target Identifier:</label>
            {scopeType === 'AUTHOR' && (
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full bg-white border border-black px-2.5 py-1.5 font-bold"
              >
                {authors.slice(0, 50).map((a) => (
                  <option key={a.author_id} value={a.author_id}>
                    [{a.author_id}] {a.author_name} ({a.cohort})
                  </option>
                ))}
              </select>
            )}

            {scopeType === 'QA' && (
              <input
                type="text"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                placeholder="e.g. TOFU-QA-0000"
                className="w-full bg-white border border-black px-2.5 py-1.5 font-bold"
              />
            )}

            {scopeType === 'ATTRIBUTE' && (
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full bg-white border border-black px-2.5 py-1.5 font-bold"
              >
                <option value="fact_1">fact_1 (Identity, Origin & Literary Genre)</option>
                <option value="fact_2">fact_2 (Birth Date & Earliest Life)</option>
                <option value="fact_3">fact_3 (Parents & Family Background)</option>
                <option value="fact_4">fact_4 (Writing Style & Core Themes)</option>
                <option value="fact_5">fact_5 (Notable & Best-Selling Works)</option>
                <option value="fact_6">fact_6 (Literary Awards & Recognition)</option>
              </select>
            )}

            {scopeType === 'GROUP' && (
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full bg-white border border-black px-2.5 py-1.5 font-bold"
              >
                {[...Array(10).keys()].map((i) => (
                  <option key={i} value={`Cohort ${i}`}>
                    Cohort {i} (20 Authors, 400 QA Pairs, 10.0% of Universe)
                  </option>
                ))}
                <option value="forget10">Official forget10 Split (Authors 180..199)</option>
              </select>
            )}
          </div>
        </div>
      </div>

      {/* Impact Metrics Summary Cards */}
      {impactData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-white border border-black shadow-sm">
            <span className="text-[10px] text-neutral-500 font-bold uppercase">Affected Authors:</span>
            <div className="text-xl font-bold mt-1 text-black">{impactData.affected_authors_count}</div>
            <div className="text-[10px] text-neutral-400 mt-0.5">Author entities targeted</div>
          </div>

          <div className="p-4 bg-white border border-black shadow-sm">
            <span className="text-[10px] text-neutral-500 font-bold uppercase">AFFECTED QA PAIRS:</span>
            <div className="text-xl font-bold mt-1 text-black">{impactData.affected_records_count}</div>
            <div className="text-[10px] text-neutral-400 mt-0.5">784-dim TF-IDF feature vectors</div>
          </div>

          <div className="p-4 bg-white border border-black shadow-sm">
            <span className="text-[10px] text-neutral-500 font-bold uppercase">PROJECTED UTILITY DELTA:</span>
            <div className="text-xl font-bold mt-1 text-red-600">{impactData.projected_utility_delta}</div>
            <div className="text-[10px] text-neutral-400 mt-0.5">Of 4,000 QA universe</div>
          </div>

          <div className="p-4 bg-white border border-black shadow-sm">
            <span className="text-[10px] text-neutral-500 font-bold uppercase">ESTIMATED RGA RUNTIME:</span>
            <div className="text-xl font-bold mt-1 text-teal-700">~{impactData.estimated_rga_time_seconds}s</div>
            <div className="text-[10px] text-neutral-400 mt-0.5">vs ~{impactData.estimated_retrain_time_seconds}s retrain</div>
          </div>
        </div>
      )}

      {/* Detailed Technical Impact Breakdown */}
      {impactData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-black bg-white p-5 shadow-sm space-y-3">
            <div className="pb-2 border-b border-black font-bold">// REQUIRED_OPERATIONS_CHECKLIST</div>
            <div className="space-y-2">
              {impactData.operations_checklist.map((op, idx) => (
                <div key={idx} className="p-2.5 bg-[#F8F9FA] border border-neutral-300 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-[11px] text-black">{op.name}</div>
                    <div className="text-[10px] text-neutral-500 mt-0.5">Category: {op.type}</div>
                  </div>
                  <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-600 text-[9px] font-bold">
                    PENDING_CONFIRMATION
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-black bg-white p-5 shadow-sm space-y-3 flex flex-col justify-between">
            <div>
              <div className="pb-2 border-b border-black font-bold">// TARGET_MODELS & CHECKPOINTS</div>
              <div className="mt-3 space-y-2 text-[11px]">
                <div className="p-2 bg-[#F8F9FA] border border-neutral-300">
                  <span className="text-neutral-500 text-[10px]">ORIGINAL MODEL:</span>
                  <div className="font-bold">checkpoints/exp_baseline/original.pt</div>
                </div>
                <div className="p-2 bg-[#F8F9FA] border border-neutral-300">
                  <span className="text-neutral-500 text-[10px]">APPROXIMATE UNLEARNED MODEL:</span>
                  <div className="font-bold text-teal-700">checkpoints/exp_baseline/unlearned.pt (RGA Target)</div>
                </div>
                <div className="p-2 bg-[#F8F9FA] border border-neutral-300">
                  <span className="text-neutral-500 text-[10px]">RETRAINED REFERENCE ORACLE:</span>
                  <div className="font-bold text-neutral-700">checkpoints/exp_baseline/retrained.pt</div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-black">
              <button
                onClick={handleExecuteUnlearning}
                disabled={isExecuting}
                className="w-full py-2.5 bg-red-600 text-white font-bold border border-black hover:bg-red-700 disabled:opacity-50 tracking-wider text-xs"
              >
                {isExecuting ? 'EXECUTING UNLEARNING WORKFLOW...' : 'CONFIRM & EXECUTE PERMANENT UNLEARNING >'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
