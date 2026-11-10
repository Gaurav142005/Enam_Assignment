import { ArrowUpRight, ChevronDown, ChevronRight, Minus, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { AskBox } from "@/components/AskBox";
import { BackLink } from "@/components/BackLink";
import { ColumnChart, LineChart } from "@/components/charts";
import { NetworkLine } from "@/components/NetworkLine";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { PriceChart } from "@/components/PriceChart";
import { Empty } from "@/components/States";
import { api } from "@/lib/api";
import { ago, inr, pct, tone } from "@/lib/format";
import type { CompanyPerson, ResearchJob, Fundamentals, Holding, NewsItem, ResearchReport, Series, Signal } from "@/lib/types";
import { Avatar } from "@/components/Avatar";
import Link from "next/link";

/** PULL: one company. Price → your position → who can help → fundamentals (computed) → LLM sections → news (context). */
export default async function CompanyPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const [r, news, leaders, deep] = await Promise.all([
    api<ResearchReport>(`/pull/research/${encodeURIComponent(ticker)}`),
    api<NewsItem[]>(`/news/${encodeURIComponent(ticker)}`).catch(() => [] as NewsItem[]),
    api<CompanyPerson[]>(`/network/companies/${encodeURIComponent(ticker)}/people`).catch(() => [] as CompanyPerson[]),
    api<ResearchJob>(`/pull/deep/${encodeURIComponent(ticker)}/latest`).catch(() => null),
  ]);
  const c = r.company;
  const f = r.fundamentals;

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact title={c.ticker} sub={`${f?.name ?? c.name}${c.sector !== "—" ? ` · ${c.sector}` : ""}`} />

      <Link href={`/company/${c.ticker}/research`} className="card mx-4 mb-3 flex items-start gap-3 p-4 active:opacity-70">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <Sparkles size={18} />
        </span>
        <span className="min-w-0 flex-1 text-[13px] leading-snug">
          <span className="block font-semibold">{deep?.finished_at ? "Open deep research" : "Run deep research"}</span>
          <span className="block text-muted">
            {deep?.finished_at
              ? `Generated ${ago(deep.finished_at)} ago · ${deep.result?.movements.length ?? 0} movements · ${deep.result?.sources.length ?? 0} sources`
              : "Reads transcripts, decks, the annual report and a year of filings. About a minute."}
          </span>
          {deep?.result?.summary && <span className="mt-1.5 text-ink/80 line-clamp-3">{deep.result.summary}</span>}
        </span>
        <ChevronRight size={16} className="text-muted" />
      </Link>

      <div className="mb-3">
        <AskBox ticker={c.ticker} />
      </div>

      {r.position && <PositionCard h={r.position} />}
      <div className={r.position ? "mt-3" : ""}>
        <PriceChart ticker={c.ticker} />
      </div>

      <SectionTitle>Who can help</SectionTitle>
      {r.network.length ? (
        <div className="space-y-1.5 px-4">
          {r.network.map((h) => (
            <NetworkLine key={h.person_id} hint={h} />
          ))}
        </div>
      ) : (
        <Empty>No one in your network has worked here yet.</Empty>
      )}

      {leaders.length > 0 && <Leadership people={leaders} />}

      {f ? <FundamentalsView f={f} /> : <Empty>Fundamentals unavailable for {c.ticker} right now.</Empty>}

      {news.length > 0 && <NewsList items={news} />}
    </main>
  );
}

function PositionCard({ h }: { h: Holding }) {
  return (
    <section className="card mx-4 grid grid-cols-3 gap-2 p-4 text-center" aria-label="Your position">
      <div>
        <p className="text-[11px] text-muted">Your holding</p>
        <p className="mt-0.5 text-sm font-semibold">{inr(h.value)}</p>
        <p className="num text-[11px] text-muted">{h.qty.toLocaleString("en-IN")} sh</p>
      </div>
      <div>
        <p className="text-[11px] text-muted">Unrealised</p>
        <p className={`mt-0.5 text-sm font-semibold ${tone(h.pnl)}`}>{inr(h.pnl, true)}</p>
        <p className={`num text-[11px] ${tone(h.pnl_pct)}`}>{pct(h.pnl_pct)}</p>
      </div>
      <div>
        <p className="text-[11px] text-muted">Weight</p>
        <p className="mt-0.5 text-sm font-semibold">{h.weight_pct?.toFixed(1)}%</p>
        <p className="num text-[11px] text-muted">avg ₹{h.avg_cost?.toLocaleString("en-IN")}</p>
      </div>
    </section>
  );
}

const TONE_ICON = {
  positive: { Icon: TrendingUp, cls: "text-up-ink", label: "Positive" },
  negative: { Icon: TrendingDown, cls: "text-down-ink", label: "Negative" },
  neutral: { Icon: Minus, cls: "text-muted", label: "Neutral" },
} as const;

