import { ArrowLeft, ArrowRight, BookOpenCheck, Share2, Sparkles } from 'lucide-react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { ArtifactPanel } from '../components/matter/ArtifactPanel';
import { ActivityFeed } from '../components/matter/ActivityFeed';
import { ExecutiveSummaryCard } from '../components/matter/ExecutiveSummaryCard';
import { MatterHeader } from '../components/matter/MatterHeader';
import { MatterHealthCard } from '../components/matter/MatterHealthCard';
import { RiskList } from '../components/matter/RiskList';
import { WorkstreamCard } from '../components/matter/WorkstreamCard';
import { PageShell } from '../components/layout/PageShell';
import {
  getActivitiesForMatter,
  getArtifactsForMatter,
  getMatterById,
  getRisksForMatter,
  getWorkstreamsForMatter,
} from '../data/mockMatterData';

export function MatterOverviewPage() {
  const { matterId } = useParams<{ matterId: string }>();
  const matter = getMatterById(matterId ?? '');

  if (!matter) {
    return <Navigate to="/matters" replace />;
  }

  const workstreams = getWorkstreamsForMatter(matter.id);
  const risks = getRisksForMatter(matter.id);
  const activities = getActivitiesForMatter(matter.id);
  const artifacts = getArtifactsForMatter(matter.id);

  return (
    <PageShell
      title="Matter Overview"
      subtitle="Single source of context for deal intelligence, legal execution, and AI synthesis."
      actions={
        <>
          <Link
            to="/matters"
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to matters
          </Link>
          <Link
            to={`/matters/${matter.id}/client-view`}
            className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100"
          >
            <Share2 className="h-4 w-4" />
            Client-facing shared view
          </Link>
          <Link
            to={`/matters/${matter.id}/close-learn`}
            className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            <BookOpenCheck className="h-4 w-4" />
            Close & learn
          </Link>
        </>
      }
    >
      <div className="space-y-5">
        <MatterHeader matter={matter} />

        <div className="grid gap-5 lg:grid-cols-[2fr_1fr]">
          <ExecutiveSummaryCard matter={matter} />
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-base font-semibold text-slate-900">Matter-level synthesis signal</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              The platform continuously composes evidence from workstreams, review tables, documents, and threads
              into a single matter model. Risks are weighted by legal materiality and deal impact.
            </p>
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              <p className="inline-flex items-center gap-1.5 font-medium text-slate-900">
                <Sparkles className="h-4 w-4 text-slate-600" />
                Latest synthesized insight
              </p>
              <p className="mt-1">
                2 blockers and 3 client-dependent inputs are now the primary gating items for close-readiness.
              </p>
            </div>
          </div>
        </div>

        <MatterHealthCard matter={matter} workstreams={workstreams} />

        <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
          <RiskList matterId={matter.id} risks={risks} workstreams={workstreams} />
          <ActivityFeed activities={activities} />
        </div>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-900">Workstreams</h3>
            <p className="text-sm text-slate-500">All workstreams are linked to matter context</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workstreams.map((workstream) => (
              <WorkstreamCard key={workstream.id} matterId={matter.id} workstream={workstream} />
            ))}
          </div>
        </section>

        <ArtifactPanel artifacts={artifacts} />

        <div className="flex justify-end">
          <Link
            to={`/matters/${matter.id}/workstreams/ws-ip`}
            className="inline-flex items-center gap-1 text-sm font-medium text-slate-700 hover:text-slate-900"
          >
            Jump to IP workstream detail
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </PageShell>
  );
}
