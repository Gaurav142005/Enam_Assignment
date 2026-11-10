"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, ArrowUpRight, BarChart3, Check, ChevronDown, CircleAlert, CircleDashed, Loader2, Minus, PieChart, RefreshCw, TrendingDown,
  TrendingUp, UserRound,
} from "lucide-react";
import { BackLink } from "@/components/BackLink";
import { NetworkLine } from "@/components/NetworkLine";
import { PageHeader } from "@/components/PageHeader";
import { CATEGORY_ICON } from "@/components/PushCard";
import { api, ApiError } from "@/lib/api";
import { ago, pct, tone } from "@/lib/format";
import type { Cite, CitedPoint, DeepResearch, Movement, PromiseCheck, ResearchJob, SourceDoc, Theme } from "@/lib/types";

/** PULL: deep research. Starts a 30–60 s job that reads every recent primary document, shows progress, then the report. */
export default function ResearchPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = use(params);
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback((id: string) => {
    timer.current = setTimeout(async () => {
      try {
        const j = await api<ResearchJob>(`/pull/deep/jobs/${id}`);
        setJob(j);
        if (j.status === "queued" || j.status === "running") poll(id);
      } catch (e) {
        setError((e as Error).message);
      }
    }, 1500);
  }, []);

  const run = useCallback(
    async (refresh = false) => {
      setError(null);
      setElapsed(0);
      try {
        const res = await fetch(`/api/pull/deep/${encodeURIComponent(ticker)}?refresh=${refresh}`, { method: "POST" });
        if (!res.ok) throw new ApiError(`Couldn't start research (${res.status})`);
        const j = (await res.json()) as ResearchJob;
        setJob(j);
        if (j.status !== "done" && j.status !== "error") poll(j.id);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [ticker, poll],
  );

  useEffect(() => {
    run(false);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [run]);

  const busy = !job || job.status === "queued" || job.status === "running";
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [busy]);

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact eyebrow="Deep research" title={ticker.toUpperCase()} sub={job?.result?.name ?? "Primary sources only: filings, transcripts, decks, annual report"} />
      {error && <p className="mx-4 text-sm text-down-ink">{error}</p>}
      {job && busy && <Progress job={job} elapsed={elapsed} />}
      {job?.status === "error" && (
        <div className="card mx-4 p-4 text-sm">
          <p className="font-medium">Research didn&apos;t finish</p>
          <p className="mt-1 text-muted">{job.error}</p>
          <button onClick={() => run(true)} className="mt-3 rounded-full bg-ink px-4 py-2 text-sm text-bg">
            Try again
          </button>
        </div>
      )}
      {job?.status === "done" && job.result && <Report r={job.result} onRefresh={() => run(true)} />}
    </main>
  );
}

