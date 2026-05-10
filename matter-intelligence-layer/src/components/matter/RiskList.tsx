import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Risk, Workstream } from '../../types/matter';
import { StatusBadge } from '../common/StatusBadge';

interface RiskListProps {
  matterId: string;
  risks: Risk[];
  workstreams: Workstream[];
}

export function RiskList({ matterId, risks, workstreams }: RiskListProps) {
  const sortedRisks = [...risks].sort((a, b) => severityWeight(b.severity) - severityWeight(a.severity));

  const workstreamNameById = workstreams.reduce<Record<string, string>>((acc, stream) => {
    acc[stream.id] = stream.name;
    return acc;
  }, {});

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">Top Risks</h3>
        <p className="text-xs uppercase tracking-wide text-slate-500">Ranked by severity</p>
      </div>
      <div className="space-y-3">
        {sortedRisks.map((risk) => (
          <Link
            key={risk.id}
            to={`/matters/${matterId}/risks/${risk.id}`}
            className="block rounded-lg border border-slate-200 p-3 transition hover:border-slate-300 hover:bg-slate-50"
          >
            <div className="mb-2 flex items-start justify-between gap-3">
              <p className="text-sm font-medium text-slate-900">{risk.title}</p>
              <StatusBadge label={risk.severity} />
            </div>
            <p className="text-xs text-slate-600">
              Source workstream{risk.workstreamIds.length > 1 ? 's' : ''}:{' '}
              {risk.workstreamIds.map((id) => workstreamNameById[id]).join(', ')}
            </p>
            <p className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-slate-700">
              View risk detail
              <ArrowUpRight className="h-3.5 w-3.5" />
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}

function severityWeight(severity: Risk['severity']) {
  switch (severity) {
    case 'Critical':
      return 4;
    case 'High':
      return 3;
    case 'Medium':
      return 2;
    case 'Low':
      return 1;
    default:
      return 0;
  }
}
