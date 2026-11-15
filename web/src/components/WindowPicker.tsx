"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { CalendarDays, X } from "lucide-react";
import { shortDay } from "@/lib/format";

const OPTIONS = [
  { h: 24, label: "24h" },
  { h: 72, label: "3d" },
  { h: 168, label: "7d" },
  { h: 720, label: "30d" },
];
const KEY = "finn.briefWindow"; // "168" for a preset, "since:2026-11-03" for a date
const MAX_DAYS = 90; // the API keeps 90 days of filings

/** YYYY-MM-DD in India, `daysAgo` days back. */
function istDate(daysAgo = 0): string {
  return new Date(Date.now() - daysAgo * 86400_000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

/**
 * Lookback window for the Brief: presets, or "since" any date in the last 90 days. A date is kept as a date (?since=),
 * not converted to hours, so the label always shows the day you picked. The last choice is remembered on this device.
 */
export function WindowPicker({ value, since }: { value: number; since: string | null }) {
  const router = useRouter();
  const params = useSearchParams();
  const input = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(since ?? istDate(7));

  const go = (next: { h?: number; since?: string }) => {
    const q = new URLSearchParams(params);
    q.delete("h");
    q.delete("since");
    if (next.since) q.set("since", next.since);
    else q.set("h", String(next.h));
    try {
      localStorage.setItem(KEY, next.since ? `since:${next.since}` : String(next.h));
    } catch {}
    router.replace(`/?${q}`, { scroll: false });
  };

  // No window in the URL: reopen with the one chosen last time.
  useEffect(() => {
    if (params.get("h") || params.get("since")) return;
    try {
      const saved = localStorage.getItem(KEY) ?? "";
      if (saved.startsWith("since:")) {
        const d = saved.slice(6);
        if (d >= istDate(MAX_DAYS) && d <= istDate()) go({ since: d });
      } else if (Number(saved) && Number(saved) !== value) go({ h: Number(saved) });
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (since) setDraft(since);
  }, [since]);

  const valid = (d: string) => /^\d{4}-\d{2}-\d{2}$/.test(d) && d >= istDate(MAX_DAYS) && d <= istDate();
  const apply = () => {
    if (!valid(draft)) return;
    setOpen(false);
    if (draft !== since) go({ since: draft });
  };

  const custom = !!since;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="inline-flex gap-1 rounded-full border border-line bg-surface p-0.5 text-xs" role="radiogroup" aria-label="Lookback window">
        {OPTIONS.map(({ h, label }) => (
          <button
            key={h}
            role="radio"
            aria-checked={!custom && value === h}
            onClick={() => {
              setOpen(false);
              go({ h });
            }}
            className={`rounded-full px-2.5 py-1 font-medium transition-colors ${!custom && value === h ? "bg-ink text-bg" : "text-muted"}`}
          >
            {label}
          </button>
        ))}
        <button
          role="radio"
          aria-checked={custom}
          onClick={() => {
            setOpen(!open);
            if (!open) setTimeout(() => input.current?.focus(), 0);
          }}
          className={`flex items-center gap-1 rounded-full px-2.5 py-1 font-medium transition-colors ${custom ? "bg-ink text-bg" : "text-muted"}`}
        >
          <CalendarDays size={13} aria-hidden />
          {custom ? `Since ${shortDay(since)}` : "Custom"}
        </button>
      </div>

      {open && (
        <div className="flex w-full animate-fade-in items-center gap-2 rounded-2xl border border-line bg-surface p-2 text-xs">
          <span className="pl-1 text-muted">Since</span>
          {/* Nothing reloads while the date is being picked (the iOS wheel fires a change on every tick); Show applies it. */}
          <input
            ref={input}
            type="date"
            min={istDate(MAX_DAYS)}
            max={istDate()}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            aria-label="Show filings since"
            className="min-w-0 flex-1 rounded-lg border border-line bg-bg px-2 py-1.5 text-[13px] text-ink"
          />
          <button onClick={apply} disabled={!valid(draft)} className="rounded-full bg-ink px-3 py-1.5 font-medium text-bg disabled:opacity-40">
            Show
          </button>
          <button onClick={() => setOpen(false)} aria-label="Close" className="rounded-full p-1 text-muted">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
