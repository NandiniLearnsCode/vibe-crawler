import { ArrowLeft } from 'lucide-react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { PageShell } from '../components/layout/PageShell';
import { CloseMatterSummary } from '../components/matter/CloseMatterSummary';
import { getKnowledgeAssetsForMatter, getMatterById } from '../data/mockMatterData';

export function CloseAndLearnPage() {
  const { matterId } = useParams<{ matterId: string }>();
  const matter = getMatterById(matterId ?? '');

  if (!matter) {
    return <Navigate to="/matters" replace />;
  }

  const knowledgeAssets = getKnowledgeAssetsForMatter(matter.id);

  return (
    <PageShell
      title="Close & Learn"
      subtitle={`${matter.name} • Institutional learning outputs`}
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
      <CloseMatterSummary matter={matter} knowledgeAssets={knowledgeAssets} />
    </PageShell>
  );
}