function Signals({ items }: { items: Signal[] }) {
  if (!items.length) return null;
  return (
    <ul className="space-y-2">
      {items.map((s) => {
        const { Icon, cls, label } = TONE_ICON[s.tone];
        return (
          <li key={s.text} className="flex gap-2.5 text-[13px] leading-snug">
            <Icon size={16} className={`mt-0.5 shrink-0 ${cls}`} aria-label={label} />
            <span>{s.text}</span>
          </li>
        );
      })}
    </ul>
  );
}

/** A research section that can be folded away. Closed, it still says the one thing that matters (its lead signal). */
function Block({ title, teaser, open = false, children }: { title: string; teaser?: Signal; open?: boolean; children: React.ReactNode }) {
  const t = teaser ? TONE_ICON[teaser.tone] : null;
  return (
    <details open={open} className="card group mx-4 mt-3">
      <summary className="flex cursor-pointer items-start gap-3 p-4">
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-semibold">{title}</span>
          {teaser && t && (
            <span className="mt-1 flex gap-1.5 text-xs leading-snug text-muted group-open:hidden">
              <t.Icon size={14} className={`mt-px shrink-0 ${t.cls}`} aria-label={t.label} />
              <span className="line-clamp-2">{teaser.text}</span>
            </span>
          )}
        </span>
        <ChevronDown size={18} className="mt-0.5 shrink-0 text-muted transition-transform group-open:rotate-180" />
      </summary>
      <div className="space-y-4 px-4 pb-4">{children}</div>
    </details>
  );
}

function FundamentalsView({ f }: { f: Fundamentals }) {
  const a = (k: string) => f.annual.find((s) => s.key === k);
  const q = (k: string) => f.quarterly.find((s) => s.key === k);
  const sig = (sec: Signal["section"]) => f.signals.filter((s) => s.section === sec);
  const pick = (...xs: (Series | undefined)[]) => xs.filter((s): s is Series => !!s && s.points.some((p) => p.value !== null));
  const fyOnly = (s?: Series) => s && { ...s, points: s.points.filter((p) => p.period !== "TTM").slice(-10) };
  const last = (s?: Series, n = 6) => s && { ...s, points: s.points.filter((p) => p.period !== "TTM").slice(-n) };

  return (
    <>
      <SectionTitle right={<span className="text-xs text-muted">{f.view}</span>}>Fundamentals</SectionTitle>
      <dl className="card mx-4 grid grid-cols-3 gap-x-2 gap-y-3 p-4">
        {f.snapshot.map((m) => (
          <div key={m.label} className="min-w-0">
            <dd className="num truncate text-sm font-semibold">{m.value}</dd>
            <dt className="text-[11px] text-muted">{m.label}</dt>
          </div>
        ))}
      </dl>

      {f.about && (
        <Block title="Business" teaser={{ section: "financials", tone: "neutral", text: f.about.split(". ")[0] }}>
          <p className="text-[13px] leading-relaxed text-muted">{f.about}</p>
        </Block>
      )}

      <Block title="Trajectory" teaser={sig("trajectory")[0]} open>
        <Signals items={sig("trajectory")} />
        <ColumnChart series={pick(fyOnly(a("revenue")), fyOnly(a("pat")))} label="Annual revenue and net profit" />
        {!f.is_lender && <LineChart series={pick(fyOnly(a("margin")))} label="EBITDA margin by year" />}
        <ColumnChart series={pick(q("revenue"), q("pat"))} annual={false} label="Quarterly revenue and net profit" />
      </Block>

      <Block title="Balance sheet" teaser={sig("balance_sheet")[0]}>
        <Signals items={sig("balance_sheet")} />
        {f.is_lender ? (
          <>
            <ColumnChart series={pick(last(a("Deposits")))} label="Deposits by year" />
            <LineChart series={pick(q("Gross NPA %"), q("Net NPA %"))} annual={false} label="Gross and net NPA by quarter" />
          </>
        ) : (
          <>
            <ColumnChart series={pick(last(a("borrowings")), last(a("equity")))} label="Borrowings and net worth by year" />
            <LineChart series={pick(last(a("Working Capital Days"), 8))} label="Working-capital days by year" />
          </>
        )}
      </Block>

      {!f.is_lender && (
        <Block title="Cash quality" teaser={sig("cash_quality")[0]}>
          <Signals items={sig("cash_quality")} />
          <ColumnChart series={pick(last(a("pat")), last(a("Cash from Operating Activity")))} label="Net profit and cash from operations by year" />
        </Block>
      )}

      {f.shareholding.length > 0 && (
        <Block title="Shareholding" teaser={sig("shareholding")[0]}>
          <Signals items={sig("shareholding")} />
          <LineChart series={f.shareholding} annual={false} label="Shareholding by holder type, quarterly" />
        </Block>
      )}

      <p className="mx-4 mt-2 text-[11px] text-muted">
        Computed from {f.view} statements compiled from annual reports and exchange filings ·{" "}
        <a href={f.source_url} target="_blank" rel="noopener noreferrer" className="text-accent">
          screener.in
        </a>
      </p>
    </>
  );
}

