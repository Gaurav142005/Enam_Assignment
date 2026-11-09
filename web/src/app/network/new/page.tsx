"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus, X } from "lucide-react";
import { BackLink } from "@/components/BackLink";
import { PageHeader } from "@/components/PageHeader";
import { Segmented } from "@/components/Segmented";
import { apiPost } from "@/lib/api";
import type { Person, PersonIn } from "@/lib/types";

type Role = { company: string; title: string; start: string; end: string };
type School = { school: string; degree: string; start: string; end: string };

const CLOSENESS: Record<string, number> = { Close: 0.85, Regular: 0.6, Acquaintance: 0.35 };
const field = "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-[15px] outline-none placeholder:text-muted focus:border-accent";
const year = (s: string) => (/^\d{4}$/.test(s.trim()) ? Number(s.trim()) : null);

/** Add a connection by hand: the people you know that LinkedIn doesn't (or that you haven't exported yet). */
export default function NewConnectionPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [context, setContext] = useState("");
  const [closeness, setCloseness] = useState("Regular");
  const [lastContact, setLastContact] = useState("");
  const [expertise, setExpertise] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [roles, setRoles] = useState<Role[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body: PersonIn = {
      name: name.trim(),
      current_title: title.trim() || undefined,
      current_company: company.trim() || undefined,
      context: context.trim() || undefined,
      strength: CLOSENESS[closeness],
      last_contact: lastContact || null,
      expertise: expertise.split(",").map((x) => x.trim()).filter(Boolean),
      linkedin_url: linkedin.trim() || undefined,
      past_roles: roles
        .filter((r) => r.company.trim())
        .map((r) => ({ company: r.company.trim(), title: r.title.trim(), ticker: null, start: year(r.start), end: year(r.end) })),
      education: schools
        .filter((s) => s.school.trim())
        .map((s) => ({ school: s.school.trim(), degree: s.degree.trim(), start: year(s.start), end: year(s.end) })),
    };
    try {
      const p = await apiPost<Person>("/network/people", body);
      router.push(`/people/${p.id}`);
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact title="Add a connection" />
      <form onSubmit={submit} className="space-y-3 px-4">
        <input className={field} placeholder="Full name *" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} autoFocus />
        <div className="grid grid-cols-2 gap-2">
          <input className={field} placeholder="Current role" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className={field} placeholder="Company" value={company} onChange={(e) => setCompany(e.target.value)} />
        </div>
        <input className={field} placeholder="How you know them (e.g. IIT batchmate)" value={context} onChange={(e) => setContext(e.target.value)} />
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-muted">How close</span>
          <Segmented value={closeness} options={Object.keys(CLOSENESS)} label="Closeness" onChange={setCloseness} />
        </div>
        <label className="flex items-center justify-between gap-3 text-sm text-muted">
          Last spoke
          <input type="date" className={`${field} w-auto`} value={lastContact} onChange={(e) => setLastContact(e.target.value)} />
        </label>

        <h2 className="eyebrow pt-3">Career</h2>
        {roles.map((r, i) => (
          <Row key={i} onRemove={() => setRoles(roles.filter((_, k) => k !== i))}>
            <input className={field} placeholder="Company" value={r.company} onChange={(e) => setRoles(roles.map((x, k) => (k === i ? { ...x, company: e.target.value } : x)))} />
            <input className={field} placeholder="Title" value={r.title} onChange={(e) => setRoles(roles.map((x, k) => (k === i ? { ...x, title: e.target.value } : x)))} />
            <Years start={r.start} end={r.end} onChange={(start, end) => setRoles(roles.map((x, k) => (k === i ? { ...x, start, end } : x)))} />
          </Row>
        ))}
        <AddButton onClick={() => setRoles([...roles, { company: "", title: "", start: "", end: "" }])}>Add past role</AddButton>

        <h2 className="eyebrow pt-3">Education</h2>
        {schools.map((s, i) => (
          <Row key={i} onRemove={() => setSchools(schools.filter((_, k) => k !== i))}>
            <input className={field} placeholder="School" value={s.school} onChange={(e) => setSchools(schools.map((x, k) => (k === i ? { ...x, school: e.target.value } : x)))} />
            <input className={field} placeholder="Degree" value={s.degree} onChange={(e) => setSchools(schools.map((x, k) => (k === i ? { ...x, degree: e.target.value } : x)))} />
            <Years start={s.start} end={s.end} onChange={(start, end) => setSchools(schools.map((x, k) => (k === i ? { ...x, start, end } : x)))} />
          </Row>
        ))}
        <AddButton onClick={() => setSchools([...schools, { school: "", degree: "", start: "", end: "" }])}>Add school</AddButton>

        <h2 className="eyebrow pt-3">More</h2>
        <input className={field} placeholder="Go-to for (comma-separated: rural lending, specialty chemicals…)" value={expertise} onChange={(e) => setExpertise(e.target.value)} />
        <input className={field} placeholder="LinkedIn URL (optional)" type="url" value={linkedin} onChange={(e) => setLinkedin(e.target.value)} />

        {error && <p className="text-sm text-down-ink">{error}</p>}
        <button type="submit" disabled={busy || name.trim().length < 2} className="mt-2 w-full rounded-full bg-ink py-3 text-sm font-medium text-bg disabled:opacity-40">
          {busy ? "Saving…" : "Save connection"}
        </button>
        <p className="pb-4 text-center text-[11px] text-muted">Past roles and schools are what let FINN find overlaps with company leaders.</p>
      </form>
    </main>
  );
}

function Row({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
  return (
    <div className="card relative space-y-2 p-3 pr-10">
      {children}
      <button type="button" onClick={onRemove} aria-label="Remove" className="absolute right-2 top-2 rounded-full p-1.5 text-muted active:bg-line/50">
        <X size={16} />
      </button>
    </div>
  );
}

function Years({ start, end, onChange }: { start: string; end: string; onChange: (s: string, e: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <input className={field} inputMode="numeric" placeholder="From (year)" value={start} onChange={(e) => onChange(e.target.value, end)} />
      <input className={field} inputMode="numeric" placeholder="To (blank = now)" value={end} onChange={(e) => onChange(start, e.target.value)} />
    </div>
  );
}

function AddButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="flex items-center gap-1.5 text-sm font-medium text-accent">
      <Plus size={16} /> {children}
    </button>
  );
}
