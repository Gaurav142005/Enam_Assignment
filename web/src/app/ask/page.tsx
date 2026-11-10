import Link from "next/link";
import { ArrowUpRight, Search, Sparkles } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import type { Company } from "@/lib/types";

type Recent = { ticker: string; name: string; finished_at: string; summary: string | null; movements: number };

/** PULL — on-demand research on any NSE ticker. */
export default async function AskPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const q = (await searchParams).q ?? "";
  const [results, watch, portfolio, recent] = await Promise.all([
    q ? api<Company[]>(`/pull/search?q=${encodeURIComponent(q)}`) : Promise.resolve([]),
    api<Company[]>("/portfolio/watchlist"),
    api<Company[]>("/portfolio"),
    api<Recent[]>("/pull/deep").catch(() => [] as Recent[]),
  ]);

  return (
    <main>
      <PageHeader title="Ask" sub="Any NSE company, answered from its own filings." />
      <form action="/ask" className="px-4">
        <label className="card flex items-center gap-2 px-3 py-2.5">
          <Search size={18} className="text-muted" />
          <input
            name="q"
            defaultValue={q}
            placeholder="Ticker or company: DIXON, Aarti…"
            autoComplete="off"
            className="w-full bg-transparent text-[15px] outline-none placeholder:text-muted"
          />
        </label>
      </form>

      {q && (
        <>
          <SectionTitle>Results</SectionTitle>
          <CompanyList items={results} />
        </>
      )}

      {!q && recent.length > 0 && (
        <>
          <SectionTitle>Your deep research</SectionTitle>
          <ul className="card mx-4 divide-y divide-line">
            {recent.map((r) => (
              <li key={r.ticker}>
                <Link href={`/company/${r.ticker}/research`} className="flex items-start gap-3 px-4 py-3 active:bg-line/40">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                    <Sparkles size={14} />
                  </span>
                  <span className="min-w-0 flex-1 text-[13px] leading-snug">
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="font-semibold">{r.ticker}</span>
                      <span className="num shrink-0 text-[11px] text-muted">{ago(r.finished_at)} ago</span>
                    </span>
                    <span className="text-muted line-clamp-2">{r.summary ?? `${r.movements} movements in the last 12 months`}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}

      <SectionTitle>Research list</SectionTitle>
      <CompanyList items={watch} />

      <SectionTitle>Portfolio</SectionTitle>
      <CompanyList items={portfolio} />
    </main>
  );
}

function CompanyList({ items }: { items: Company[] }) {
  return (
    <ul className="card mx-4 divide-y divide-line">
      {items.map((c) => (
        <li key={c.ticker}>
          <Link href={`/company/${c.ticker}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{c.ticker}</span>
              <span className="block truncate text-xs text-muted">
                {c.name} · {c.sector}
              </span>
            </span>
            <ArrowUpRight size={16} className="text-muted" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
