import { ArrowLeft } from 'lucide-react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { ClientViewPanel } from '../components/client/ClientViewPanel';
import { PageShell } from '../components/layout/PageShell';
import { getClientUpdatesForMatter, getMatterById } from '../data/mockMatterData';

export function ClientSharedSpacePage() {
  const { matterId } = useParams<{ matterId: string }>();
  const matter = getMatterById(matterId ?? '');

  if (!matter) {
    return <Navigate to="/matters" replace />;
  }

  const updates = getClientUpdatesForMatter(matter.id);

  return (
    <PageShell
      title="Shared Space"
      subtitle={`${matter.name} • Client-safe view`}
      actions={
        <Link
          to={`/matters/${matter.id}`}
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          <ArrowLeft className="h-4 w-4" />
          Return to internal view
        </Link>
      }
    >
      <ClientViewPanel matter={matter} updates={updates} />
    </PageShell>
  );
}
