import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { PageShell } from '../components/layout/PageShell';
import { StatusBadge } from '../components/common/StatusBadge';
import { matters } from '../data/mockMatterData';

export function MattersListPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [matterTypeFilter, setMatterTypeFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [partnerFilter, setPartnerFilter] = useState('All');
  const [clientFilter, setClientFilter] = useState('All');

  const filteredMatters = useMemo(
    () =>
      matters.filter((matter) => {
        const matchesSearch =
          matter.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          matter.client.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = matterTypeFilter === 'All' || matter.matterType === matterTypeFilter;
        const matchesStatus = statusFilter === 'All' || matter.status === statusFilter;
        const matchesPartner = partnerFilter === 'All' || matter.leadPartner === partnerFilter;
        const matchesClient = clientFilter === 'All' || matter.client === clientFilter;
        return matchesSearch && matchesType && matchesStatus && matchesPartner && matchesClient;
      }),
    [searchTerm, matterTypeFilter, statusFilter, partnerFilter, clientFilter],
  );

  return (
    <PageShell
      title="Matters"
      subtitle="Persistent matter context links AI activity, diligence workflows, risks, and collaboration in one intelligence layer."
    >
      <section className="mb-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 lg:grid-cols-[2fr_repeat(4,1fr)]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by matter or client"
              className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm text-slate-800 outline-none transition focus:border-slate-500"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <FilterSelect
            label="Matter type"
            value={matterTypeFilter}
            options={['All', ...new Set(matters.map((matter) => matter.matterType))]}
            onChange={setMatterTypeFilter}
          />
          <FilterSelect
            label="Status"
            value={statusFilter}
            options={['All', ...new Set(matters.map((matter) => matter.status))]}
            onChange={setStatusFilter}
          />
          <FilterSelect
            label="Partner"
            value={partnerFilter}
            options={['All', ...new Set(matters.map((matter) => matter.leadPartner))]}
            onChange={setPartnerFilter}
          />
          <FilterSelect
            label="Client"
            value={clientFilter}
            options={['All', ...new Set(matters.map((matter) => matter.client))]}
            onChange={setClientFilter}
          />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filteredMatters.map((matter) => (
          <article key={matter.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{matter.name}</h2>
                <p className="text-sm text-slate-600">{matter.client}</p>
              </div>
              <StatusBadge label={matter.status} />
            </div>

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Detail label="Matter type" value={matter.matterType} />
              <Detail label="Lead partner" value={matter.leadPartner} />
              <Detail label="Workstreams" value={`${matter.workstreamIds.length || 0}`} />
              <Detail label="Risk level" value={matter.riskLevel} />
              <Detail label="Stage" value={matter.stage} />
              <Detail label="Last AI update" value={matter.metrics.executiveSummaryRefreshed} />
            </dl>

            <p className="mt-4 text-xs text-slate-500">
              Matter context retained across agents, review tables, documents, and collaboration artifacts.
            </p>

            <Link
              to={`/matters/${matter.id}`}
              className="mt-4 inline-flex rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              Open matter
            </Link>
          </article>
        ))}
      </section>
    </PageShell>
  );
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: string[];
  onChange: (nextValue: string) => void;
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-slate-500">
      {label}
      <select
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm normal-case text-slate-700 outline-none focus:border-slate-500"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

interface DetailProps {
  label: string;
  value: string;
}

function Detail({ label, value }: DetailProps) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-slate-800">{value}</dd>
    </div>
  );
}
