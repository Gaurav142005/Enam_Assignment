"use client";

import { useEffect, useState } from "react";
import { BackLink } from "@/components/BackLink";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { api, apiPut } from "@/lib/api";
import { CATEGORY_LABEL } from "@/lib/format";
import type { AlertRules, Category } from "@/lib/types";

/** The investor decides what "unusual" and "material" mean; FINN watches for it. */
export default function SettingsPage() {
  const [rules, setRules] = useState<AlertRules | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<AlertRules>("/push/rules").then(setRules);
  }, []);

  if (!rules) return <PageHeader title="Alerts" sub="Loading…" />;

  const save = async (next: AlertRules) => {
    setRules(next);
    setSaved(false);
    await apiPut("/push/rules", next);
    setSaved(true);
  };
  const toggle = (c: Category) =>
    save({ ...rules, categories: rules.categories.includes(c) ? rules.categories.filter((x) => x !== c) : [...rules.categories, c] });

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact title="Alerts" sub={saved ? "Saved. The Brief now uses these." : "You decide what counts as unusual; FINN watches for it."} />

      <SectionTitle>End-of-day triggers</SectionTitle>
      <div className="card mx-4 divide-y divide-line">
        <Stepper label="Price move beyond" unit="%" value={rules.price_move_pct} step={0.5} min={1} onChange={(v) => save({ ...rules, price_move_pct: v })} />
        <Stepper label="Volume above" unit="× avg" value={rules.volume_multiple} step={0.5} min={1} onChange={(v) => save({ ...rules, volume_multiple: v })} />
      </div>

      <p className="mx-4 mt-2 text-[11px] text-muted">Checked against each end-of-day close. Volume is compared with its 20-day average.</p>

      <SectionTitle>Announcement types I care about</SectionTitle>
      <div className="flex flex-wrap gap-2 px-4">
        {(Object.keys(CATEGORY_LABEL) as Category[]).map((c) => {
          const on = rules.categories.includes(c);
          return (
            <button
              key={c}
              onClick={() => toggle(c)}
              aria-pressed={on}
              className={`rounded-full border px-3 py-1.5 text-[13px] ${on ? "border-ink bg-ink text-bg" : "border-line bg-surface text-muted"}`}
            >
              {CATEGORY_LABEL[c]}
            </button>
          );
        })}
      </div>

    </main>
  );
}

function Stepper(props: { label: string; unit: string; value: number; step: number; min: number; onChange: (v: number) => void }) {
  const { label, unit, value, step, min, onChange } = props;
  const btn = "h-8 w-8 rounded-full border border-line text-lg leading-none active:bg-line/50";
  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm">
      <span>{label}</span>
      <span className="flex items-center gap-3">
        <button className={btn} onClick={() => onChange(Math.max(min, value - step))} aria-label={`Decrease ${label}`}>−</button>
        <span className="num w-16 text-center">
          {value} {unit}
        </span>
        <button className={btn} onClick={() => onChange(value + step)} aria-label={`Increase ${label}`}>+</button>
      </span>
    </div>
  );
}
