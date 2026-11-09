import Link from "next/link";
import { Avatar } from "@/components/Avatar";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Person, ReconnectNudge, ThemeGroup } from "@/lib/types";

/** NETWORK — queried directly. (It also surfaces inside Brief and Ask.) */
export default async function NetworkPage() {
  const [nudges, themes, people] = await Promise.all([
    api<ReconnectNudge[]>("/network/reconnect"),
    api<ThemeGroup[]>("/network/themes"),
    api<Person[]>("/network/people"),
  ]);

  return (
    <main>
      <PageHeader title="Network" sub={`${people.length} people · ${themes.length} areas of expertise`} />

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

      <SectionTitle>Expertise map</SectionTitle>
      <div className="flex flex-wrap gap-2 px-4">
        {themes.map((t) => (
          <span key={t.theme} className="card flex items-center gap-1.5 px-3 py-1.5 text-[13px]">
            {t.theme}
            <span className="num text-xs text-muted">{t.people.length}</span>
          </span>
        ))}
      </div>

      <SectionTitle>People</SectionTitle>
      <ul className="card mx-4 divide-y divide-line">
        {people.map((p) => (
          <li key={p.id}>
            <Link href={`/people/${p.id}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
              <Avatar name={p.name} />
              <span className="min-w-0 text-[13px] leading-snug">
                <span className="block font-medium">{p.name}</span>
                <span className="block truncate text-muted">{p.headline}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
