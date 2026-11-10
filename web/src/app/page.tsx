import Link from "next/link";
import { Suspense } from "react";
import { ArrowUpRight, ChevronDown, SlidersHorizontal } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { BriefStatus } from "@/components/BriefStatus";
import { CATEGORY_ICON, MoveRow, PushCard } from "@/components/PushCard";
import { DemoNote, Empty } from "@/components/States";
import { SwipeDeck } from "@/components/SwipeDeck";
import { WindowPicker } from "@/components/WindowPicker";
import { api } from "@/lib/api";
import { ago, CATEGORY_LABEL, windowLabel } from "@/lib/format";
import type { Digest } from "@/lib/types";

const DECK_SIZE = 10; // a deck you can actually swipe through; everything else stays one tap away

function today(): string {
  return new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata" });
}

/** One sentence that names what matters, so the investor knows before swiping. */
function lede(d: Digest, hours: number): string {
  if (!d.attention.length) return `Nothing material in the last ${windowLabel(hours)}.`;
  const names = [...new Set(d.attention.map((i) => i.ticker))];
  const head = names.slice(0, 3).join(", ");
  const n = d.attention.filter((i) => i.priority !== "normal").length || d.attention.length;
  return `${n} that matter: ${head}${names.length > 3 ? ` and ${names.length - 3} more companies` : ""}.`;
}

/** PUSH — the Brief. What changed across my portfolio, ranked; routine collapsed; network woven in. */
export default async function BriefPage({ searchParams }: { searchParams: Promise<{ h?: string }> }) {
  const hours = Number((await searchParams).h) || 24;
  const d = await api<Digest>(`/push/digest?hours=${hours}`);
  const routineCount = d.routine.reduce((n, g) => n + g.count, 0);
  const top = d.attention.slice(0, DECK_SIZE);
  const rest = d.attention.slice(DECK_SIZE);

  return (
    <main>
      <PageHeader
        eyebrow={today()}
        title="Brief"
        sub={lede(d, hours)}
        right={
          <Link href="/settings" aria-label="Alert settings" className="mb-1 rounded-full p-2 text-muted active:bg-line/50">
            <SlidersHorizontal size={20} />
          </Link>
        }
      />
      <div className="flex flex-wrap items-center justify-between gap-2 px-4">
        <Suspense>
          <WindowPicker value={hours} />
        </Suspense>
        <BriefStatus refreshedAt={d.refreshed_at} newCount={d.new_count} live={d.live} />
      </div>

      <SectionTitle>Needs your attention</SectionTitle>
      {d.attention.length ? (
        <>
          <SwipeDeck label="Items that need your attention">
            {top.map((i) => (
              <PushCard key={i.id} item={i} />
            ))}
          </SwipeDeck>
          {rest.length > 0 && (
            <details className="card group mx-4 mt-3">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm">
                <span>
                  {rest.length} more, lower priority
                  <span className="block text-xs text-muted">Ranked below the cards above</span>
                </span>
                <ChevronDown size={16} className="text-muted transition-transform group-open:rotate-180" />
              </summary>
              <ul className="divide-y divide-line border-t border-line">
                {rest.map((i) => {
                  const Icon = i.category ? CATEGORY_ICON[i.category] : CATEGORY_ICON.unclassified;
                  return (
                    <li key={i.id} className="flex items-start gap-3 px-4 py-2.5 text-[13px] leading-snug">
                      <Icon size={15} className="mt-0.5 shrink-0 text-muted" aria-hidden />
                      <span className="min-w-0 flex-1">
                        <Link href={`/company/${i.ticker}`} className="font-semibold">
                          {i.ticker}
                        </Link>{" "}
                        <span className="text-muted">{i.results ? `${i.results.period} results` : i.title}</span>
                      </span>
                      {i.source_url ? (
                        <a href={i.source_url} target="_blank" rel="noopener noreferrer" aria-label="Open filing" className="num flex shrink-0 items-center gap-0.5 text-xs text-muted">
                          {ago(i.at)} <ArrowUpRight size={12} />
                        </a>
                      ) : (
                        <span className="num shrink-0 text-xs text-muted">{ago(i.at)}</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </details>
          )}
        </>
      ) : (
        <Empty>Nothing material in the last {windowLabel(hours)}. Widen the window to look further back.</Empty>
      )}

      {d.moves.length > 0 && (
        <>
          <SectionTitle right={<Link href="/settings" className="text-xs text-accent">Thresholds</Link>}>Unusual moves</SectionTitle>
          <div className="card mx-4 divide-y divide-line">
            {d.moves.map((m) => (
              <MoveRow key={m.id} item={m} />
            ))}
          </div>
        </>
      )}

      {d.routine.length > 0 && (
        <>
          <SectionTitle right={<span className="num text-xs text-muted">{routineCount}</span>}>Routine, collapsed</SectionTitle>
          <div className="card mx-4 divide-y divide-line">
            {d.routine.map((g) => {
              const Icon = CATEGORY_ICON[g.category];
              return (
                <details key={g.category} className="group">
                  <summary className="flex cursor-pointer items-center gap-3 px-4 py-3 text-sm">
                    <Icon size={16} className="text-muted" aria-hidden />
                    <span className="flex-1">{CATEGORY_LABEL[g.category]}</span>
                    <span className="num text-muted">{g.count}</span>
                    <ChevronDown size={16} className="text-muted transition-transform group-open:rotate-180" />
                  </summary>
                  <ul className="space-y-2.5 px-4 pb-3 pl-11">
                    {g.items.map((i) => (
                      <li key={i.id} className="flex gap-2 text-[13px]">
                        <Link href={`/company/${i.ticker}`} className="w-20 shrink-0 font-medium">
                          {i.ticker}
                        </Link>
                        <span className="min-w-0 flex-1 text-muted">{i.title}</span>
                        {i.source_url ? (
                          <a href={i.source_url} target="_blank" rel="noopener noreferrer" aria-label="Open filing" className="shrink-0 text-muted">
                            <ArrowUpRight size={14} />
                          </a>
                        ) : (
                          <span className="num shrink-0 text-xs text-muted">{ago(i.at)}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              );
            })}
          </div>
        </>
      )}
      {!d.live && <DemoNote />}
    </main>
  );
}
