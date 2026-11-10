import Link from "next/link";
import { ArrowUpRight, BarChart3, CalendarClock, Coins, Mic, Users, Vote } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Upcoming } from "@/lib/types";

const ICON: Record<Upcoming["kind"], LucideIcon> = {
  results: BarChart3, earnings_call: Mic, investor_meetings: Users, agm: Vote, dividend: Coins, board_meeting: CalendarClock, corporate_action: Coins,
};

function dayLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00+05:30`);
  const today = new Date(new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }) + "T00:00:00+05:30");
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Tomorrow";
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
}

function timeLabel(t: string | null): string | null {
  if (!t) return null;
  const [h, m] = t.split(":").map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h >= 12 ? "PM" : "AM"}`;
}

/** What's coming in the next two weeks, grouped by day. Results get a "talk to X beforehand". */
export function ComingUp({ items }: { items: Upcoming[] }) {
  if (!items.length) return null;
  const days = new Map<string, Upcoming[]>();
  for (const u of items) days.set(u.date, [...(days.get(u.date) ?? []), u]);
  return (
    <ol className="card mx-4 divide-y divide-line">
      {[...days.entries()].map(([day, list]) => (
        <li key={day} className="flex gap-3 px-4 py-3">
          <span className="w-[4.5rem] shrink-0 pt-px text-xs font-semibold">{dayLabel(day)}</span>
          <ul className="min-w-0 flex-1 space-y-2">
            {list.map((u) => {
              const Icon = ICON[u.kind];
              const when = [timeLabel(u.time), u.end_date ? `to ${dayLabel(u.end_date)}` : null].filter(Boolean).join(" · ");
              return (
                <li key={u.id} className="text-[13px] leading-snug">
                  <span className="flex items-start gap-2">
                    <Icon size={14} className="mt-0.5 shrink-0 text-muted" aria-hidden />
                    <span className="min-w-0">
                      <Link href={`/company/${u.ticker}`} className="font-semibold">
                        {u.ticker}
                      </Link>{" "}
                      <span className="text-ink/80">{u.title}</span>
                      {!u.in_portfolio && <span className="ml-1 text-[11px] text-muted">(research list)</span>}
                      {when && <span className="block text-xs text-muted">{when}</span>}
                      {u.ask && (
                        <Link href={`/people/${u.ask.person_id}`} className="block text-xs font-medium text-accent">
                          Talk to {u.ask.name} beforehand
                        </Link>
                      )}
                    </span>
                    {u.url && (
                      <a href={u.url} target="_blank" rel="noopener noreferrer" aria-label="Open the notice" className="ml-auto shrink-0 pt-0.5 text-muted">
                        <ArrowUpRight size={13} />
                      </a>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </li>
      ))}
    </ol>
  );
}
