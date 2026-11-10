import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { Avatar } from "@/components/Avatar";
import { BackLink } from "@/components/BackLink";
import { LogContact } from "@/components/LogContact";
import { NetworkLine, Strength } from "@/components/NetworkLine";
import { SectionTitle } from "@/components/PageHeader";
import { RemoveConnection } from "@/components/RemoveConnection";
import { api, ApiError } from "@/lib/api";
import { shortDate, tenure } from "@/lib/format";
import type { Dossier, Person } from "@/lib/types";

const SOURCE: Record<Person["source"], string> = {
  synthetic: "Demo profile",
  linkedin: "From your LinkedIn export",
  manual: "Added by you",
  company: "From company & exchange records",
  filing: "From an exchange filing",
};

function lastSpoke(iso: string | null): string {
  if (!iso) return "No conversation logged";
  const days = Math.round((Date.now() - new Date(`${iso}T00:00:00`).getTime()) / 86400000);
  if (days <= 0) return "Spoke today";
  if (days < 60) return `Last spoke ${days} days ago`;
  return `Last spoke ${Math.round(days / 30)} months ago`;
}

/** Person: a connection (how you know them, when you last spoke) or someone to diligence (who can reach them, what to ask). */
export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let d: Dossier;
  try {
    d = await api<Dossier>(`/network/people/${id}/dossier`);
  } catch (e) {
    if (e instanceof ApiError && e.message.endsWith("404")) notFound();
    throw e;
  }
  const p = d.person;
  const rel = p.relationship;

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <header className="flex flex-col items-center px-6 pb-2 pt-2 text-center">
        <Avatar name={p.name} size={64} />
        <h1 className="mt-3 text-xl font-semibold">{p.name}</h1>
        <p className="mt-0.5 text-sm text-muted">{p.headline}</p>
        {p.bio && <p className="mt-2 max-w-xs text-xs leading-relaxed text-muted">{p.bio}</p>}
        <p className="mt-2 flex items-center gap-3 text-[11px] uppercase tracking-wide text-muted">
          {SOURCE[p.source]}
          {p.linkedin_url && (
            <a href={p.linkedin_url} target="_blank" rel="noopener noreferrer" className="normal-case tracking-normal text-accent">
              LinkedIn profile ↗
            </a>
          )}
        </p>
      </header>

      {rel && (
        <section className="card mx-4 mt-3 p-4" aria-label="Your relationship">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 text-[13px] leading-snug">
              <p className="font-medium">{rel.context}</p>
              <p className="mt-0.5 flex items-center gap-2 text-muted">
                <Strength value={rel.strength} /> {lastSpoke(rel.last_contact)}
              </p>
            </div>
            <LogContact id={p.id} />
          </div>
        </section>
      )}

      {!rel && (
        <>
          <SectionTitle>How you can reach them</SectionTitle>
          <div className="space-y-1.5 px-4">
            {d.shared_with_you.map((x) => (
              <p key={x} className="rounded-xl border border-accent/30 bg-accent-soft/60 px-3 py-2.5 text-[13px] font-medium">
                {x}
              </p>
            ))}
            {d.paths.length || d.shared_with_you.length ? (
              d.paths.map((h) => <NetworkLine key={h.person_id} hint={h} lead="Via" />)
            ) : (
              <p className="text-sm text-muted">No one in your network overlaps with them yet. Fuller career histories for your connections surface more paths.</p>
            )}
          </div>
        </>
      )}

      {d.ask_about.length > 0 && (
        <>
          <SectionTitle>Worth asking about</SectionTitle>
          <ul className="card mx-4 divide-y divide-line">
            {d.ask_about.map((q) => (
              <li key={q} className="px-4 py-3 text-[13px] leading-snug">
                {q}
              </li>
            ))}
          </ul>
        </>
      )}

      {d.in_filings.length > 0 && (
        <>
          <SectionTitle>On the record</SectionTitle>
          <ul className="card mx-4 divide-y divide-line">
            {d.in_filings.map((f) => (
              <li key={`${f.date}-${f.title}`} className="flex items-start justify-between gap-3 px-4 py-3 text-[13px]">
                <span>
                  {f.title}
                  <span className="num block text-[11px] text-muted">{shortDate(f.date)}</span>
                </span>
                {f.url && (
                  <a href={f.url} target="_blank" rel="noopener noreferrer" aria-label="Open filing" className="shrink-0 text-accent">
                    <ArrowUpRight size={15} />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      <SectionTitle>Career</SectionTitle>
      <ol className="card mx-4 divide-y divide-line">
        {p.positions.map((pos) => (
          <li key={`${pos.company}-${pos.title}-${pos.start}`} className="px-4 py-3 text-[13px]">
            <p className="font-medium">{pos.title || "Role not stated"}</p>
            <p className="text-muted">
              {pos.ticker ? (
                <Link href={`/company/${pos.ticker}`} className="text-accent">
                  {pos.company}
                </Link>
              ) : (
                pos.company
              )}
              {pos.start !== null && (
                <>
                  {" "}
                  · <span className="num">{tenure(pos.start, pos.end)}</span>
                </>
              )}
            </p>
          </li>
        ))}
      </ol>

      {p.education.length > 0 && (
        <>
          <SectionTitle>Education</SectionTitle>
          <ul className="card mx-4 divide-y divide-line">
            {p.education.map((e) => (
              <li key={e.school} className="px-4 py-3 text-[13px]">
                <p className="font-medium">{e.school}</p>
                <p className="text-muted">{[e.degree, tenure(e.start, e.end, false)].filter(Boolean).join(" · ")}</p>
              </li>
            ))}
          </ul>
        </>
      )}

      {p.expertise.length > 0 && (
        <>
          <SectionTitle>Go-to for</SectionTitle>
          <div className="flex flex-wrap gap-2 px-4">
            {p.expertise.map((x) => (
              <Link key={x} href={`/network?q=${encodeURIComponent(x)}`} className="rounded-full bg-accent-soft px-3 py-1 text-[13px] text-accent">
                {x}
              </Link>
            ))}
          </div>
        </>
      )}

      {(p.source === "manual" || p.source === "linkedin") && (
        <div className="mt-8 text-center">
          <RemoveConnection id={p.id} name={p.name} />
        </div>
      )}
    </main>
  );
}
