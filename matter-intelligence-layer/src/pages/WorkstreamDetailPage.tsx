import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { PageShell } from '../components/layout/PageShell';
import { StatusBadge } from '../components/common/StatusBadge';
import { artifacts, getMatterById, risks, workstreams } from '../data/mockMatterData';

export function WorkstreamDetailPage() {
  const { matterId, workstreamId } = useParams<{ matterId: string; workstreamId: string }>();
  const matter = getMatterById(matterId ?? '');
  const workstream = workstreams.find((item) => item.id === workstreamId && item.matterId === matterId);

  if (!matter || !workstream) {
    return <Navigate to="/matters" replace />;
  }

  const flaggedRisks = risks.filter((risk) => workstream.flaggedRiskIds.includes(risk.id));
  const linkedArtifacts = artifacts.filter((artifact) => workstream.linkedArtifactIds.includes(artifact.id));

  return (
    <PageShell
      title={`${workstream.name} Workstream`}
      subtitle={`${matter.name} • Internal only`}
      actions={
        <Link
          to={`/matters/${matter.id}`}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to matter
        </Link>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
        <section className="space-y-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{workstream.name} Summary</h2>
                <p className="text-sm text-slate-600">{workstream.summary}</p>
              </div>
              <span className="text-sm font-semibold text-slate-700">{workstream.completion}% complete</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Metric label="Owner" value={workstream.owner} />
              <Metric label="Collaborators" value={workstream.collaborators.join(', ')} />
              <Metric label="Open issues" value={`${workstream.openIssues}`} />
              <Metric label="Flagged risks" value={`${workstream.flaggedRiskIds.length}`} />
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-base font-semibold text-slate-900">Diligence checklist</h3>
            <ul className="space-y-2">
              {workstream.checklist.map((item) => (
                <li key={item.item} className="flex items-center justify-between rounded-md border border-slate-200 p-2.5">
                  <span className="text-sm text-slate-800">{item.item}</span>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      item.status === 'Blocked'
                        ? 'bg-rose-50 text-rose-700'
                        : item.status === 'Complete'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-amber-50 text-amber-700'
                    }`}
                  >
                    {item.status}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-base font-semibold text-slate-900">Open issues</h3>
            <ul className="space-y-2 text-sm text-slate-700">
              {flaggedRisks.map((risk) => (
                <li key={risk.id} className="rounded-md border border-slate-200 p-3">
                  <p className="font-medium text-slate-900">{risk.title}</p>
                  <p className="mt-1">{risk.whyItMatters}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="space-y-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">How this workstream affects the matter</h3>
            <p className="text-sm leading-6 text-slate-700">{workstream.matterImpactSynthesis}</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">Flagged risks</h3>
            <div className="space-y-2">
              {flaggedRisks.map((risk) => (
                <Link
                  key={risk.id}
                  to={`/matters/${matter.id}/risks/${risk.id}`}
                  className="block rounded-md border border-slate-200 p-3 hover:bg-slate-50"
                >
                  <div className="mb-1 flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-900">{risk.title}</p>
                    <StatusBadge label={risk.severity} />
                  </div>
                  <p className="text-xs text-slate-600">Risk severity: {risk.severity}</p>
                </Link>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">Linked documents & AI findings</h3>
            <ul className="space-y-2">
              {linkedArtifacts.map((artifact) => (
                <li key={artifact.id} className="rounded-md border border-slate-200 p-3 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">{artifact.title}</p>
                  <p className="text-xs text-slate-500">
                    {artifact.type} • Updated {artifact.updatedAt}
                  </p>
                </li>
              ))}
              {workstream.linkedAIOutputs.map((output) => (
                <li
                  key={output}
                  className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-3 text-sm text-slate-700"
                >
                  AI finding: {output}
                </li>
              ))}
            </ul>
          </div>

          <Link
            to={`/matters/${matter.id}`}
            className="inline-flex items-center gap-1 text-sm font-medium text-slate-700 hover:text-slate-900"
          >
            Return to matter dashboard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      </div>
    </PageShell>
  );
}

interface MetricProps {
  label: string;
  value: string;
}

function Metric({ label, value }: MetricProps) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-slate-800">{value}</p>
    </div>
  );
}
