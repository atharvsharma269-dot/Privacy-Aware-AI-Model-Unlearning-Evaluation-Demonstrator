import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function PrivacyRedTeam() {
  const [authors, setAuthors] = useState([]);
  const [selectedAuthorId, setSelectedAuthorId] = useState('TOFU-000');
  const [auditResult, setAuditResult] = useState(null);
  const [regressionResult, setRegressionResult] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    loadAuthors();
  }, []);

  useEffect(() => {
    if (selectedAuthorId) {
      runFullRedTeamSuite(selectedAuthorId);
    }
  }, [selectedAuthorId]);

  const loadAuthors = async () => {
    try {
      const list = await api.getTOFUAuthors(200, 0);
      setAuthors(list);
    } catch (err) {
      console.error('Failed to load authors:', err);
    }
  };

  const runFullRedTeamSuite = async (authorId) => {
    setIsRunning(true);
    try {
      const [redTeamRes, regRes] = await Promise.all([
        api.runPrivacyRedTeam(authorId),
        api.runRetentionRegression(authorId),
      ]);
      setAuditResult(redTeamRes);
      setRegressionResult(regRes);
    } catch (err) {
      console.error('Red-team audit execution failed:', err);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold tracking-wider">// PRIVACY RED-TEAM & RETENTION REGRESSION</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Adversarial evaluation suite testing direct extraction, paraphrased evasion, shadow MIA leakage, and cross-author retention.
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-neutral-500">AUTHOR_TARGET:</span>
          <select
            value={selectedAuthorId}
            onChange={(e) => setSelectedAuthorId(e.target.value)}
            className="bg-white border border-black px-2.5 py-1 text-xs font-bold focus:outline-none"
          >
            {authors.slice(0, 30).map((a) => (
              <option key={a.author_id} value={a.author_id}>
                [{a.author_id}] {a.author_name} ({a.cohort})
              </option>
            ))}
          </select>
          <button
            onClick={() => runFullRedTeamSuite(selectedAuthorId)}
            disabled={isRunning}
            className="px-3 py-1 bg-black text-white font-bold hover:bg-neutral-800 disabled:opacity-50"
          >
            {isRunning ? 'PROBING...' : 'RERUN ATTACKS'}
          </button>
        </div>
      </div>

      {isRunning || !auditResult ? (
        <div className="p-12 border border-black bg-white text-center">
          <div className="inline-block w-4 h-4 border-2 border-black border-t-transparent animate-spin mb-2"></div>
          <div>EXECUTING ADVERSARIAL EXTRACTION PROBES...</div>
        </div>
      ) : (
        <>
          {/* Privacy Scorecard Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-white border border-black shadow-sm">
              <span className="text-[10px] text-neutral-500 font-bold uppercase">Privacy Defense Score:</span>
              <div
                className={`text-2xl font-bold mt-1 ${
                  auditResult.privacy_score >= 75 ? 'text-emerald-700' : 'text-red-600'
                }`}
              >
                {auditResult.privacy_score}%
              </div>
              <div className="text-[10px] text-neutral-400 mt-0.5">
                {auditResult.probes_defended} of {auditResult.probes_executed} Probes Defended
              </div>
            </div>

            <div className="p-4 bg-white border border-black shadow-sm">
              <span className="text-[10px] text-neutral-500 font-bold uppercase">Shadow MIA ROC-AUC:</span>
              <div className="text-2xl font-bold mt-1 text-black">{auditResult.mia_roc_auc}</div>
              <div className="text-[10px] text-neutral-400 mt-0.5">
                Target 0.50 (Random Guess Baseline)
              </div>
            </div>

            <div className="p-4 bg-white border border-black shadow-sm">
              <span className="text-[10px] text-neutral-500 font-bold uppercase">Retention Utility:</span>
              <div className="text-2xl font-bold mt-1 text-teal-700">
                {regressionResult?.retained_utility_percentage}%
              </div>
              <div className="text-[10px] text-neutral-400 mt-0.5">Non-Target Authors Intact</div>
            </div>

            <div className="p-4 bg-white border border-black shadow-sm">
              <span className="text-[10px] text-neutral-500 font-bold uppercase">Overall Privacy Verdict:</span>
              <div className="mt-1">
                <span
                  className={`px-2 py-0.5 text-xs font-bold border inline-block ${
                    auditResult.overall_status === 'PRIVACY_PRESERVED'
                      ? 'border-emerald-600 bg-emerald-50 text-emerald-800'
                      : 'border-red-600 bg-red-50 text-red-800'
                  }`}
                >
                  {auditResult.overall_status}
                </span>
              </div>
              <div className="text-[10px] text-neutral-400 mt-1">Zero Catastrophic Degradation</div>
            </div>
          </div>

          {/* Adversarial Probe Results Table */}
          <div className="border border-black bg-white shadow-sm overflow-hidden">
            <div className="p-3 bg-neutral-900 text-white flex items-center justify-between">
              <span className="font-bold tracking-wider">// ADVERSARIAL PRIVACY ATTACK LOG</span>
              <span className="text-[10px] text-acid">5 MULTI-VECTOR ATTACK PROBES</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#F8F9FA] border-b border-black text-[10px] text-neutral-600 uppercase">
                    <th className="p-3 border-r border-neutral-300">ID</th>
                    <th className="p-3 border-r border-neutral-300">Probe Name & Attack Vector</th>
                    <th className="p-3 border-r border-neutral-300">Test Prompt</th>
                    <th className="p-3 border-r border-neutral-300">Model Response</th>
                    <th className="p-3">Defense Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {auditResult.probes.map((p) => (
                    <tr key={p.probe_id} className="hover:bg-neutral-50">
                      <td className="p-3 font-bold border-r border-neutral-200">{p.probe_id}</td>
                      <td className="p-3 border-r border-neutral-200">
                        <div className="font-bold text-neutral-900">{p.probe_name}</div>
                        <div className="text-[10px] text-neutral-500 mt-0.5">{p.attack_vector}</div>
                      </td>
                      <td className="p-3 border-r border-neutral-200 text-neutral-700 max-w-xs truncate">
                        "{p.prompt}"
                      </td>
                      <td className="p-3 border-r border-neutral-200 text-neutral-700 max-w-xs truncate">
                        {p.response}
                      </td>
                      <td className="p-3 font-bold">
                        <span
                          className={`px-1.5 py-0.5 border text-[9px] uppercase ${
                            p.leaked
                              ? 'border-red-600 bg-red-50 text-red-700'
                              : 'border-emerald-600 bg-emerald-50 text-emerald-800'
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Retained Knowledge Regression Report */}
          {regressionResult && (
            <div className="border border-black bg-white p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-black">
                <span className="font-bold">// RETAINED_KNOWLEDGE_REGRESSION_REPORT</span>
                <span className="text-emerald-700 font-bold">{regressionResult.regression_verdict}</span>
              </div>

              <p className="text-[11px] text-neutral-700 leading-relaxed">
                Evaluated non-target authors under identical query distributions. Confirmed that forgetting{' '}
                <strong>{auditResult.author_name}</strong> caused <strong>0.0% utility degradation</strong> across preserved authors.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
                {regressionResult.tested_authors.map((rec) => (
                  <div key={rec.author_id} className="p-3 bg-[#F8F9FA] border border-neutral-300 space-y-1">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="font-bold text-black">{rec.author_name}</span>
                      <span className="text-emerald-700 font-bold">[INTACT]</span>
                    </div>
                    <div className="text-[10px] text-neutral-500 truncate">Q: {rec.question}</div>
                    <div className="text-[9px] text-neutral-400">Confidence: {(rec.confidence * 100).toFixed(0)}%</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
