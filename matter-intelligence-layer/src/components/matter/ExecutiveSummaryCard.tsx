import { Sparkles } from 'lucide-react';
import type { Matter } from '../../types/matter';

interface ExecutiveSummaryCardProps {
  matter: Matter;
}

export function ExecutiveSummaryCard({ matter }: ExecutiveSummaryCardProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">Executive Summary</h3>
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-200">
          <Sparkles className="h-3.5 w-3.5" />
          Refreshed {matter.metrics.executiveSummaryRefreshed}
        </span>
      </div>
      <p className="text-sm leading-6 text-slate-700">{matter.summary.dealStatus}</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Top risks</h4>
          <ul className="space-y-1.5 text-sm text-slate-700">
            {matter.summary.topRisks.map((risk) => (
              <li key={risk} className="rounded-md bg-slate-50 px-3 py-2">
                {risk}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Key missing items
          </h4>
          <ul className="space-y-1.5 text-sm text-slate-700">
            {matter.summary.missingItems.map((item) => (
              <li key={item} className="rounded-md bg-slate-50 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Suggested next actions
          </h4>
          <ul className="space-y-1.5 text-sm text-slate-700">
            {matter.summary.suggestedNextActions.map((action) => (
              <li key={action} className="rounded-md bg-slate-50 px-3 py-2">
                {action}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
