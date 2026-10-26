import React, { useState, useEffect } from 'react';
import { History, Download, Eye, CheckCircle2, Clock, FileText, ArrowRight, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

export default function ExperimentHistory({ activeExperiment, onSelectExperiment, onNavigate }) {
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadExperiments();
  }, []);

  const loadExperiments = async () => {
    setLoading(true);
    try {
      const data = await api.listExperiments();
      setExperiments(data);
    } catch (err) {
      console.error('Failed to load experiments:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-teal-950 flex items-center space-x-2 font-serif">
            <History className="h-5 w-5 text-teal-800" />
            <span>Experiment History & Audit Archive</span>
          </h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Review past unlearning trials, compare parameter configurations, and export certified results for academic publication.
          </p>
        </div>
        <button
          onClick={loadExperiments}
          className="p-2.5 rounded-xl bg-teal-100/70 hover:bg-teal-200 text-teal-900 transition shadow-sm border border-teal-850/15"
          title="Refresh experiments"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-teal-800' : ''}`} />
        </button>
      </div>

      {/* Experiment Table */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4">
        {loading ? (
          <div className="h-48 flex items-center justify-center text-teal-700 text-xs space-x-2">
            <RefreshCw className="h-4 w-4 animate-spin text-teal-800" />
            <span className="font-medium font-mono">Querying experiment records...</span>
          </div>
        ) : experiments.length > 0 ? (
          <div className="overflow-x-auto rounded-2xl border border-teal-850/15">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-teal-950 text-white font-mono">
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Experiment Name</th>
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Architecture</th>
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Status</th>
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Test Utility</th>
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Speedup</th>
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px]">Created At</th>
                  <th className="py-3.5 px-4 font-bold uppercase tracking-wider text-[11px] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-teal-850/15 font-sans text-teal-950 bg-white">
                {experiments.map((exp) => {
                  const isActive = activeExperiment?.id === exp.id;
                  const m = exp.metrics;
                  return (
                    <tr
                      key={exp.id}
                      className={`hover:bg-teal-50/50 transition ${
                        isActive ? 'bg-teal-100/50' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center space-x-2">
                          {isActive && <span className="h-2 w-2 rounded-full bg-teal-700"></span>}
                          <div>
                            <div className="font-bold text-teal-950 font-serif">{exp.name}</div>
                            <div className="text-[10px] text-teal-700 font-mono">{exp.id}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-teal-900">
                        {exp.model_name.toUpperCase()}
                        <span className="text-teal-600 block text-[10px] font-medium">Seed: {exp.seed}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-3 py-1 rounded-md text-[10px] font-mono font-bold ${
                            exp.status === 'EVALUATED'
                              ? 'bg-teal-100 text-teal-950 border border-teal-300'
                              : 'bg-teal-50 text-teal-800 border border-teal-850/15'
                          }`}
                        >
                          {exp.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        {m?.unlearned_model?.test?.accuracy ? (
                          <span className="text-teal-900 font-extrabold">
                            {m.unlearned_model.test.accuracy}%
                          </span>
                        ) : (
                          '--'
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-teal-950">
                        {m?.speedup_factor ? `${m.speedup_factor}x` : '--'}
                      </td>
                      <td className="py-3.5 px-4 text-teal-700 text-[11px] font-medium font-mono">
                        {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : '--'}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => {
                              onSelectExperiment(exp);
                              onNavigate('evaluation');
                            }}
                            className="px-3 py-1 rounded-lg bg-teal-950 hover:bg-teal-900 text-teal-100 transition text-[11px] font-bold shadow-sm font-mono"
                          >
                            Open
                          </button>
                          <a
                            href={api.getExportUrl(exp.id, 'csv')}
                            download
                            className="p-1.5 rounded-lg bg-teal-100/70 hover:bg-teal-200 text-teal-900 transition border border-teal-850/15 shadow-sm"
                            title="Download CSV"
                          >
                            <Download className="h-3.5 w-3.5" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-48 flex flex-col items-center justify-center text-teal-700 text-xs space-y-2 bg-teal-50/40 rounded-2xl">
            <History className="h-8 w-8 text-teal-400" />
            <p className="font-semibold text-teal-950">No experiments recorded yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
