import type { MatterStatus, RiskSeverity } from '../../types/matter';

type BadgeTone = MatterStatus | RiskSeverity | 'Internal only' | 'Client-safe view' | 'Blocked';

const toneClassMap: Record<BadgeTone, string> = {
  Active: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  'At Risk': 'bg-amber-50 text-amber-700 ring-amber-200',
  Closed: 'bg-slate-100 text-slate-700 ring-slate-200',
  Critical: 'bg-rose-100 text-rose-700 ring-rose-200',
  High: 'bg-rose-50 text-rose-700 ring-rose-200',
  Medium: 'bg-amber-50 text-amber-700 ring-amber-200',
  Low: 'bg-sky-50 text-sky-700 ring-sky-200',
  'Internal only': 'bg-slate-100 text-slate-700 ring-slate-200',
  'Client-safe view': 'bg-blue-50 text-blue-700 ring-blue-200',
  Blocked: 'bg-rose-50 text-rose-700 ring-rose-200',
};

interface StatusBadgeProps {
  label: BadgeTone;
}

export function StatusBadge({ label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${toneClassMap[label]}`}
    >
      {label}
    </span>
  );
}