function Progress({ job, elapsed }: { job: ResearchJob; elapsed: number }) {
  return (
    <section className="card mx-4 p-4" aria-live="polite">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-medium">Reading everything the company has published</p>
        <span className="num text-xs text-muted">{elapsed}s</span>
      </div>
      <ol className="space-y-3">
        {job.steps.map((s) => (
          <li key={s.key} className="flex gap-3 text-[13px]">
            <span className="mt-0.5 shrink-0">
              {s.status === "done" ? (
                <Check size={16} className="text-up-ink" />
              ) : s.status === "running" ? (
                <Loader2 size={16} className="animate-spin text-accent" />
              ) : s.status === "error" ? (
                <CircleAlert size={16} className="text-down-ink" />
              ) : (
                <CircleDashed size={16} className="text-muted" />
              )}
            </span>
            <span className="min-w-0">
              <span className={s.status === "pending" ? "text-muted" : ""}>{s.label}</span>
              {s.detail && <span className="block text-xs text-muted">{s.detail}</span>}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-[11px] text-muted">Usually 20–60 seconds. Re-runs reuse everything already read.</p>
    </section>
  );
}

// ── report ────────────────────────────────────────────────────────────────

function Cites({ cites, sources }: { cites: Cite[]; sources: Map<string, SourceDoc> }) {
  if (!cites.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {cites.slice(0, 3).map((c, i) => {
        const s = sources.get(c.doc);
        const href = s?.url ? `${s.url}${c.page ? `#page=${c.page}` : ""}` : undefined;
        const label = `${c.doc}${c.page ? ` p.${c.page}` : ""}`;
        return href ? (
          <a key={i} href={href} target="_blank" rel="noopener noreferrer" title={s?.title} className="num rounded bg-accent-soft px-1 text-[10px] font-medium text-accent">
            {label}
          </a>
        ) : (
          <span key={i} className="num rounded bg-line px-1 text-[10px] text-muted">
            {label}
          </span>
        );
      })}
    </span>
  );
}

function Section({ title, count, open = true, children }: { title: string; count?: number; open?: boolean; children: React.ReactNode }) {
  return (
    <details open={open} className="card group mx-4 mt-3">
      <summary className="flex cursor-pointer items-center justify-between p-4">
        <span className="text-[15px] font-semibold">
          {title}
          {count !== undefined && <span className="num ml-2 text-xs font-normal text-muted">{count}</span>}
        </span>
        <ChevronDown size={18} className="text-muted transition-transform group-open:rotate-180" />
      </summary>
      <div className="px-4 pb-4">{children}</div>
    </details>
  );
}

const KIND_ICON = { financial: BarChart3, people: UserRound, ownership: PieChart, market: Activity, event: Activity } as const;
const TONE_ICON = { positive: TrendingUp, negative: TrendingDown, neutral: Minus } as const;
const VERDICT = {
  beat: { label: "Beat", cls: "bg-up/15 text-up-ink" },
  met: { label: "Met", cls: "bg-up/10 text-up-ink" },
  missed: { label: "Missed", cls: "bg-down/15 text-down-ink" },
  unclear: { label: "Unclear", cls: "bg-line text-muted" },
} as const;

function monthLabel(d: string): string {
  return new Date(`${d}T00:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

function Timeline({ items, sources }: { items: Movement[]; sources: Map<string, SourceDoc> }) {
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, 10);
  let lastMonth = "";
  return (
    <>
      <ol className="relative space-y-3 border-l border-line pl-5">
        {shown.map((m, i) => {
          const month = monthLabel(m.date);
          const header = month !== lastMonth;
          lastMonth = month;
          const Icon = m.category ? CATEGORY_ICON[m.category] : KIND_ICON[m.kind];
          const T = TONE_ICON[m.tone];
          return (
            <li key={i}>
              {header && <p className="eyebrow -ml-5 mb-2 bg-surface pl-5">{month}</p>}
              <span className="absolute -left-[9px] mt-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full border border-line bg-surface">
                <Icon size={11} className="text-muted" aria-hidden />
              </span>
              <div className="text-[13px] leading-snug">
                <p className="flex items-start gap-1.5">
                  <T size={14} className={`mt-0.5 shrink-0 ${m.tone === "positive" ? "text-up-ink" : m.tone === "negative" ? "text-down-ink" : "text-muted"}`} aria-label={m.tone} />
                  <span className="font-medium">{m.title}</span>
                </p>
                {m.detail && m.detail !== m.title && <p className="mt-0.5 pl-5 text-muted">{m.detail}</p>}
                <p className="mt-1 flex flex-wrap items-center gap-2 pl-5 text-[11px] text-muted">
                  <span className="num">{new Date(`${m.date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>
                  {m.reaction_pct !== null && (
                    <span className={`num rounded-full bg-bg px-1.5 py-px font-medium ${tone(m.reaction_pct)}`}>stock {pct(m.reaction_pct)}</span>
                  )}
                  <Cites cites={m.cites} sources={sources} />
                </p>
              </div>
            </li>
          );
        })}
      </ol>
      {items.length > 10 && (
        <button onClick={() => setAll(!all)} className="mt-3 text-xs font-medium text-accent">
          {all ? "Show fewer" : `Show all ${items.length}`}
        </button>
      )}
    </>
  );
}

