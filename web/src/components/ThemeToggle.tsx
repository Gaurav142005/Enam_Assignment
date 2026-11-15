"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { applyTheme, effectiveTheme, readTheme, THEME_EVENT, type ThemeChoice } from "@/lib/theme";

/** One-tap switch in the header: flips between light and dark (Settings also offers "match the device"). */
export function ThemeToggle() {
  const [mode, setMode] = useState<"light" | "dark" | null>(null);
  useEffect(() => {
    const sync = () => setMode(effectiveTheme(readTheme()));
    sync();
    window.addEventListener(THEME_EVENT, sync);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", sync);
    return () => {
      window.removeEventListener(THEME_EVENT, sync);
      mq.removeEventListener("change", sync);
    };
  }, []);
  if (!mode) return <span className="h-9 w-9" />;
  const next = mode === "dark" ? "light" : "dark";
  return (
    <button onClick={() => applyTheme(next)} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`} className="rounded-full p-2 text-muted active:bg-line/50">
      {mode === "dark" ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}

const OPTIONS: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
  { value: "system", label: "Device", icon: Monitor },
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
];

/** Full choice for Settings: match the device, or pin light / dark. */
export function ThemePicker() {
  const [choice, setChoice] = useState<ThemeChoice | null>(null);
  useEffect(() => {
    const sync = () => setChoice(readTheme());
    sync();
    window.addEventListener(THEME_EVENT, sync);
    return () => window.removeEventListener(THEME_EVENT, sync);
  }, []);
  return (
    <div className="card mx-4 grid grid-cols-3 gap-1 p-1" role="radiogroup" aria-label="Appearance">
      {OPTIONS.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          role="radio"
          aria-checked={choice === value}
          onClick={() => applyTheme(value)}
          className={`flex flex-col items-center gap-1 rounded-xl py-2.5 text-[13px] ${choice === value ? "bg-accent-soft font-semibold text-accent" : "text-muted"}`}
        >
          <Icon size={18} />
          {label}
        </button>
      ))}
    </div>
  );
}
