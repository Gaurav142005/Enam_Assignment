import Link from "next/link";
import { ArrowUpRight, Search } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Company } from "@/lib/types";

/** PULL — on-demand research on any NSE ticker. */
export default async function AskPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const q = (await searchParams).q ?? "";
  const [results, watch, portfolio] = await Promise.all([
    q ? api<Company[]>(`/pull/search?q=${encodeURIComponent(q)}`) : Promise.resolve([]),
    api<Company[]>("/portfolio/watchlist"),
    api<Company[]>("/portfolio"),
  ]);

  return (
    <main>
      <PageHeader title="Ask" sub="Research any NSE company, from its own filings." />
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