function Promises({ items, sources }: { items: PromiseCheck[]; sources: Map<string, SourceDoc> }) {
  return (
    <ul className="space-y-3">
      {items.map((p, i) => (
        <li key={i} className="rounded-xl border border-line p-3 text-[13px] leading-snug">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="font-semibold">{p.quarter}</span>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${VERDICT[p.verdict].cls}`}>{VERDICT[p.verdict].label}</span>
          </div>
          <p>
            <span className="text-muted">Promised: </span>
            {p.promised}
          </p>
          <p className="mt-1">
            <span className="text-muted">Delivered: </span>
            {p.delivered}
            <Cites cites={p.cites} sources={sources} />
          </p>
        </li>
      ))}
    </ul>
  );
}

function Points({ items, sources }: { items: (CitedPoint | Theme)[]; sources: Map<string, SourceDoc> }) {
  return (
    <ul className="space-y-2.5">
      {items.map((x, i) => (
        <li key={i} className="text-[13px] leading-snug">
          {"title" in x ? (
            <>
              <span className="font-medium">{x.title}. </span>
              <span className="text-muted">{x.detail}</span>
            </>
          ) : (
            x.text
          )}
          <Cites cites={x.cites} sources={sources} />
        </li>
      ))}
    </ul>
  );
}

function Report({ r, onRefresh }: { r: DeepResearch; onRefresh: () => void }) {
  const sources = new Map(r.sources.map((s) => [s.id, s]));
  const docs = r.sources.filter((s) => s.kind !== "filing");
  const filings = r.sources.filter((s) => s.kind === "filing");
  return (
    <>
      <div className="mx-4 flex items-center justify-between text-[11px] text-muted">
        <span>
          {ago(r.generated_at)} ago · {docs.length} documents · {r.stats.pages_read.toLocaleString("en-IN")} pages · {filings.length} filings
        </span>
        <button onClick={onRefresh} className="flex items-center gap-1 font-medium text-accent">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {r.summary && (
        <section className="card mx-4 mt-3 p-4">
          <p className="eyebrow mb-1.5">What changed</p>
          <p className="text-[15px] leading-relaxed">{r.summary}</p>
        </section>
      )}

      {r.promised_vs_delivered.length > 0 && (
        <Section title="Promised vs delivered" count={r.promised_vs_delivered.length}>
          <Promises items={r.promised_vs_delivered} sources={sources} />
        </Section>
      )}

      <Section title="Major movements, last 12 months" count={r.movements.length}>
        <Timeline items={r.movements} sources={sources} />
      </Section>

      {r.guidance.length > 0 && (
        <Section title="Guidance on record" count={r.guidance.length}>
          <ul className="divide-y divide-line">
            {r.guidance.map((g, i) => (
              <li key={i} className="py-2.5 text-[13px] leading-snug">
                <p className="text-muted">
                  {g.metric}
                  {g.horizon && <span className="text-[11px]"> · {g.horizon}</span>}
                </p>
                <p className="mt-0.5 font-semibold">
                  {g.value}
                  <Cites cites={g.cites} sources={sources} />
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(r.bull.length > 0 || r.bear.length > 0) && (
        <Section title="Bull vs bear">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-up-ink">
            <TrendingUp size={14} /> Bull case
          </p>
          <Points items={r.bull} sources={sources} />
          <p className="mb-2 mt-4 flex items-center gap-1.5 text-xs font-semibold text-down-ink">
            <TrendingDown size={14} /> Bear case
          </p>
          <Points items={r.bear} sources={sources} />
        </Section>
      )}

      {r.themes.length > 0 && (
        <Section title="Themes" count={r.themes.length} open={false}>
          <Points items={r.themes} sources={sources} />
        </Section>
      )}
      {r.risks.length > 0 && (
        <Section title="Risks" count={r.risks.length} open={false}>
          <Points items={r.risks} sources={sources} />
        </Section>
      )}

      {r.questions.length > 0 && (
        <Section title="Questions worth asking" count={r.questions.length}>
          <ul className="space-y-4">
            {r.questions.map((q, i) => (
              <li key={i} className="text-[13px] leading-snug">
                <p className="font-medium">{q.question}</p>
                {q.why && <p className="mt-0.5 text-muted">{q.why}</p>}
                {q.ask && (
                  <div className="mt-2">
                    <NetworkLine hint={q.ask} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Sources read" count={r.sources.length} open={false}>
        <ul className="space-y-2 text-[13px]">
          {r.sources.map((s) => (
            <li key={s.id} className="flex gap-2">
              <span className="num w-7 shrink-0 text-[11px] font-medium text-muted">{s.id}</span>
              <span className="min-w-0 flex-1">
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="hover:text-accent">
                    {s.title} <ArrowUpRight size={12} className="inline" />
                  </a>
                ) : (
                  s.title
                )}
                {s.pages > 0 && (
                  <span className="block text-[11px] text-muted">
                    {s.pages} pages{s.used_pages && s.used_pages < s.pages ? ` · ${s.used_pages} most relevant read` : ""}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      {r.notes.length > 0 && (
        <p className="mx-4 mt-4 text-[11px] leading-relaxed text-muted">
          Some documents weren&apos;t read this time. Refresh to include them; everything already read is reused.
        </p>
      )}
    </>
  );
}
