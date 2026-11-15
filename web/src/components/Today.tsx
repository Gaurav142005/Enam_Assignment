import Link from "next/link";
import { inr, pct, shortDate, shortDay, tone } from "@/lib/format";
import type { PortfolioPerformance, PushItem } from "@/lib/types";

/** The headline fact of an item, in plain words (results → the numbers; otherwise its title). */
function fact(i: PushItem): React.ReactNode {
  const r = i.results;
  if (!r) return i.title;
  const rev = r.rows.find((x) => x.metric === "Revenue");
  const pat = r.rows.find((x) => x.metric === "PAT");
  return (
    <>
      {r.period} results: revenue <span className={tone(rev?.yoy_pct ?? null)}>{pct(rev?.yoy_pct ?? null)}</span>, profit{" "}
      <span className={tone(pat?.yoy_pct ?? null)}>{pct(pat?.yoy_pct ?? null)}</span> on the year
    </>
  );
}

/**
 * The 10-second read: how your money moved last session against the market, who moved it, and the one or two things
 * worth your time. Everything else is below.
 */
export function Today({ perf, since, items, more }: { perf: PortfolioPerformance | null; since?: string | null; items: PushItem[]; more: number }) {
  const you = perf?.portfolio_return_pct ?? null;
  const mkt = perf?.benchmark_return_pct ?? null;
  const gap = you !== null && mkt !== null ? you - mkt : null;
  const ranked = (perf?.holdings ?? []).filter((h) => h.return_pct !== null);
  const days = perf?.days ?? 1;
  const pnl = days > 1 ? perf?.period_pnl ?? null : perf?.day_pnl ?? null;
  const from = new Date(Date.now() - days * 86400000).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
  const label = since
    ? `Since ${shortDay(since)}`
    : days > 1
      ? `Last ${days} days · since ${from}`
      : `Last session${perf?.as_of ? ` · ${shortDate(perf.as_of)}` : ""}`;
  const best = ranked[0];
  const worst = ranked.at(-1);

  return (
    <section className="card mx-4 overflow-hidden" aria-label="Today at a glance">
      <div className="bg-gradient-to-br from-tint-peach via-tint-peach/40 to-transparent">
      {perf && (
        <div className="p-4 pb-3">
          <p className="eyebrow">{label}</p>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <div>
              <p className="text-[13px] text-muted">Your portfolio</p>
              <p className={`font-display text-[34px] font-medium leading-none tracking-tight ${tone(you)}`}>{pct(you)}</p>
              {pnl !== null && <p className={`mt-1 text-[14px] font-medium ${tone(pnl)}`}>{inr(pnl, true)}</p>}
            </div>
            <div>
              <p className="text-[13px] text-muted">{perf.benchmark_name}</p>
              <p className={`font-display text-[34px] font-medium leading-none tracking-tight ${tone(mkt)}`}>{pct(mkt)}</p>
              {gap !== null && (
                <p className="mt-1 text-[14px] text-muted">
                  You {gap >= 0 ? "beat" : "trailed"} it by <span className={`font-medium ${tone(gap)}`}>{Math.abs(gap).toFixed(1)} pts</span>
                </p>
              )}
            </div>
          </div>
          {best && worst && best.ticker !== worst.ticker && (
            <p className="mt-3 text-[14px] text-muted">
              Led by{" "}
              <Link href={`/company/${best.ticker}`} className="font-semibold text-ink">
                {best.ticker}
              </Link>{" "}
              <span className={tone(best.return_pct)}>{pct(best.return_pct)}</span>; held back by{" "}
              <Link href={`/company/${worst.ticker}`} className="font-semibold text-ink">
                {worst.ticker}
              </Link>{" "}
              <span className={tone(worst.return_pct)}>{pct(worst.return_pct)}</span>.
            </p>
          )}
        </div>
      )}

      </div>
      {items.length > 0 && (
        <ol className="divide-y divide-line border-t border-line">
          {items.map((i) => (
            <li key={i.id}>
              <a href={`#card-${i.id}`} className="block px-4 py-3 active:bg-line/40">
                <p className="text-[12px] font-semibold uppercase tracking-wide text-muted">
                  {i.company_name}
                  {i.is_new && <span className="ml-2 rounded-full bg-accent px-1.5 py-px text-[10px] text-bg">New</span>}
                </p>
                <p className="mt-0.5 text-[16px] font-semibold leading-snug">{fact(i)}</p>
                {i.thesis?.stance === "challenges" && <p className="mt-0.5 text-[13px] font-medium text-down-ink">Challenges your thesis</p>}
              </a>
            </li>
          ))}
        </ol>
      )}
      {more > 0 && <p className="border-t border-line px-4 py-2.5 text-[13px] text-muted">{more} more below</p>}
    </section>
  );
}
