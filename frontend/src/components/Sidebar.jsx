import React from 'react';
import {
  Compass,
  Layers,
  PlayCircle,
  UserX,
  FlaskConical,
  BarChart3,
  History,
  Lightbulb,
  Trophy,
  Terminal,
  ShieldCheck,
} from 'lucide-react';

const NAV_ITEMS = [
  { id: 'overview', num: '01', label: 'Overview', icon: Compass, badge: null },
  { id: 'live-demo', num: 'F1', label: 'Live Unlearning Demo', icon: Trophy, badge: 'Live Lab' },
  { id: 'dataset', num: '02', label: 'Dataset Explorer', icon: Layers, badge: null },
  { id: 'training', num: '03', label: 'Model Training', icon: PlayCircle, badge: 'Stage A' },
  { id: 'forgetting', num: '04', label: 'Forgetting Request', icon: UserX, badge: 'Stage B' },
  { id: 'unlearning', num: '05', label: 'Unlearning Lab', icon: FlaskConical, badge: 'Stage C & D' },
  { id: 'evaluation', num: '06', label: 'Evaluation Metrics', icon: BarChart3, badge: 'Stage E' },
  { id: 'history', num: '07', label: 'Audit History', icon: History, badge: null },
  { id: 'insights', num: '08', label: 'Research Insights', icon: Lightbulb, badge: 'Analysis' },
];

export default function Sidebar({ currentTab, onSelectTab, activeExperiment }) {
  return (
    <aside className="w-64 bg-teal-950 border-r border-teal-850 flex flex-col justify-between shrink-0 select-none shadow-tactile z-20">
      <div className="p-4 space-y-4">
        {/* Terminal Title / System Identifier */}
        <div className="px-3 pt-1 pb-2 border-b border-teal-850/80">
          <div className="flex items-center space-x-2 text-teal-300">
            <Terminal className="h-4 w-4 text-teal-300 shrink-0" />
            <span className="font-mono text-xs font-bold tracking-wider uppercase">RESEARCH TERMINAL</span>
          </div>
          <div className="text-[10px] text-teal-400/80 font-mono mt-0.5 tracking-tight truncate">
            {activeExperiment ? `EXP: ${activeExperiment.id.slice(0, 14)}...` : 'IDLE :: READY FOR PIPELINE'}
          </div>
        </div>

        <div className="px-3 text-[10px] font-bold text-teal-300/90 uppercase tracking-widest flex items-center justify-between">
          <span>Navigation Flow</span>
          <span className="h-1.5 w-1.5 rounded-full bg-teal-300 animate-pulse"></span>
        </div>

        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-teal-800 text-teal-100 shadow-panel border-l-4 border-teal-300 font-semibold'
                    : 'text-teal-200/80 hover:bg-teal-900 hover:text-teal-100'
                }`}
              >
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div
                    className={`h-5 w-5 rounded-md flex items-center justify-center font-mono text-[9px] font-bold shrink-0 ${
                      isActive
                        ? 'bg-teal-300 text-teal-950'
                        : 'bg-teal-900/90 text-teal-400 border border-teal-800'
                    }`}
                  >
                    {item.num}
                  </div>
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-medium shrink-0 ml-1.5 ${
                      isActive
                        ? 'bg-teal-300/20 text-teal-200 border border-teal-300/30'
                        : 'bg-teal-900 text-teal-400 border border-teal-850'
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

      {/* Retro-futuristic editorial research spec footer */}
      <div className="p-3.5 m-3 rounded-xl bg-teal-900/90 border border-teal-800 text-teal-100 shadow-panel space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-teal-300" />
            <span className="font-bold text-[11px] text-teal-100 tracking-wide">Responsible AI</span>
          </div>
          <span className="text-[9px] bg-teal-800 text-teal-300 px-1.5 py-0.5 rounded font-mono border border-teal-700">
            NeurIPS '23
          </span>
        </div>
        <p className="text-[10px] text-teal-300/80 leading-normal font-normal">
          Empirical verification of selective forgetting vs retrained golden reference.
        </p>
      </div>
    </aside>
  );
}
