"use client";

import { useRouter, useSearchParams } from "next/navigation";

const OPTIONS = [
  { h: 4, label: "4h" },
  { h: 24, label: "24h" },
  { h: 72, label: "3d" },
  { h: 168, label: "7d" },
];

export function WindowPicker({ value }: { value: number }) {
  const router = useRouter();
  const params = useSearchParams();
  return (
    <div className="inline-flex gap-1 rounded-full border border-line bg-surface p-0.5 text-xs" role="radiogroup" aria-label="Time window">
      {OPTIONS.map(({ h, label }) => (
        <button
          key={h}
          role="radio"
          aria-checked={value === h}
          onClick={() => {
            const next = new URLSearchParams(params);
            next.set("h", String(h));
            router.replace(`/?${next}`, { scroll: false });
          }}
          className={`rounded-full px-2.5 py-1 font-medium ${value === h ? "bg-ink text-bg" : "text-muted"}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
