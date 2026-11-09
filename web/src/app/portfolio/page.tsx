import Link from "next/link";
import { Suspense } from "react";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { SegmentedParam } from "@/components/Segmented";
import { Sparkline } from "@/components/Sparkline";
import { api } from "@/lib/api";
import { pct, rupees, shortDate, tone } from "@/lib/format";
import type { Holding, PerfPeriod, PortfolioPerformance } from "@/lib/types";

const PERIODS: PerfPeriod[] = ["1D", "1W", "1M", "3M", "6M", "1Y"];
const PERIOD_NAME: Record<PerfPeriod, string> = { "1D": "today", "1W": "this week", "1M": "past month", "3M": "past 3 months", "6M": "past 6 months", "1Y": "past year" };

/** Portfolio: how am I doing, who's carrying it, who's dragging — always against the market. */
export default async function PortfolioPage({ searchParams }: { searchParams: Promise<{ p?: string }> }) {
  const raw = (await searchParams).p as PerfPeriod;
  const period: PerfPeriod = PERIODS.includes(raw) ? raw : "1M";
  const d = await api<PortfolioPerformance>(`/market/portfolio?period=${period}`);
  const bench = d.benchmark_return_pct;
  const rel = d.portfolio_return_pct !== null && bench !== null ? d.portfolio_return_pct - bench : null;
  const beating = d.holdings.filter((h) => h.return_pct !== null && bench !== null && h.return_pct >= bench);
  const lagging = d.holdings.filter((h) => !beating.includes(h));

  return (
    <main>
      <PageHeader title="Portfolio" sub={`${d.holdings.length} companies · equal-weighted${d.as_of ? ` · close ${shortDate(d.as_of)}` : ""}`} />
      <div className="px-4">
        <Suspense>
          <SegmentedParam param="p" value={period} options={PERIODS} label="Performance period" />
        </Suspense>
      </div>

      <section className="card mx-4 mt-4 p-4" aria-label="Portfolio summary">
        <p className="text-xs text-muted">Your portfolio, {PERIOD_NAME[period]}</p>
        <p className={`mt-1 text-5xl font-semibold tracking-tight ${tone(d.portfolio_return_pct)}`}>{pct(d.portfolio_return_pct)}</p>
        <p className="mt-2 text-sm">
          {rel !== null && (
            <span className={`font-medium ${tone(rel)}`}>
              {rel >= 0 ? "+" : "−"}
              {Math.abs(rel).toFixed(1)} pts {rel >= 0 ? "ahead of" : "behind"}
            </span>
          )}{" "}
          <span className="text-muted">
            {d.benchmark_name} ({pct(bench)})
          </span>
        </p>
        <Breadth up={d.up} down={d.down} total={d.holdings.length} />
      </section>

      <SectionTitle right={<span className="text-xs text-muted">{PERIOD_NAME[period]}</span>}>Beating {d.benchmark_name} · {beating.length}</SectionTitle>
      <HoldingList items={beating} period={period} />
      <SectionTitle>Lagging {d.benchmark_name} · {lagging.length}</SectionTitle>
      <HoldingList items={lagging} period={period} />
      <p className="mx-4 mt-6 text-center text-[11px] text-muted">
        End-of-day prices from Yahoo Finance. Returns are close-to-close; the portfolio figure is an equal-weighted average.
      </p>
    </main>
  );
}

/** Thin segmented bar: one whole (the portfolio), split by direction. */
function Breadth({ up, down, total }: { up: number; down: number; total: number }) {
  const flat = Math.max(0, total - up - down);
  const parts = [
    { n: up, cls: "bg-up", name: "up" },
    { n: flat, cls: "bg-line", name: "flat" },
    { n: down, cls: "bg-down", name: "down" },
  ].filter((p) => p.n > 0);
  return (
    <div className="mt-4">
      <div className="flex h-2 gap-0.5" role="img" aria-label={`${up} up, ${down} down${flat ? `, ${flat} flat` : ""}`}>
        {parts.map((p) => (
          <span key={p.name} className={`${p.cls} rounded-full`} style={{ flexGrow: p.n }} />
        ))}
      </div>
      <p className="mt-2 flex gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-up" /> {up} up
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-down" /> {down} down
        </span>
      </p>
    </div>
  );
}

function HoldingList({ items, period }: { items: Holding[]; period: PerfPeriod }) {
  if (!items.length) return <p className="px-4 text-sm text-muted">None.</p>;
  return (
    <ul className="card mx-4 divide-y divide-line">
      {items.map((h) => (
        <li key={h.ticker}>
          <Link href={`/company/${h.ticker}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{h.ticker}</span>
              <span className="block truncate text-xs text-muted">{h.name}</span>
            </span>
            <Sparkline values={h.spark} label={`${h.ticker} price trend, ${period}`} />
            <span className="w-[5.5rem] text-right">
              <span className={`num block text-sm font-semibold ${tone(h.return_pct)}`}>{pct(h.return_pct)}</span>
              <span className="num block text-xs text-muted">{rupees(h.last_close)}</span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
