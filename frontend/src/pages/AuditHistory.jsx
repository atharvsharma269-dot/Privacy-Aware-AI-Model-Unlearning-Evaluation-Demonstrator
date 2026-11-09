import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function AuditHistory() {
  const [timeline, setTimeline] = useState([]);
  const [filterAction, setFilterAction] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadTimeline();
  }, []);

  const loadTimeline = async () => {
    setIsLoading(true);
    try {
      const data = await api.getTOFUTimeline();
      setTimeline(data);
    } catch (err) {
      console.error('Failed to load audit timeline:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset the active knowledge store back to the pristine TOFU benchmark?')) return;
    try {
      await api.resetTOFUDemo();
      await loadTimeline();
    } catch (err) {
      alert(`Reset failed: ${err.message}`);
    }
  };

  const filteredTimeline = timeline.filter((item) => {
    if (filterAction === 'ALL') return true;
    return item.action.includes(filterAction);
  });

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm font-bold tracking-wider">// COMPREHENSIVE AUDIT LOG & TIMELINE</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Cryptographically timestamped record of all unlearning requests, knowledge purges, queries, and retention proofs.
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={loadTimeline}
            className="px-3 py-1.5 bg-neutral-100 border border-black font-bold hover:bg-neutral-200"
          >
            REFRESH
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-1.5 bg-red-600 text-white font-bold border border-black hover:bg-red-700"
          >
            RESET TOFU STORE
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-1 border border-black bg-white p-2">
        {['ALL', 'PURGE', 'QUERY', 'VERIFY', 'AUDIT'].map((f) => (
          <button
            key={f}
            onClick={() => setFilterAction(f)}
            className={`px-3 py-1 font-bold border transition-all ${
              filterAction === f
                ? 'bg-black text-white border-black'
                : 'bg-neutral-100 text-neutral-700 border-neutral-300 hover:border-black'
            }`}
          >
            {f === 'ALL' ? 'ALL EVENTS' : f}
          </button>
        ))}
        <div className="ml-auto text-neutral-500 flex items-center px-2 text-[10px]">
          TOTAL AUDIT ENTRIES: {filteredTimeline.length}
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="border border-black bg-white shadow-sm overflow-hidden">
        <div className="p-3 bg-neutral-900 text-white flex items-center justify-between">
          <span className="font-bold tracking-wider">// PROVENANCE LOG LEDGER</span>
          <span className="text-[10px] text-acid">AUDIT TRAIL // GDPR_ART_17_RECORD</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-neutral-500">
            <div className="inline-block w-4 h-4 border-2 border-black border-t-transparent animate-spin mb-2"></div>
            <div>LOADING AUDIT LEDGER...</div>
          </div>
        ) : filteredTimeline.length === 0 ? (
          <div className="p-12 text-center text-neutral-500">No audit events match the selected filter.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#F8F9FA] border-b border-black text-[10px] text-neutral-600 uppercase">
                  <th className="p-3 border-r border-neutral-300">Timestamp</th>
                  <th className="p-3 border-r border-neutral-300">Action Type</th>
                  <th className="p-3 border-r border-neutral-300">Target</th>
                  <th className="p-3 border-r border-neutral-300">Status</th>
                  <th className="p-3">Audit Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {filteredTimeline.map((item, idx) => {
                  const isPurge = item.action.includes('PURGE');
                  return (
                    <tr key={idx} className="hover:bg-neutral-50 font-mono text-[11px]">
                      <td className="p-3 border-r border-neutral-200 text-neutral-500 whitespace-nowrap">
                        {new Date(item.timestamp).toLocaleString()}
                      </td>
                      <td className="p-3 border-r border-neutral-200 font-bold text-neutral-900 whitespace-nowrap">
                        {item.action}
                      </td>
                      <td className="p-3 border-r border-neutral-200 font-bold whitespace-nowrap">
                        {item.target}
                      </td>
                      <td className="p-3 border-r border-neutral-200 whitespace-nowrap">
                        <span
                          className={`px-1.5 py-0.5 border text-[9px] font-bold ${
                            isPurge
                              ? 'border-red-600 bg-red-50 text-red-700'
                              : 'border-emerald-600 bg-emerald-50 text-emerald-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="p-3 text-neutral-700 leading-relaxed">{item.details}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
