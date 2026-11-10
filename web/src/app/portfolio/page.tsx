import Link from "next/link";
import { Suspense } from "react";
import { Plus } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { ResetPortfolio } from "@/components/ResetPortfolio";
import { SyncBanner } from "@/components/SyncBanner";
import { SegmentedParam } from "@/components/Segmented";
import { Sparkline } from "@/components/Sparkline";
import { api } from "@/lib/api";
import { inr, pct, rupees, shortDate, tone } from "@/lib/format";
import type { Digest, Holding, HoldingRecord, PerfPeriod, PortfolioPerformance } from "@/lib/types";

const PERIODS: PerfPeriod[] = ["1D", "1W", "1M", "3M", "6M", "1Y"];
const PERIOD_NAME: Record<PerfPeriod, string> = { "1D": "today", "1W": "this week", "1M": "past month", "3M": "past 3 months", "6M": "past 6 months", "1Y": "past year" };

/** Portfolio: how am I doing, who's carrying it, who's dragging — always against the market. */
export default async function PortfolioPage({ searchParams }: { searchParams: Promise<{ p?: string }> }) {
  const raw = (await searchParams).p as PerfPeriod;
  const period: PerfPeriod = PERIODS.includes(raw) ? raw : "1M";
  const [d, brief] = await Promise.all([
    api<PortfolioPerformance>(`/market/portfolio?period=${period}`),
    api<Digest>("/push/digest?hours=168").catch(() => null),
  ]);
  const records = await api<HoldingRecord[]>("/portfolio/holdings").catch(() => [] as HoldingRecord[]);
  const syncing = records.filter((h) => h.syncing).map((h) => h.ticker);
  // The weave: which holdings have something material in this week's Brief.
  const flagged = new Map<string, string>();
  for (const i of brief?.attention ?? []) if (i.priority !== "normal" && !flagged.has(i.ticker)) flagged.set(i.ticker, i.results ? `${i.results.period} results` : i.title);
  const bench = d.benchmark_return_pct;
  const rel = d.portfolio_return_pct !== null && bench !== null ? d.portfolio_return_pct - bench : null;
  const beating = d.holdings.filter((h) => h.return_pct !== null && bench !== null && h.return_pct >= bench);
  const lagging = d.holdings.filter((h) => !beating.includes(h));

  return (
    <main>
      <PageHeader
        title="Portfolio"
        sub={`${d.holdings.length} companies${d.as_of ? ` · close ${shortDate(d.as_of)}` : ""}`}
        right={
          <Link href="/portfolio/add" className="mb-1 flex items-center gap-1 rounded-full bg-ink px-3 py-1.5 text-xs font-medium text-bg active:opacity-80">
            <Plus size={14} /> Add
          </Link>
        }
      />
      <SyncBanner initial={syncing} />

      {d.total_value !== null && (
        <section className="card mx-4 p-4" aria-label="Portfolio value">
          <p className="text-xs text-muted">Current value</p>
          <p className="mt-1 text-5xl font-semibold tracking-tight">{inr(d.total_value)}</p>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-[11px] text-muted">Last session</p>
              <p className={`font-semibold ${tone(d.day_pnl)}`}>{inr(d.day_pnl, true)}</p>
            </div>
            <div>
              <p className="text-[11px] text-muted">Since purchase · cost {inr(d.total_cost)}</p>
              <p className={`font-semibold ${tone(d.total_pnl)}`}>
                {inr(d.total_pnl, true)}{" "}
                <span className="font-normal">({pct(d.total_pnl !== null && d.total_cost ? (d.total_pnl / d.total_cost) * 100 : null)})</span>
              </p>
            </div>
          </div>
        </section>
      )}

      <div className="mt-4 px-4">
        <Suspense>
          <SegmentedParam param="p" value={period} options={PERIODS} label="Performance period" />
        </Suspense>
      </div>

      <section className="card mx-4 mt-3 p-4" aria-label="Period performance">
        <p className="text-xs text-muted">
          Return, {PERIOD_NAME[period]} · {d.weighting === "value" ? "value-weighted" : "equal-weighted"}
        </p>
        <p className="mt-1 text-2xl font-semibold tracking-tight">
          <span className={tone(d.portfolio_return_pct)}>{pct(d.portfolio_return_pct)}</span>
          {d.period_pnl !== null && <span className={`ml-2 text-base font-medium ${tone(d.period_pnl)}`}>{inr(d.period_pnl, true)}</span>}
        </p>
        <p className="mt-1 text-sm">
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
      <HoldingList items={beating} period={period} flagged={flagged} />
      <SectionTitle>Lagging {d.benchmark_name} · {lagging.length}</SectionTitle>
      <HoldingList items={lagging} period={period} flagged={flagged} />
      <p className="mx-4 mt-6 text-center text-[11px] text-muted">
        <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-accent align-middle" /> has something material in this week&apos;s Brief.
        End-of-day prices from Yahoo Finance. Period figures hold today&apos;s quantities constant; P&amp;L is unrealised, before costs and taxes.
      </p>
      <ResetPortfolio />
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

function HoldingList({ items, period, flagged }: { items: Holding[]; period: PerfPeriod; flagged: Map<string, string> }) {
  if (!items.length) return <p className="px-4 text-sm text-muted">None.</p>;
  return (
    <ul className="card mx-4 divide-y divide-line">
      {items.map((h) => (
        <li key={h.ticker}>
          <Link href={`/company/${h.ticker}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-1.5 text-sm font-medium">
                {h.ticker}
                {flagged.has(h.ticker) && <span className="h-1.5 w-1.5 rounded-full bg-accent" role="img" aria-label={`In this week's Brief: ${flagged.get(h.ticker)}`} title={flagged.get(h.ticker)} />}
              </span>
              <span className="block truncate text-xs text-muted">
                {h.weight_pct !== null ? `${h.weight_pct.toFixed(1)}% · ${inr(h.value)}` : h.name}
              </span>
            </span>
            <Sparkline values={h.spark} label={`${h.ticker} price trend, ${period}`} />
            <span className="w-[5.75rem] text-right">
              <span className={`num block text-sm font-semibold ${tone(h.return_pct)}`}>{pct(h.return_pct)}</span>
              <span className="num block text-xs text-muted">
                {h.period_pnl !== null ? inr(h.period_pnl, true) : rupees(h.last_close)}
              </span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
