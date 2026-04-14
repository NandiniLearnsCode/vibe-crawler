import type { PropsWithChildren, ReactNode } from 'react';

interface PageShellProps extends PropsWithChildren {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageShell({ title, subtitle, actions, children }: PageShellProps) {
  return (
    <div className="min-h-screen bg-slate-50/70 text-slate-900">
      <div className="mx-auto w-full max-w-7xl px-6 py-8 lg:px-10">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              Matter Intelligence Layer
            </p>
            <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
            {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </header>
        {children}
      </div>
    </div>
  );
}
