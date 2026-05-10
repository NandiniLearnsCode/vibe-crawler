import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Workstream } from '../../types/matter';

interface WorkstreamCardProps {
  matterId: string;
  workstream: Workstream;
}

export function WorkstreamCard({ matterId, workstream }: WorkstreamCardProps) {
  return (
    <Link
      to={`/matters/${matterId}/workstreams/${workstream.id}`}
      className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
    >
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-base font-semibold text-slate-900">{workstream.name}</h4>
        <span className="text-sm font-medium text-slate-700">{workstream.completion}% complete</span>
      </div>
      <p className="text-sm text-slate-600">{workstream.summary}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <Metric label="Owner" value={workstream.owner} />
        <Metric label="Open issues" value={`${workstream.openIssues}`} />
        <Metric label="Flagged risks" value={`${workstream.flaggedRiskIds.length}`} />
        <Metric label="Linked docs" value={`${workstream.linkedArtifactIds.length}`} />
      </div>
      <p className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-slate-700">
        Open workstream detail
        <ArrowRight className="h-3.5 w-3.5" />
      </p>
    </Link>
  );
}

interface MetricProps {
  label: string;
  value: string;
}

function Metric({ label, value }: MetricProps) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-sm font-medium text-slate-800">{value}</p>
    </div>
  );
}
