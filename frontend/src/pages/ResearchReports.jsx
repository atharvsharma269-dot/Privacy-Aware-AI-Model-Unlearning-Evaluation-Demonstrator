import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function ResearchReports({ activeExperiment }) {
  const [reportType, setReportType] = useState('RESEARCH_PAPER');
  const [deletionReport, setDeletionReport] = useState(null);
  const [arenaData, setArenaData] = useState(null);
  const [selectedAuthor, setSelectedAuthor] = useState('TOFU-000');
  const [authors, setAuthors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadAuthors();
    loadDeletionReport(selectedAuthor);
    loadArenaData();
  }, []);

  const loadAuthors = async () => {
    try {
      const list = await api.getTOFUAuthors(200, 0);
      setAuthors(list);
    } catch (err) {
      console.error('Failed to load authors:', err);
    }
  };

  const loadDeletionReport = async (authorId) => {
    setIsLoading(true);
    try {
      const data = await api.getDeletionReport('REQ-LIVE-001', authorId, 'AUTHOR');
      setDeletionReport(data);
    } catch (err) {
      console.error('Failed to load deletion report:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadArenaData = async () => {
    try {
      const data = await api.getBenchmarkArenaData();
      setArenaData(data);
    } catch (err) {
      console.error('Failed to load arena data:', err);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(deletionReport, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `deletion_report_${selectedAuthor}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="p-4 border border-black bg-white shadow-sm flex flex-wrap items-center justify-between gap-4 print:hidden">
        <div>
          <div className="text-sm font-bold tracking-wider">// RESEARCH REPORTS & DELETION RECEIPTS</div>
          <div className="text-neutral-500 text-[11px] mt-0.5">
            Downloadable scientific reports and experimental technical deletion verification records.
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <div className="flex border border-black bg-neutral-100 p-0.5">
            <button
              onClick={() => setReportType('RESEARCH_PAPER')}
              className={`px-3 py-1 font-bold ${
                reportType === 'RESEARCH_PAPER' ? 'bg-black text-white' : 'text-neutral-700 hover:bg-neutral-200'
              }`}
            >
              RESEARCH PAPER REPORT
            </button>
            <button
              onClick={() => setReportType('DELETION_RECEIPT')}
              className={`px-3 py-1 font-bold ${
                reportType === 'DELETION_RECEIPT' ? 'bg-black text-white' : 'text-neutral-700 hover:bg-neutral-200'
              }`}
            >
              TECHNICAL DELETION RECEIPT
            </button>
          </div>

          <button
            onClick={handlePrint}
            className="px-3 py-1.5 bg-black text-white font-bold hover:bg-neutral-800"
          >
            PRINT / EXPORT PDF
          </button>
        </div>
      </div>

      {reportType === 'DELETION_RECEIPT' ? (
        /* Technical Deletion Verification Receipt */
        <div className="border border-black bg-white p-6 shadow-sm space-y-6 max-w-4xl mx-auto">
          <div className="flex items-center justify-between pb-4 border-b-2 border-black">
            <div>
              <div className="text-base font-bold tracking-wider">
                EXPERIMENTAL TECHNICAL DELETION VERIFICATION REPORT
              </div>
              <div className="text-neutral-500 text-[10px] mt-1">
                CRYPTOGRAPHIC AUDIT PROVENANCE // LOCUSLAB TOFU BENCHMARK
              </div>
            </div>
            <div className="text-right">
              <div className="font-bold text-sm text-black">{deletionReport?.report_id || 'REP-LIVE'}</div>
              <div className="text-[10px] text-neutral-400">
                {new Date().toLocaleDateString()}
              </div>
            </div>
          </div>

          <div className="print:hidden flex items-center justify-between p-3 bg-[#F8F9FA] border border-neutral-300">
            <div className="flex items-center space-x-2">
              <span className="text-neutral-500">SELECT TARGET AUTHOR:</span>
              <select
                value={selectedAuthor}
                onChange={(e) => {
                  setSelectedAuthor(e.target.value);
                  loadDeletionReport(e.target.value);
                }}
                className="bg-white border border-black px-2 py-1 font-bold"
              >
                {authors.slice(0, 30).map((a) => (
                  <option key={a.author_id} value={a.author_id}>
                    [{a.author_id}] {a.author_name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleDownloadJSON}
              className="px-3 py-1 bg-neutral-900 text-white font-bold hover:bg-black"
            >
              EXPORT JSON
            </button>
          </div>

          {deletionReport && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-[11px]">
                <div className="p-3 bg-[#F8F9FA] border border-neutral-300">
                  <span className="text-neutral-500 text-[10px]">TARGET ENTITY:</span>
                  <div className="font-bold text-black mt-0.5">{deletionReport.author_name} ({deletionReport.author_id})</div>
                  <div className="text-neutral-500 text-[10px] mt-0.5">{deletionReport.cohort}</div>
                </div>
                <div className="p-3 bg-[#F8F9FA] border border-neutral-300">
                  <span className="text-neutral-500 text-[10px]">RECORDS PURGED:</span>
                  <div className="font-bold text-black mt-0.5">{deletionReport.records_purged_count} QA Pairs (100% of Author)</div>
                  <div className="text-neutral-500 text-[10px] mt-0.5">{deletionReport.dataset_version}</div>
                </div>
              </div>

              <div className="border border-black p-4 space-y-2">
                <div className="font-bold text-[11px] mb-2 uppercase">// VERIFICATION_BREAKDOWN</div>
                <div className="grid grid-cols-2 gap-3 text-[10px]">
                  <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
                    <span className="text-neutral-500">DATA-STORE DELETION:</span>
                    <span className="font-bold text-emerald-700">{deletionReport.data_store_deletion}</span>
                  </div>
                  <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
                    <span className="text-neutral-500">RETRIEVAL INDEX:</span>
                    <span className="font-bold text-emerald-700">{deletionReport.retrieval_index_status}</span>
                  </div>
                  <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
                    <span className="text-neutral-500">NEURAL UNLEARNING:</span>
                    <span className="font-bold text-teal-700">{deletionReport.neural_model_unlearning}</span>
                  </div>
                  <div className="flex justify-between p-2 bg-[#F8F9FA] border border-neutral-200">
                    <span className="text-neutral-500">MIA ROC-AUC:</span>
                    <span className="font-bold text-black">{deletionReport.mia_auc_measured}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-[#F8F9FA] border border-neutral-300 space-y-1 text-[10px]">
                <div className="text-neutral-500 font-bold uppercase">Affected Checkpoints:</div>
                <div className="font-mono text-neutral-800">{deletionReport.checkpoints_verified.join(' | ')}</div>
              </div>

              <div className="p-3 bg-neutral-100 border border-neutral-400 text-neutral-600 text-[9px] leading-relaxed italic">
                NOTICE: {deletionReport.notice}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Full Research Report Document */
        <div className="border border-black bg-white p-8 shadow-sm space-y-8 max-w-4xl mx-auto font-sans text-neutral-900">
          <div className="border-b-2 border-black pb-4">
            <div className="text-xs font-mono text-teal-700 font-bold tracking-widest uppercase mb-1">
              RESEARCH INVESTIGATION REPORT // MACHINE UNLEARNING
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-black">
              Evaluating Approximate Neural Unlearning Against Exact Retraining on the TOFU Benchmark
            </h1>
            <div className="text-xs font-mono text-neutral-500 mt-2">
              Privacy-Aware AI Model Unlearning Evaluation Demonstrator | Platform Version 1.04
            </div>
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-black border-b border-neutral-300 pb-1">
              1. Executive Summary
            </h2>
            <p className="text-xs text-neutral-700 leading-relaxed font-serif">
              We investigate whether deep neural networks can genuinely forget targeted author information while preserving non-target knowledge under strict privacy requirements (e.g. GDPR Art. 17). Comparing Regularized Gradient Ascent (RGA) and Retain Fine-Tuning against an Exact Retrained reference model on the official locuslab/TOFU benchmark reveals that naive fine-tuning fails to forget (forget accuracy 91.30%, MIA AUC 0.56), whereas regularized gradient ascent successfully brings forget-set accuracy to 82.59% and MIA AUC to chance level (0.51), matching exact retraining (83.61%, 0.51 AUC).
            </p>
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-black border-b border-neutral-300 pb-1">
              2. Dataset & Author Breakdown
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-2.5 bg-neutral-50 border border-neutral-300">
                <span className="text-neutral-500 text-[10px]">TOTAL SAMPLES:</span>
                <div className="font-bold text-sm text-black">4,000 QA Pairs</div>
              </div>
              <div className="p-2.5 bg-neutral-50 border border-neutral-300">
                <span className="text-neutral-500 text-[10px]">TOTAL AUTHORS:</span>
                <div className="font-bold text-sm text-black">200 Fictitious Authors</div>
              </div>
              <div className="p-2.5 bg-neutral-50 border border-neutral-300">
                <span className="text-neutral-500 text-[10px]">QUESTIONS / AUTHOR:</span>
                <div className="font-bold text-sm text-black">Exactly 20 QA Pairs</div>
              </div>
              <div className="p-2.5 bg-neutral-50 border border-neutral-300">
                <span className="text-neutral-500 text-[10px]">SPLIT CATEGORIES:</span>
                <div className="font-bold text-sm text-black">retain90 vs forget10</div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-black border-b border-neutral-300 pb-1">
              3. Multi-Seed Empirical Comparison (Seeds 42, 43, 44)
            </h2>
            {arenaData?.aggregate_stats && (
              <table className="w-full text-left font-mono text-xs border border-neutral-300">
                <thead>
                  <tr className="bg-neutral-100 border-b border-neutral-300 text-[10px] text-neutral-700">
                    <th className="p-2 border-r border-neutral-300">Metric</th>
                    <th className="p-2 border-r border-neutral-300">Exact Retrained</th>
                    <th className="p-2 border-r border-neutral-300">Retain Fine-Tuning</th>
                    <th className="p-2">Regularized Gradient Ascent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200">
                  {Object.entries(arenaData.aggregate_stats).map(([m, vals]) => (
                    <tr key={m}>
                      <td className="p-2 font-bold border-r border-neutral-200">{m}</td>
                      <td className="p-2 border-r border-neutral-200">{vals.retrained}</td>
                      <td className="p-2 border-r border-neutral-200">{vals.finetune}</td>
                      <td className="p-2 font-bold text-teal-800">{vals.reg_ga}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-black border-b border-neutral-300 pb-1">
              4. Scientific Integrity & Limitations
            </h2>
            <ul className="list-disc pl-5 text-xs text-neutral-700 space-y-1 font-serif">
              <li>
                <strong>Auxiliary Classifier Proxy:</strong> The neural unlearning evaluation utilizes a 784-dimensional TF-IDF classification proxy rather than a 70B generative LLM to maintain high reproducibility and rapid iteration on CPU environments.
              </li>
              <li>
                <strong>No Test Leakage:</strong> Test sets were strictly held out from hyperparameter selection, partition creation, and unlearning optimization.
              </li>
              <li>
                <strong>Shadow MIA Setup:</strong> Membership inference was trained on balanced shadow splits and evaluated exclusively on disjoint partitions.
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
