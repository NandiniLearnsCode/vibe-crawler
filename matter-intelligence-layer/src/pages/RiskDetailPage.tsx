import { ArrowLeft, FileText, FolderKanban } from 'lucide-react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { PageShell } from '../components/layout/PageShell';
import { StatusBadge } from '../components/common/StatusBadge';
import { artifacts, getMatterById, risks, workstreams } from '../data/mockMatterData';

export function RiskDetailPage() {
  const { matterId, riskId } = useParams<{ matterId: string; riskId: string }>();
  const matter = getMatterById(matterId ?? '');
  const risk = risks.find((item) => item.id === riskId && item.matterId === matterId);

  if (!matter || !risk) {
    return <Navigate to="/matters" replace />;
  }

  const sourceWorkstreams = workstreams.filter((stream) => risk.workstreamIds.includes(stream.id));
  const evidenceArtifacts = artifacts.filter((artifact) => risk.evidenceArtifactIds.includes(artifact.id));

  return (
    <PageShell
      title="Risk Detail"
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
      <section className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
        <div className="space-y-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-2 flex items-start justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">{risk.title}</h2>
              <StatusBadge label={risk.severity} />
            </div>
            <div className="grid gap-2 text-sm text-slate-700 md:grid-cols-2">
              <p>
                <span className="font-medium text-slate-900">Workstream source:</span>{' '}
                {sourceWorkstreams.map((stream) => stream.name).join(', ')}
              </p>
              <p>
                <span className="font-medium text-slate-900">Affected entity:</span> {risk.affectedEntity}
              </p>
              <p className="md:col-span-2">
                <span className="font-medium text-slate-900">Why it matters:</span> {risk.whyItMatters}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">AI explanation</h3>
            <p className="text-sm leading-6 text-slate-700">{risk.aiExplanation}</p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">Recommended next step</h3>
            <p className="text-sm text-slate-700">{risk.recommendedNextStep}</p>
            <p className="mt-2 text-sm">
              <span className="font-medium text-slate-900">Client input needed:</span>{' '}
              <span className={risk.clientInputNeeded ? 'text-amber-700' : 'text-emerald-700'}>
                {risk.clientInputNeeded ? 'Yes' : 'No'}
              </span>
            </p>
          </div>
        </div>

        <aside className="space-y-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">Evidence / source documents</h3>
            <ul className="space-y-2">
              {evidenceArtifacts.map((artifact) => (
                <li key={artifact.id} className="rounded-md border border-slate-200 p-3">
                  <p className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-900">
                    <FileText className="h-4 w-4 text-slate-500" />
                    {artifact.title}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {artifact.type} • Updated {artifact.updatedAt}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-slate-900">Related workstreams</h3>
            <ul className="space-y-2">
              {sourceWorkstreams.map((stream) => (
                <li key={stream.id} className="rounded-md border border-slate-200 p-3 text-sm text-slate-700">
                  <p className="inline-flex items-center gap-1.5 font-medium text-slate-900">
                    <FolderKanban className="h-4 w-4 text-slate-500" />
                    {stream.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{stream.completion}% complete</p>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </section>
    </PageShell>
  );
}
