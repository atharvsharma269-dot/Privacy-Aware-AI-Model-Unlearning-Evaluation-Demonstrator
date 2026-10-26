import React from 'react';

export default function MetricCard({
  title,
  value,
  unit = '',
  subtitle,
  icon: Icon,
  variant = 'default',
  badge,
}) {
  const getAccentStyles = () => {
    switch (variant) {
      case 'emerald':
        return {
          iconBg: 'bg-teal-100 text-teal-800 border-teal-300/60',
          borderAccent: 'border-l-4 border-l-teal-600',
        };
      case 'amber':
        return {
          iconBg: 'bg-amber-50 text-amber-800 border-amber-300/60',
          borderAccent: 'border-l-4 border-l-amber-600',
        };
      case 'purple':
      case 'rose':
        return {
          iconBg: 'bg-rose-50 text-rose-800 border-rose-300/60',
          borderAccent: 'border-l-4 border-l-rose-600',
        };
      case 'blue':
      default:
        return {
          iconBg: 'bg-teal-50 text-teal-900 border-teal-300/60',
          borderAccent: 'border-l-4 border-l-teal-800',
        };
    }
  };

  const styles = getAccentStyles();

  return (
    <div
      className={`p-5 rounded-2xl bg-white border border-teal-800/15 shadow-tactile hover:shadow-tactile-hover transition-all duration-150 relative overflow-hidden ${styles.borderAccent}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-bold tracking-wider uppercase text-teal-800/80">{title}</span>
        {Icon && (
          <div className={`h-8 w-8 rounded-xl border flex items-center justify-center ${styles.iconBg} shadow-sm`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="flex items-baseline space-x-1.5">
        <span className="text-3xl font-extrabold font-mono tracking-tight text-teal-950">
          {value !== undefined && value !== null ? value : '--'}
        </span>
        {unit && <span className="text-xs font-semibold text-teal-700 font-mono">{unit}</span>}
        {badge && (
          <span className="ml-2 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-teal-100 text-teal-900 border border-teal-300/60">
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="text-[11px] text-teal-700/80 mt-1.5 font-medium leading-tight">{subtitle}</p>}
    </div>
  );
}
