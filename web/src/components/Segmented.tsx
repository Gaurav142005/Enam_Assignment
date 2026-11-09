"use client";

import { useRouter, useSearchParams } from "next/navigation";

/** One-row preset filter that writes a search param (shareable, back-button friendly). */
export function SegmentedParam({ param, value, options, label }: { param: string; value: string; options: string[]; label: string }) {
  const router = useRouter();
  const params = useSearchParams();
  return (
    <Segmented
      value={value}
      options={options}
      label={label}
      onChange={(v) => {
        const next = new URLSearchParams(params);
        next.set(param, v);
        router.replace(`?${next}`, { scroll: false });
      }}
    />
  );
}

export function Segmented({ value, options, label, onChange }: { value: string; options: string[]; label: string; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex gap-0.5 rounded-full border border-line bg-surface p-0.5 text-xs" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o}
          role="radio"
          aria-checked={value === o}
          onClick={() => onChange(o)}
          className={`min-w-9 rounded-full px-2.5 py-1 font-medium ${value === o ? "bg-ink text-bg" : "text-muted"}`}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
