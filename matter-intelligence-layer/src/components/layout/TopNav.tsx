import { Building2, BriefcaseBusiness, Users } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-200/80 hover:text-slate-900'
  }`;

export function TopNav() {
  return (
    <nav className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3 lg:px-10">
        <Link to="/matters" className="flex items-center gap-2 text-slate-900">
          <Building2 className="h-5 w-5 text-slate-700" />
          <div>
            <p className="text-sm font-semibold">Harvey</p>
            <p className="text-[11px] leading-none text-slate-500">Matter Intelligence Layer</p>
          </div>
        </Link>
        <div className="flex items-center gap-1">
          <NavLink to="/matters" className={linkClass}>
            <span className="inline-flex items-center gap-1.5">
              <BriefcaseBusiness className="h-4 w-4" />
              Matters
            </span>
          </NavLink>
          <NavLink to="/matters/matter-falcon/client-view" className={linkClass}>
            <span className="inline-flex items-center gap-1.5">
              <Users className="h-4 w-4" />
              Client-safe view
            </span>
          </NavLink>
        </div>
      </div>
    </nav>
  );
}
