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

type Group = { key: string; kind: Upcoming["kind"]; what: string; name: string | null; items: Upcoming[]; end: string | null; time: string | null };

const KIND_LABEL: Partial<Record<Upcoming["kind"], string>> = { investor_meetings: "Investor meetings" };

/** "Analyst / investor meetings: CITIC CLSA India Forum" → what "Investor meetings", name "CLSA India Forum". */
function split(u: Upcoming): { what: string; name: string | null } {
  const [head, ...rest] = u.title.split(": ");
  const name = rest.join(": ").replace(/^CITIC\s+/i, "").trim() || null;
  return { what: KIND_LABEL[u.kind] ?? head, name };
}

/** One row per event: the same forum on the same day is one line with every company attending, not four. */
function group(list: Upcoming[]): Group[] {
  const out = new Map<string, Group>();
  for (const u of list) {
    const { what, name } = split(u);
    const key = `${u.kind}|${(name ?? what).toLowerCase()}`;
    const g = out.get(key) ?? { key, kind: u.kind, what, name, items: [], end: null, time: u.time };
    g.items.push(u);
    if (u.end_date && (!g.end || u.end_date > g.end)) g.end = u.end_date;
    if (name && (!g.name || name.length < g.name.length)) g.name = name;
    if (g.time !== u.time) g.time = null; // different slots per company: don't show one
    out.set(key, g);
  }
  // Named events first (they're the ones you'd act on), then the bigger groups.
  return [...out.values()].sort((a, b) => Number(!!b.name) - Number(!!a.name) || b.items.length - a.items.length);
}

/** What's coming in the next two weeks, grouped by day, then by event. Results get a "talk to X beforehand". */
export function ComingUp({ items }: { items: Upcoming[] }) {
  if (!items.length) return null;
  const days = new Map<string, Upcoming[]>();
  for (const u of items) days.set(u.date, [...(days.get(u.date) ?? []), u]);
  return (
    <ol className="card mx-4 divide-y divide-line overflow-hidden bg-gradient-to-b from-tint-mint/70 to-surface">
      {[...days.entries()].map(([day, list]) => (
        <li key={day} className="flex gap-3 px-4 py-3">
          <span className="w-[4.5rem] shrink-0 pt-px text-xs font-semibold">{dayLabel(day)}</span>
          <ul className="min-w-0 flex-1 space-y-2.5">
            {group(list).map((g) => {
              const Icon = ICON[g.kind];
              const when = [timeLabel(g.time), g.end ? `to ${dayLabel(g.end)}` : null].filter(Boolean).join(" · ");
              const single = g.items.length === 1 ? g.items[0] : null;
              const asks = g.items.filter((u) => u.ask);
              return (
                <li key={g.key} className="text-[14px] leading-snug">
                  <span className="flex items-start gap-2">
                    <Icon size={14} className="mt-0.5 shrink-0 text-muted" aria-hidden />
                    <span className="min-w-0">
                      <span className="block">
                        <span className="font-medium">{g.name ?? g.what}</span>
                        {g.name && <span className="text-muted"> · {g.what.toLowerCase()}</span>}
                      </span>
                      <span className="mt-0.5 block text-[13px]">
                        {g.items.map((u, i) => (
                          <span key={u.id}>
                            {i > 0 && <span className="text-muted">, </span>}
                            <Link href={`/company/${u.ticker}`} className={`font-semibold ${u.in_portfolio ? "" : "text-muted"}`}>
                              {u.ticker}
                            </Link>
                          </span>
                        ))}
                        {g.items.every((u) => !u.in_portfolio) && <span className="ml-1 text-[12px] text-muted">(research list)</span>}
                      </span>
                      {when && <span className="block text-xs text-muted">{when}</span>}
                      {asks.map((u) => (
                        <Link key={u.id} href={`/people/${u.ask!.person_id}`} className="block text-xs font-medium text-accent">
                          Talk to {u.ask!.name} beforehand{g.items.length > 1 ? ` (${u.ticker})` : ""}
                        </Link>
                      ))}
                    </span>
                    {single?.url && (
                      <a href={single.url} target="_blank" rel="noopener noreferrer" aria-label="Open the notice" className="ml-auto shrink-0 pt-0.5 text-muted">
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
