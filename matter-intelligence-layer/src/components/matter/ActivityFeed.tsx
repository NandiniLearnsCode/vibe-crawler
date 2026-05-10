import { Bot, Building2, UserCircle2, UserRoundCog } from 'lucide-react';
import type { ActivityEvent } from '../../types/matter';

interface ActivityFeedProps {
  activities: ActivityEvent[];
}

const actorIconMap = {
  'AI Agent': Bot,
  Associate: UserCircle2,
  Partner: UserRoundCog,
  Client: Building2,
} as const;

export function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-3 text-base font-semibold text-slate-900">Activity Feed</h3>
      <ul className="space-y-3">
        {activities.map((event) => {
          const Icon = actorIconMap[event.actorType];
          return (
            <li key={event.id} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-start gap-3">
                <span className="rounded-md bg-slate-100 p-2 text-slate-600">
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-800">
                    <span className="font-medium">{event.actor}</span> • {event.action}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{event.timestamp}</p>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
