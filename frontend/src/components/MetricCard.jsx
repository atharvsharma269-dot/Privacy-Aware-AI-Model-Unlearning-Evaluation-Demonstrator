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
  return (
    <div className="p-5 border border-black bg-white shadow-brutal flex flex-col justify-between font-mono relative">
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] font-bold tracking-widest uppercase text-neutral-600">
            {title}
          </span>
          {badge && (
            <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 border border-black bg-neutral-100 text-black">
              {badge}
            </span>
          )}
          {Icon && (
            <div className="h-6 w-6 border border-black bg-black text-white flex items-center justify-center">
              <Icon className="h-3.5 w-3.5" />
            </div>
          )}
        </div>

        <div className="flex items-baseline space-x-1.5 my-1">
          <span className="text-3xl font-black tracking-tight text-black font-sans">
            {value !== undefined && value !== null ? value : '--'}
          </span>
          {unit && <span className="text-xs font-bold text-neutral-600">{unit}</span>}
        </div>
      </div>

      {subtitle && (
        <div className="mt-3 pt-2 border-t border-neutral-200 text-[10px] text-neutral-600 leading-tight">
          {subtitle}
        </div>
      )}
    </div>
  );
}
