import Link from "next/link";
import { notFound } from "next/navigation";
import { Avatar } from "@/components/Avatar";
import { BackLink } from "@/components/BackLink";
import { NetworkLine } from "@/components/NetworkLine";
import { SectionTitle } from "@/components/PageHeader";
import { api, ApiError } from "@/lib/api";
import type { NetworkHint, Person } from "@/lib/types";

/** Person: career path, how you know them / who knows them (diligence + second-degree reach). */
export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let p: Person;
  try {
    p = await api<Person>(`/network/people/${id}`);
  } catch (e) {
    if (e instanceof ApiError && e.message.endsWith("404")) notFound();
    throw e;
  }
  const inNetwork = p.relationship !== null;
  const connections = inNetwork ? [] : await api<NetworkHint[]>(`/network/people/${id}/connections`);

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <header className="flex flex-col items-center px-4 pb-2 pt-2 text-center">
        <Avatar name={p.name} size={64} />
        <h1 className="mt-3 text-xl font-semibold">{p.name}</h1>
        <p className="mt-0.5 text-sm text-muted">{p.headline}</p>
        {p.relationship && <p className="mt-2 text-xs text-muted">{p.relationship.context}</p>}
      </header>

      {!inNetwork && (
        <>
          <SectionTitle>Who you know who knows them</SectionTitle>
          <div className="space-y-1.5 px-4">
            {connections.length ? (
              connections.map((h) => <NetworkLine key={h.person_id} hint={h} lead="" />)
            ) : (
              <p className="text-sm text-muted">No overlap with your network.</p>
            )}
          </div>
        </>
      )}

      <SectionTitle>Career</SectionTitle>
      <ol className="card mx-4 divide-y divide-line">
        {p.positions.map((pos) => (
          <li key={`${pos.company}-${pos.start}`} className="px-4 py-3 text-[13px]">
            <p className="font-medium">{pos.title}</p>
            <p className="text-muted">
              {pos.ticker ? (
                <Link href={`/company/${pos.ticker}`} className="text-accent">
                  {pos.company}
                </Link>
              ) : (
                pos.company
              )}{" "}
              · <span className="num">{pos.start}–{pos.end ?? "now"}</span>
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
                <p className="text-muted">
                  {e.degree} · <span className="num">{e.start}–{e.end}</span>
                </p>
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
              <span key={x} className="rounded-full bg-accent-soft px-3 py-1 text-[13px] text-accent">
                {x}
              </span>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
