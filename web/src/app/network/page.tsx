import Link from "next/link";
import { ChevronDown, ChevronRight, FileUp, Search, UserPlus } from "lucide-react";
import { Avatar } from "@/components/Avatar";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { api } from "@/lib/api";
import { NetworkLine } from "@/components/NetworkLine";
import type { CompanyPeopleSummary, NetworkAnswer, Person, ReconnectNudge, ThemeGroup } from "@/lib/types";

const SOURCE_LABEL: Record<Person["source"], string> = { linkedin: "LinkedIn", manual: "Added", synthetic: "Demo", company: "", filing: "" };
const ASKS = ["Who knows rural lending?", "Anyone at Dixon?", "Specialty chemicals", "Finance people at Polycab", "IIT Kanpur"];
const FILTERS = [
  ["all", "All"],
  ["linkedin", "LinkedIn"],
  ["manual", "Added"],
  ["synthetic", "Demo"],
] as const;

/** NETWORK: queried directly. (It also surfaces inside Brief and Ask.) */
export default async function NetworkPage({ searchParams }: { searchParams: Promise<{ src?: string; theme?: string; q?: string }> }) {
  const { src = "all", theme, q } = await searchParams;
  const answer = q ? await api<NetworkAnswer>(`/network/ask?q=${encodeURIComponent(q)}`) : null;
  const [nudges, themes, people, companies] = await Promise.all([
    api<ReconnectNudge[]>("/network/reconnect"),
    api<ThemeGroup[]>("/network/themes"),
    api<Person[]>("/network/people"),
    api<CompanyPeopleSummary[]>("/network/companies"),
  ]);
  const imported = people.filter((p) => p.source === "linkedin").length;
  const portfolio = new Map(companies.map((c) => [c.ticker, c.name]));
  const atPortfolio = new Map<string, Person[]>();
  for (const p of people) {
    const t = p.positions.find((pos) => pos.ticker && portfolio.has(pos.ticker))?.ticker;
    if (t) atPortfolio.set(t, [...(atPortfolio.get(t) ?? []), p]);
  }
  const bySource = src === "all" ? people : people.filter((p) => p.source === src);
  const shown = theme ? bySource.filter((p) => p.expertise.includes(theme)) : bySource;

  return (
    <main>
      <PageHeader
        title="Network"
        sub={`${people.length} people${imported ? ` · ${imported} from LinkedIn` : ""}`}
        right={
          <div className="mb-1 flex gap-1">
            <Link href="/network/import" aria-label="Import LinkedIn connections" className="rounded-full p-2 text-muted active:bg-line/50">
              <FileUp size={20} />
            </Link>
            <Link href="/network/new" aria-label="Add a connection" className="rounded-full p-2 text-muted active:bg-line/50">
              <UserPlus size={20} />
            </Link>
          </div>
        }
      />

      <form action="/network" className="px-4">
        <label className="card flex items-center gap-2 px-3 py-2.5 focus-within:border-accent">
          <Search size={18} className="shrink-0 text-muted" />
          <input name="q" defaultValue={q ?? ""} placeholder="Who knows…  rural lending · Dixon · a CFO" autoComplete="off" aria-label="Ask your network" className="w-full bg-transparent text-[15px] outline-none placeholder:text-muted" />
        </label>
      </form>
      {!answer && (
        <div className="no-scrollbar mt-2 flex gap-2 overflow-x-auto px-4">
          {ASKS.map((x) => (
            <Link key={x} href={`/network?q=${encodeURIComponent(x)}`} className="shrink-0 rounded-full border border-line bg-surface px-3 py-1.5 text-xs text-muted">
              {x}
            </Link>
          ))}
        </div>
      )}
      {answer && (
        <section className="mt-3" aria-live="polite">
          <div className="mb-2 flex items-baseline justify-between gap-3 px-4">
            <p className="text-xs text-muted">{answer.understood}</p>
            <Link href="/network" className="shrink-0 text-xs text-accent">
              Clear
            </Link>
          </div>
          {answer.results.length ? (
            <div className="space-y-1.5 px-4">
              {answer.results.map((h) => (
                <NetworkLine key={h.person_id} hint={h} lead="" />
              ))}
            </div>
          ) : (
            <p className="px-4 text-sm text-muted">No one yet. Try a company, a sector, a role or a school.</p>
          )}
        </section>
      )}
      <div className="h-4" />

      {!imported && (
        <Link href="/network/import" className="card mx-4 flex items-center gap-3 p-4 active:opacity-70">
          <FileUp size={22} className="shrink-0 text-accent" />
          <span className="min-w-0 flex-1 text-[13px] leading-snug">
            <span className="block font-medium">Bring in your LinkedIn connections</span>
            <span className="block text-muted">Upload your data export and FINN maps who you know at every company you own or research.</span>
          </span>
          <ChevronRight size={16} className="text-muted" />
        </Link>
      )}

      {nudges.length > 0 && (
        <>
          <SectionTitle>Good reason to reconnect</SectionTitle>
          <div className="card mx-4 divide-y divide-line">
            {nudges.map((n) => (
              <Link key={n.person.id} href={`/people/${n.person.id}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
                <Avatar name={n.person.name} />
                <span className="min-w-0 text-[13px] leading-snug">
                  <span className="block font-medium">{n.person.name}</span>
                  <span className="block text-muted">{n.reason}</span>
                </span>
              </Link>
            ))}
          </div>
        </>
      )}

      {atPortfolio.size > 0 && (
        <>
          <SectionTitle>Your people at portfolio companies</SectionTitle>
          <ul className="card mx-4 divide-y divide-line">
            {[...atPortfolio.entries()].map(([t, ps]) => (
              <li key={t} className="px-4 py-3">
                <Link href={`/company/${t}`} className="text-xs font-semibold">
                  {t} <span className="font-normal text-muted">· {portfolio.get(t)}</span>
                </Link>
                <div className="mt-2 flex flex-wrap gap-2">
                  {ps.map((p) => (
                    <Link key={p.id} href={`/people/${p.id}`} className="flex items-center gap-1.5 rounded-full bg-accent-soft/60 py-1 pl-1 pr-3 text-[13px] active:opacity-70">
                      <Avatar name={p.name} size={22} />
                      {p.name}
                    </Link>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      <SectionTitle>Leadership at your companies</SectionTitle>
      <details className="card group mx-4">
        <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm">
          <span>
            {companies.reduce((n, c) => n + c.people, 0)} leaders across {companies.length} companies
            <span className="block text-xs text-muted">You have a way in at {companies.filter((c) => c.connections > 0).length} of them</span>
          </span>
          <ChevronDown size={16} className="text-muted transition-transform group-open:rotate-180" />
        </summary>
      <ul className="divide-y divide-line border-t border-line">
        {companies.map((c) => (
          <li key={c.ticker}>
            <Link href={`/company/${c.ticker}#leadership`} className="flex items-center gap-3 px-4 py-2.5 active:bg-line/40">
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{c.ticker}</span>
                <span className="block truncate text-xs text-muted">{c.name}</span>
              </span>
              <span className="text-right text-xs text-muted">
                <span className="num block">{c.people} leaders</span>
                <span className={`num block ${c.connections ? "font-medium text-accent" : ""}`}>
                  {c.connections ? `${c.connections} you know` : "no one yet"}
                </span>
              </span>
              <ChevronRight size={16} className="text-muted" />
            </Link>
          </li>
        ))}
      </ul>
      </details>

      {themes.length > 0 && (
        <>
          <SectionTitle>Expertise map</SectionTitle>
          <div className="flex flex-wrap gap-2 px-4">
            {themes.map((t) => {
              const on = theme === t.theme;
              return (
                <Link
                  key={t.theme}
                  href={on ? "/network" : `/network?theme=${encodeURIComponent(t.theme)}#everyone`}
                  scroll={false}
                  aria-pressed={on}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] ${on ? "border-ink bg-ink text-bg" : "border-line bg-surface"}`}
                >
                  {t.theme}
                  <span className={`num text-xs ${on ? "text-bg/70" : "text-muted"}`}>{t.people.length}</span>
                </Link>
              );
            })}
          </div>
        </>
      )}

      <div id="everyone" className="scroll-mt-4" />
      <SectionTitle right={theme ? <Link href="/network" className="text-xs text-accent">Clear “{theme}”</Link> : undefined}>
        {theme ? `Go-to for ${theme}` : "Everyone"}
      </SectionTitle>
      <div className="mb-2 flex gap-1.5 px-4">
        {FILTERS.map(([k, label]) => (
          <Link
            key={k}
            href={k === "all" ? "/network" : `/network?src=${k}`}
            scroll={false}
            className={`rounded-full px-3 py-1 text-xs font-medium ${src === k ? "bg-ink text-bg" : "border border-line bg-surface text-muted"}`}
          >
            {label}
          </Link>
        ))}
      </div>
      <ul className="card mx-4 divide-y divide-line">
        {shown.length === 0 && <li className="px-4 py-6 text-center text-sm text-muted">No one here yet.</li>}
        {shown.map((p) => (
          <li key={p.id}>
            <Link href={`/people/${p.id}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
              <Avatar name={p.name} />
              <span className="min-w-0 flex-1 text-[13px] leading-snug">
                <span className="block font-medium">{p.name}</span>
                <span className="block truncate text-muted">{p.headline}</span>
              </span>
              {SOURCE_LABEL[p.source] && <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted">{SOURCE_LABEL[p.source]}</span>}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
