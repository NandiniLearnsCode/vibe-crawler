import { GraduationCap, ShieldCheck } from 'lucide-react';
import type { KnowledgeAsset, Matter } from '../../types/matter';

interface CloseMatterSummaryProps {
  matter: Matter;
  knowledgeAssets: KnowledgeAsset[];
}

export function CloseMatterSummary({ matter, knowledgeAssets }: CloseMatterSummaryProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Close & Learn</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Final AI-generated matter summary: {matter.summary.dealStatus} The matter intelligence layer captured
          reusable legal workflow patterns while maintaining client confidentiality boundaries.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h4 className="mb-3 text-base font-semibold text-slate-900">Institutional knowledge outputs</h4>
        <ul className="space-y-3">
          {knowledgeAssets.map((asset) => (
            <li key={asset.id} className="rounded-lg border border-slate-200 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{asset.category}</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{asset.title}</p>
              <p className="mt-1 text-sm text-slate-700">{asset.description}</p>
              <p className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500">
                <ShieldCheck className="h-3.5 w-3.5" />
                {asset.confidentialityBoundary}
              </p>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
        <p className="inline-flex gap-2 text-sm text-blue-900">
          <GraduationCap className="mt-0.5 h-4 w-4 shrink-0" />
          Firm-scoped learning enabled. Ethical wall boundaries prevent leakage of client-confidential facts across
          matters; only abstracted workflow and drafting patterns are retained.
        </p>
      </div>
    </section>
  );
}
