import { ShieldCheck, Users2 } from 'lucide-react';
import type { Matter } from '../../types/matter';
import { StatusBadge } from '../common/StatusBadge';

interface MatterHeaderProps {
  matter: Matter;
}

export function MatterHeader({ matter }: MatterHeaderProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-900">{matter.name}</h2>
          <p className="text-sm text-slate-600">
            {matter.client} • {matter.matterType} • Counterparty: {matter.counterparty}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge label={matter.status} />
          <StatusBadge label={matter.riskLevel} />
        </div>
      </div>
      <div className="mt-4 grid gap-3 text-sm text-slate-700 md:grid-cols-2 lg:grid-cols-4">
        <p>
          <span className="font-medium text-slate-900">Lead Partner:</span> {matter.leadPartner}
        </p>
        <p>
          <span className="font-medium text-slate-900">Stage:</span> {matter.stage}
        </p>
        <p className="inline-flex items-center gap-1.5">
          <ShieldCheck className="h-4 w-4 text-slate-500" />
          <span>
            <span className="font-medium text-slate-900">Permissions:</span> {matter.permissions}
          </span>
        </p>
        <p>
          <span className="font-medium text-slate-900">Last updated:</span> {matter.lastUpdated}
        </p>
      </div>
      <div className="mt-4 inline-flex items-center gap-2 text-sm text-slate-700">
        <Users2 className="h-4 w-4 text-slate-500" />
        <span className="font-medium text-slate-900">Team:</span>
        <span>{matter.teamMembers.join(', ')}</span>
      </div>
    </section>
  );
}
