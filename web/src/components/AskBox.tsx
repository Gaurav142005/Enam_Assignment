"use client";

import { useState } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { apiPost } from "@/lib/api";
import type { Answer } from "@/lib/types";
import { NetworkLine } from "./NetworkLine";

const SUGGESTED = ["What is management guiding for?", "What are the capex plans?", "What worried analysts on the last call?", "How are margins trending and why?"];

/** PULL: ask the company's own documents a question. Answers cite the page; if the documents don't say, it says so. */
export function AskBox({ ticker }: { ticker: string }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [a, setA] = useState<Answer | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ask = async (question: string) => {
    if (question.trim().length < 3 || busy) return;
    setQ(question);
    setBusy(true);
    setError(null);
    try {
      setA(await apiPost<Answer>(`/pull/ask/${encodeURIComponent(ticker)}`, { question }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const src = new Map((a?.sources ?? []).map((s) => [s.id, s]));
  return (
    <section className="card mx-4 p-4" aria-label={`Ask about ${ticker}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(q);
        }}
        className="flex items-center gap-2 rounded-xl border border-line bg-bg px-3 py-2 focus-within:border-accent"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={`Ask anything about ${ticker}…`}
          aria-label="Question"
          className="min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted"
        />
        <button type="submit" disabled={busy || q.trim().length < 3} aria-label="Ask" className="flex h-7 w-7 items-center justify-center rounded-full bg-ink text-bg disabled:opacity-30">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <ArrowUp size={15} />}
        </button>
      </form>

      {!a && !busy && (
        <div className="no-scrollbar -mx-4 mt-3 flex gap-2 overflow-x-auto px-4">
          {SUGGESTED.map((s) => (
            <button key={s} onClick={() => ask(s)} className="shrink-0 rounded-full border border-line px-3 py-1.5 text-xs text-muted active:bg-line/40">
              {s}
            </button>
          ))}
        </div>
      )}
      {busy && <p className="mt-3 text-xs text-muted">Reading the transcripts and presentations…</p>}
      {error && <p className="mt-3 text-sm text-down-ink">{error}</p>}

      {a && !busy && (
        <div className="mt-4 space-y-3" aria-live="polite">
          {a.answer ? (
            <p className={`text-[15px] leading-relaxed ${a.found ? "" : "text-muted"}`}>{a.answer}</p>
          ) : (
            <p className="text-sm text-muted">No model is available right now, so here are the closest passages from the company&apos;s documents.</p>
          )}
          {a.points.length > 0 && (
            <ul className="space-y-2">
              {a.points.map((p, i) => (
                <li key={i} className="border-l-2 border-line pl-3 text-[13px] leading-snug text-muted">
                  {p.text}{" "}
                  {p.cites.map((c, k) => {
                    const s = src.get(c.doc);
                    return (
                      <a key={k} href={s ? `${s.url}${c.page ? `#page=${c.page}` : ""}` : undefined} target="_blank" rel="noopener noreferrer" title={s?.title} className="num ml-1 rounded bg-accent-soft px-1 text-[10px] font-medium text-accent">
                        {c.doc}
                        {c.page ? ` p.${c.page}` : ""}
                      </a>
                    );
                  })}
                </li>
              ))}
            </ul>
          )}
          {!a.answer &&
            a.passages.map((p) => (
              <p key={`${p.doc}-${p.page}`} className="border-l-2 border-line pl-3 text-xs leading-snug text-muted">
                <span className="num font-medium text-ink">
                  {p.doc} p.{p.page}
                </span>{" "}
                {p.text.slice(0, 320)}…
              </p>
            ))}
          {a.sources.length > 0 && <p className="text-[11px] text-muted">From: {a.sources.map((s) => `${s.id} ${s.title}`).join(" · ")}</p>}
          {a.ask && (
            <div>
              <p className="eyebrow mb-1.5">For colour beyond the documents</p>
              <NetworkLine hint={a.ask} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
