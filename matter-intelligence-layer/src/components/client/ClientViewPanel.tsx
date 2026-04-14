import { Shield } from 'lucide-react';
import type { ClientUpdate, Matter } from '../../types/matter';
import { StatusBadge } from '../common/StatusBadge';

interface ClientViewPanelProps {
  matter: Matter;
  updates: ClientUpdate[];
}

export function ClientViewPanel({ matter, updates }: ClientViewPanelProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-blue-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Client Collaboration / Shared Space</h3>
            <p className="text-sm text-slate-600">
              Curated updates for {matter.client}. Internal legal analysis is intentionally excluded.
            </p>
          </div>
          <StatusBadge label="Client-safe view" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Matter progress" value={`${matter.metrics.diligenceCompletion}%`} />
          <Metric label="Items requiring client input" value={`${matter.metrics.clientInputsNeeded}`} />
          <Metric label="Outstanding requests" value={`${matter.metrics.outstandingRequests}`} />
          <Metric label="Current stage" value={matter.stage} />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h4 className="mb-3 text-base font-semibold text-slate-900">Curated legal team updates</h4>
        <ul className="space-y-3">
          {updates.map((update) => (
            <li key={update.id} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-900">{update.title}</p>
                  <p className="mt-1 text-sm text-slate-700">{update.detail}</p>
                </div>
                <span className="shrink-0 text-xs text-slate-500">{update.timestamp}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="inline-flex items-start gap-2 text-sm text-slate-700">
          <Shield className="mt-0.5 h-4 w-4 text-slate-500" />
          This view excludes internal notes, privileged legal reasoning, and raw AI chain-of-thought. Only
          client-safe, reviewed updates are shown.
        </p>
      </div>
    </section>
  );
}

interface MetricProps {
  label: string;
  value: string;
}

function Metric({ label, value }: MetricProps) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}