function NewsList({ items }: { items: NewsItem[] }) {
  return (
    <>
      <SectionTitle right={<span className="text-[11px] text-muted">secondary · not used in research</span>}>In the news</SectionTitle>
      <ul className="card mx-4 divide-y divide-line">
        {items.slice(0, 3).map((n) => (
          <NewsRow key={n.url} n={n} />
        ))}
        {items.length > 3 && (
          <li>
            <details className="group">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-xs font-medium text-accent">
                <span className="group-open:hidden">{Math.min(items.length, 10) - 3} more headlines</span>
                <span className="hidden group-open:inline">Show fewer</span>
                <ChevronDown size={16} className="transition-transform group-open:rotate-180" />
              </summary>
              <ul className="divide-y divide-line border-t border-line">
                {items.slice(3, 10).map((n) => (
                  <NewsRow key={n.url} n={n} />
                ))}
              </ul>
            </details>
          </li>
        )}
      </ul>
    </>
  );
}

function NewsRow({ n }: { n: NewsItem }) {
  return (
    <li>
      <a href={n.url} target="_blank" rel="noopener noreferrer" className="flex gap-3 px-4 py-3 active:bg-line/40">
        <span className="min-w-0 flex-1">
          <span className="block text-[13px] leading-snug">{n.title}</span>
          <span className="mt-0.5 block text-[11px] text-muted">
            {n.source} · {ago(n.published_at)} ago
          </span>
        </span>
        <ArrowUpRight size={14} className="mt-0.5 shrink-0 text-muted" />
      </a>
    </li>
  );
}

function LeaderRow({ p }: { p: CompanyPerson }) {
  return (
    <li>
      <Link href={p.connection ? `/people/${p.connection.person_id}` : `/people/${p.id}`} className="flex items-center gap-3 px-4 py-2.5 active:bg-line/40">
        <Avatar name={p.name} size={30} />
        <span className="min-w-0 flex-1 text-[13px] leading-snug">
          <span className="flex items-center gap-1.5 font-medium">
            <span className={p.status === "former" ? "text-muted line-through decoration-1" : ""}>{p.name}</span>
            {p.connection && <span className="rounded-full bg-accent px-1.5 py-px text-[10px] font-medium text-bg">You know them</span>}
          </span>
          <span className="block truncate text-muted">
            {p.status === "former" ? "Former · " : ""}
            {p.role}
          </span>
          {p.paths[0] && <span className="block truncate text-[11px] text-accent">via {p.paths[0].name}: {p.paths[0].reason}</span>}
        </span>
      </Link>
    </li>
  );
}

function Leadership({ people }: { people: CompanyPerson[] }) {
  const current = people.filter((p) => p.status === "current");
  const former = people.filter((p) => p.status === "former");
  const exec = current.filter((p) => p.kind === "executive");
  const board = current.filter((p) => p.kind !== "executive");
  const known = people.filter((p) => p.connection).length;
  const asOf = people.find((p) => p.as_of)?.as_of;
  return (
    <section id="leadership" className="scroll-mt-4">
      <SectionTitle right={known ? <span className="text-xs font-medium text-accent">{known} you know</span> : undefined}>Leadership</SectionTitle>
      <ul className="card mx-4 divide-y divide-line">
        {exec.slice(0, 8).map((p) => (
          <LeaderRow key={p.id} p={p} />
        ))}
        {(exec.length > 8 || board.length > 0 || former.length > 0) && (
          <li>
            <details className="group">
              <summary className="cursor-pointer px-4 py-2.5 text-xs font-medium text-accent">
                <span className="group-open:hidden">
                  Show {exec.length > 8 ? `${exec.length - 8} more executives, ` : ""}
                  {board.length} board members{former.length ? `, ${former.length} former` : ""}
                </span>
                <span className="hidden group-open:inline">Show less</span>
              </summary>
              <ul className="divide-y divide-line border-t border-line">
                {[...exec.slice(8), ...board, ...former].map((p) => (
                  <LeaderRow key={p.id} p={p} />
                ))}
              </ul>
            </details>
          </li>
        )}
      </ul>
      <p className="mx-4 mt-2 text-[11px] text-muted">
        Management from Yahoo Finance; board from the NSE corporate-governance filing{asOf ? ` (${asOf})` : ""}; changes since from exchange filings.
      </p>
    </section>
  );
}
