"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUpRight, Loader2, NotebookPen } from "lucide-react";
import { api, apiDelete, apiPutJson } from "@/lib/api";
import type { Thesis, ThesisCheck } from "@/lib/types";
import { ThesisVerdict } from "./ThesisVerdict";

/** Your thesis on a company, in your words, and what recent filings say about it. */
export function ThesisCard({ ticker }: { ticker: string }) {
  const [thesis, setThesis] = useState<Thesis | null | undefined>(undefined);
  const [checks, setChecks] = useState<ThesisCheck[]>([]);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    const t = await api<Thesis | null>(`/portfolio/theses/${ticker}`);
    setThesis(t);
    if (t) setChecks(await api<ThesisCheck[]>(`/portfolio/theses/${ticker}/checks`));
    if (t?.checking) timer.current = setTimeout(load, 2500); // re-checking recent filings in the background
  }, [ticker]);

  useEffect(() => {
    load().catch(() => setThesis(null));
    return () => void (timer.current && clearTimeout(timer.current));
  }, [load]);

  const save = async () => {
    setError(null);
    try {
      setThesis(await apiPutJson<Thesis>(`/portfolio/theses/${ticker}`, { text: draft }));
      setEditing(false);
      setChecks([]);
      timer.current = setTimeout(load, 2500);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (thesis === undefined) return null;
  return (
    <section className="card mx-4 mb-3 p-4" aria-label="Your thesis">
      <div className="flex items-center justify-between">
        <p className="eyebrow flex items-center gap-1.5">
          <NotebookPen size={13} aria-hidden /> Your thesis
        </p>
        {thesis && !editing && (
          <button
            onClick={() => {
              setDraft(thesis.text);
              setEditing(true);
            }}
            className="text-xs font-medium text-accent"
          >
            Edit
          </button>
        )}
      </div>

      {editing || !thesis ? (
        <div className="mt-2 space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            maxLength={600}
            placeholder={`Why do you own ${ticker}? e.g. "Margins stay above 13% while volumes grow 20%+ for three years"`}
            className="w-full resize-none rounded-xl border border-line bg-bg px-3 py-2.5 text-[14px] leading-snug outline-none placeholder:text-muted focus:border-accent"
          />
          {error && <p className="text-sm text-down-ink">{error}</p>}
          <div className="flex items-center gap-2">
            <button onClick={save} disabled={draft.trim().length < 5} className="rounded-full bg-ink px-4 py-2 text-sm font-medium text-bg disabled:opacity-40">
              Save
            </button>
            {thesis && (
              <>
                <button onClick={() => setEditing(false)} className="rounded-full border border-line px-4 py-2 text-sm">
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    await apiDelete(`/portfolio/theses/${ticker}`);
                    setThesis(null);
                    setChecks([]);
                    setEditing(false);
                    setDraft("");
                  }}
                  className="ml-auto text-xs font-medium text-down-ink"
                >
                  Delete
                </button>
              </>
            )}
          </div>
          {!thesis && <p className="text-[11px] text-muted">FINN checks every material filing against it and tells you when one supports or challenges it.</p>}
        </div>
      ) : (
        <>
          <p className="mt-2 text-[15px] leading-relaxed">&ldquo;{thesis.text}&rdquo;</p>
          <div className="mt-3 space-y-2" aria-live="polite">
            {thesis.checking && (
              <p className="flex items-center gap-2 text-xs text-muted">
                <Loader2 size={13} className="animate-spin" /> Checking recent filings against it…
              </p>
            )}
            {!thesis.checking && checks.length === 0 && <p className="text-xs text-muted">No recent filing bears on it either way.</p>}
            {checks.map((c) => (
              <div key={c.announcement_id} className="border-t border-line pt-2">
                <p className="mb-1 flex items-center justify-between gap-2 text-[11px] text-muted">
                  <span className="truncate">
                    {c.date} · {c.title}
                  </span>
                  {c.url && (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" aria-label="Open filing" className="shrink-0">
                      <ArrowUpRight size={12} />
                    </a>
                  )}
                </p>
                <ThesisVerdict check={c} compact />
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
