"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { CalendarDays } from "lucide-react";

const OPTIONS = [
  { h: 24, label: "24h" },
  { h: 72, label: "3d" },
  { h: 168, label: "7d" },
  { h: 720, label: "30d" },
];
const KEY = "finn.briefWindow";
const MAX_HOURS = 24 * 90; // the API keeps 90 days of filings

function sinceLabel(hours: number): string {
  const d = new Date(Date.now() - hours * 3600_000);
  return `Since ${d.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}`;
}

/** Lookback window for the Brief: presets, or "since" any date in the last 90 days. The last choice is remembered on this device. */
export function WindowPicker({ value }: { value: number }) {
  const router = useRouter();
  const params = useSearchParams();
  const date = useRef<HTMLInputElement>(null);
  const [custom, setCustom] = useState(false);
  const isPreset = OPTIONS.some((o) => o.h === value);

  const choose = (h: number) => {
    const next = new URLSearchParams(params);
    next.set("h", String(h));
    try {
      localStorage.setItem(KEY, String(h));
    } catch {}
    router.replace(`/?${next}`, { scroll: false });
  };

  // No window in the URL: reopen with the one chosen last time.
  useEffect(() => {
    if (params.get("h")) return;
    try {
      const saved = Number(localStorage.getItem(KEY));
      if (saved && saved !== value) choose(saved);
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const today = new Date().toISOString().slice(0, 10);
  const earliest = new Date(Date.now() - MAX_HOURS * 3600_000).toISOString().slice(0, 10);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="inline-flex gap-1 rounded-full border border-line bg-surface p-0.5 text-xs" role="radiogroup" aria-label="Lookback window">
        {OPTIONS.map(({ h, label }) => (
          <button
            key={h}
            role="radio"
            aria-checked={value === h}
            onClick={() => {
              setCustom(false);
              choose(h);
            }}
            className={`rounded-full px-2.5 py-1 font-medium ${value === h ? "bg-ink text-bg" : "text-muted"}`}
          >
            {label}
          </button>
        ))}
        <button
          role="radio"
          aria-checked={!isPreset}
          onClick={() => {
            setCustom(true);
            setTimeout(() => date.current?.showPicker?.(), 0);
          }}
          className={`flex items-center gap-1 rounded-full px-2.5 py-1 font-medium ${!isPreset ? "bg-ink text-bg" : "text-muted"}`}
        >
          <CalendarDays size={13} aria-hidden />
          {isPreset ? "Custom" : sinceLabel(value)}
        </button>
      </div>
      {(custom || !isPreset) && (
        <label className="flex items-center gap-1.5 text-xs text-muted">
          Since
          <input
            ref={date}
            type="date"
            min={earliest}
            max={today}
            defaultValue={new Date(Date.now() - value * 3600_000).toISOString().slice(0, 10)}
            onChange={(e) => {
              if (!e.target.value) return;
              const start = new Date(`${e.target.value}T00:00:00`).getTime();
              choose(Math.min(MAX_HOURS, Math.max(1, Math.ceil((Date.now() - start) / 3600_000))));
            }}
            className="rounded-lg border border-line bg-surface px-2 py-1 text-xs text-ink"
          />
        </label>
      )}
    </div>
  );
}
