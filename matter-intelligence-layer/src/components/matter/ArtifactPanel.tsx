import type { Artifact } from '../../types/matter';

interface ArtifactPanelProps {
  artifacts: Artifact[];
}

export function ArtifactPanel({ artifacts }: ArtifactPanelProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">Matter Artifacts</h3>
        <p className="text-xs uppercase tracking-wide text-slate-500">Linked to matter context</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-2 py-2">Title</th>
              <th className="px-2 py-2">Type</th>
              <th className="px-2 py-2">Owner</th>
              <th className="px-2 py-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => (
              <tr key={artifact.id} className="border-b border-slate-100 last:border-0">
                <td className="px-2 py-3 text-slate-900">{artifact.title}</td>
                <td className="px-2 py-3 text-slate-700">{artifact.type}</td>
                <td className="px-2 py-3 text-slate-700">{artifact.owner}</td>
                <td className="px-2 py-3 text-slate-500">{artifact.updatedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
