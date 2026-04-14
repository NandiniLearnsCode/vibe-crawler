import type { Matter, Workstream } from '../../types/matter';

interface MatterHealthCardProps {
  matter: Matter;
  workstreams: Workstream[];
}

export function MatterHealthCard({ matter, workstreams }: MatterHealthCardProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-base font-semibold text-slate-900">Matter Health & Progress</h3>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Diligence complete" value={`${matter.metrics.diligenceCompletion}%`} />
        <Metric label="High-priority issues" value={`${matter.metrics.highPriorityIssues}`} />
        <Metric label="Outstanding requests" value={`${matter.metrics.outstandingRequests}`} />
        <Metric label="Client inputs required" value={`${matter.metrics.clientInputsNeeded}`} />
        <Metric label="Blockers" value={`${matter.metrics.blockers}`} />
      </div>
      <div className="mt-5">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Progress by workstream</h4>
        <div className="space-y-3">
          {workstreams.map((stream) => (
            <div key={stream.id}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-slate-800">{stream.name}</span>
                <span className="text-slate-600">{stream.completion}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-slate-700"
                  style={{ width: `${stream.completion}%` }}
                  aria-hidden
                />
              </div>
            </div>
          ))}
        </div>
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
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}
