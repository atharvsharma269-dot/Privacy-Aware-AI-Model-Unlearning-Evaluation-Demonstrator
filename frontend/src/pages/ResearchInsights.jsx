import React from 'react';
import { Lightbulb, ShieldAlert, Cpu, CheckCircle2, AlertTriangle, FileText, Download } from 'lucide-react';
import { api } from '../services/api';

export default function ResearchInsights({ activeExperiment }) {
  const insights = activeExperiment?.insights;
  const metrics = activeExperiment?.metrics;

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-md bg-teal-900 text-teal-200">
              SYNTHESIS
            </span>
            <span className="text-xs text-teal-800 font-semibold uppercase tracking-wider font-mono">Automated Scientific Interpretation</span>
          </div>
          <h2 className="text-xl font-bold text-teal-950 mt-1 font-serif">Research Findings & Privacy Analysis</h2>
          <p className="text-xs text-teal-700/80 mt-1 font-medium">
            Empirically derived evaluations generated directly from computed loss tensors, MIA ROC curves, and execution timestamps.
          </p>
        </div>

        {activeExperiment && (
          <div className="flex items-center space-x-2">
            <a
              href={api.getExportUrl(activeExperiment.id, 'json')}
              download
              className="px-4 py-2.5 rounded-xl bg-teal-950 hover:bg-teal-900 text-teal-100 font-bold text-xs uppercase tracking-wider transition flex items-center space-x-2 shadow-tactile font-mono"
            >
              <Download className="h-3.5 w-3.5 text-teal-300" />
              <span>Export JSON Report</span>
            </a>
          </div>
        )}
      </div>

      {insights ? (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <div className="p-8 rounded-3xl bg-teal-950 text-teal-100 shadow-tactile space-y-3 relative overflow-hidden border border-teal-850">
            <div className="flex items-center space-x-2 text-xs font-bold text-teal-300 uppercase tracking-widest font-mono">
              <Lightbulb className="h-4 w-4" />
              <span>Executive Synthesis</span>
            </div>
            <p className="text-sm md:text-base text-teal-100 leading-relaxed font-normal">
              {insights.summary_recommendation}
            </p>
          </div>

          {/* 4 Core Pillars of Empirical Analysis */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 1. Forgetting Effectiveness */}
            <div className="p-7 rounded-3xl bg-teal-100/70 border border-teal-850/15 shadow-tactile space-y-3 border-l-4 border-l-teal-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="h-7 w-7 rounded-md bg-teal-950 flex items-center justify-center font-mono font-bold text-xs text-teal-300">
                    01
                  </div>
                  <span className="text-xs font-bold text-teal-950 uppercase tracking-wider font-mono">
                    Forgetting Effectiveness
                  </span>
                </div>
                <CheckCircle2 className="h-4 w-4 text-teal-800" />
              </div>
              <p className="text-xs text-teal-950/90 leading-relaxed font-normal">
                {insights.forgetting_effectiveness}
              </p>
            </div>

            {/* 2. Retained Utility */}
            <div className="p-7 rounded-3xl bg-teal-100/70 border border-teal-850/15 shadow-tactile space-y-3 border-l-4 border-l-teal-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="h-7 w-7 rounded-md bg-teal-950 flex items-center justify-center font-mono font-bold text-xs text-teal-300">
                    02
                  </div>
                  <span className="text-xs font-bold text-teal-950 uppercase tracking-wider font-mono">
                    Retained Utility Preservation
                  </span>
                </div>
                <CheckCircle2 className="h-4 w-4 text-teal-800" />
              </div>
              <p className="text-xs text-teal-950/90 leading-relaxed font-normal">
                {insights.retained_utility}
              </p>
            </div>

            {/* 3. Privacy & MIA */}
            <div className="p-7 rounded-3xl bg-teal-100/70 border border-teal-850/15 shadow-tactile space-y-3 border-l-4 border-l-teal-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="h-7 w-7 rounded-md bg-teal-950 flex items-center justify-center font-mono font-bold text-xs text-teal-300">
                    03
                  </div>
                  <span className="text-xs font-bold text-teal-950 uppercase tracking-wider font-mono">
                    Residual Privacy Risk (MIA)
                  </span>
                </div>
                <ShieldAlert className="h-4 w-4 text-teal-800" />
              </div>
              <p className="text-xs text-teal-950/90 leading-relaxed font-normal">
                {insights.privacy_risk_mia}
              </p>
            </div>

            {/* 4. Computational Efficiency */}
            <div className="p-7 rounded-3xl bg-teal-100/70 border border-teal-850/15 shadow-tactile space-y-3 border-l-4 border-l-teal-500">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="h-7 w-7 rounded-md bg-teal-950 flex items-center justify-center font-mono font-bold text-xs text-teal-300">
                    04
                  </div>
                  <span className="text-xs font-bold text-teal-950 uppercase tracking-wider font-mono">
                    Computational Efficiency
                  </span>
                </div>
                <Cpu className="h-4 w-4 text-teal-800" />
              </div>
              <p className="text-xs text-teal-950/90 leading-relaxed font-normal">
                {insights.computational_efficiency}
              </p>
            </div>
          </div>

          {/* Scientific Caveats & Rigorous Limitations */}
          <div className="p-7 rounded-3xl bg-white border border-teal-850/15 shadow-tactile space-y-4 border-t-4 border-t-amber-600">
            <div className="flex items-center space-x-2 text-xs font-bold text-teal-950 uppercase tracking-wider font-mono">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <span>Scientific Boundaries & Methodological Limitations</span>
            </div>
            <ul className="space-y-2.5 text-xs text-teal-900">
              {insights.scientific_limitations.map((lim, idx) => (
                <li key={idx} className="flex items-start space-x-2.5">
                  <span className="h-2 w-2 rounded-full bg-teal-700 mt-1.5 shrink-0"></span>
                  <span className="leading-relaxed font-normal">{lim}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="p-12 border-2 border-dashed border-teal-850/20 rounded-3xl flex flex-col items-center justify-center text-teal-700 space-y-3 bg-teal-50/40 shadow-tactile">
          <Lightbulb className="h-10 w-10 text-teal-400" />
          <h4 className="text-base font-bold text-teal-950">No Insights Available</h4>
          <p className="text-xs text-teal-700/80 max-w-md text-center font-medium">
            Complete the evaluation phase in the Evaluation Dashboard to synthesize evidence-based interpretations from the experimental metrics.
          </p>
        </div>
      )}
    </div>
  );
}
