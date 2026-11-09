import React from 'react';

const NAV_ITEMS = [
  { id: 'overview', num: '01', slug: 'OVERVIEW', badge: null },
  { id: 'chat', num: '02', slug: 'PRIVACY_AI_CHAT', badge: 'LIVE' },
  { id: 'dataset', num: '03', slug: 'DATASET_EXPLORER', badge: 'TOFU' },
  { id: 'forgetting', num: '04', slug: 'FORGETTING_REQ', badge: null },
  { id: 'provenance', num: '05', slug: 'PROVENANCE_GRAPH', badge: 'DAG' },
  { id: 'impact', num: '06', slug: 'IMPACT_ANALYSIS', badge: null },
  { id: 'training', num: '07', slug: 'MODEL_TRAINING', badge: 'STAGE_A' },
  { id: 'unlearning', num: '08', slug: 'UNLEARNING_LAB', badge: 'STAGE_C+D' },
  { id: 'arena', num: '09', slug: 'BENCHMARK_ARENA', badge: 'STUDY' },
  { id: 'evaluation', num: '10', slug: 'EVALUATION_METRICS', badge: '3-MODEL' },
  { id: 'redteam', num: '11', slug: 'PRIVACY_RED_TEAM', badge: 'ATTACK' },
  { id: 'history', num: '12', slug: 'EXPERIMENT_HISTORY', badge: null },
  { id: 'audit', num: '13', slug: 'AUDIT_HISTORY', badge: 'LOG' },
  { id: 'reports', num: '14', slug: 'RESEARCH_REPORTS', badge: 'EXPORT' },
  { id: 'settings', num: '15', slug: 'SETTINGS', badge: 'SYSTEM' },
];

export default function Sidebar({ currentTab, onSelectTab, activeExperiment }) {
  return (
    <aside className="w-64 bg-black text-neutral-300 border-r border-neutral-800 flex flex-col justify-between shrink-0 select-none z-20 font-mono text-xs">
      <div>
        {/* Terminal Header */}
        <div className="p-4 border-b border-neutral-800 bg-neutral-950">
          <div className="flex items-center justify-between text-neutral-400">
            <span className="text-[11px] tracking-widest text-neutral-200 font-bold">
              SYS.DIR // V1.04
            </span>
            <span className="inline-block h-2 w-2 bg-acid animate-pulse"></span>
          </div>
          <div className="mt-2 text-[10px] text-neutral-400 truncate border-l border-neutral-700 pl-2">
            {activeExperiment ? (
              <span className="text-acid">EXP: {activeExperiment.id.slice(0, 16)}</span>
            ) : (
              <span className="text-neutral-500">DAEMON: IDLE_LISTENING</span>
            )}
          </div>
        </div>

        {/* Directory Navigation */}
        <div className="px-4 pt-3 pb-1 text-[10px] tracking-widest uppercase text-neutral-300 font-bold border-b border-neutral-900">
          // ROOT_NAVIGATION
        </div>

        <nav className="p-2 space-y-0.5 overflow-y-auto max-h-[calc(100vh-140px)]">
          {NAV_ITEMS.map((item) => {
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-2.5 py-2 text-left transition-all ${
                  isActive
                    ? 'bg-neutral-900 text-acid font-bold border-l-2 border-acid'
                    : 'text-neutral-400 hover:text-neutral-100 hover:bg-neutral-950'
                }`}
              >
                <div className="flex items-center space-x-2 min-w-0">
                  <span className={isActive ? 'text-acid' : 'text-neutral-400'}>
                    {isActive ? '>' : '$'}
                  </span>
                  <span className="text-neutral-300">[{item.num}]</span>
                  <span className="truncate tracking-tight">{item.slug}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] px-1 py-0.2 border uppercase tracking-wider shrink-0 ${
                      isActive
                        ? 'border-acid text-acid bg-acid/10'
                        : 'border-neutral-800 text-neutral-400 bg-neutral-900'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Terminal Footer Info */}
      <div className="p-3 border-t border-neutral-800 bg-neutral-950 space-y-2 text-[10px]">
        <div className="flex items-center justify-between text-neutral-400">
          <span>PORT: 8000</span>
          <span className="text-acid">STATUS: OK</span>
        </div>
        <div className="text-neutral-300 leading-tight">
          RESPONSIBLE_AI // GDPR_ART_17
        </div>
      </div>
    </aside>
  );
}
