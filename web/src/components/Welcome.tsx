"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, Newspaper, Sparkles, Users, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { LogoMark } from "./Logo";

const KEY = "finn.welcomed";
export const WELCOME_EVENT = "finn:welcome";

type Step = { icon: LucideIcon; tint: string; eyebrow: string; title: string; body: string; example: string };

const STEPS: Step[] = [
  {
    icon: Newspaper,
    tint: "bg-tint-peach text-tint-peach-ink",
    eyebrow: "Brief",
    title: "What changed, ranked",
    body: "Every NSE filing for your holdings, filtered to the ones that can move a price. Your portfolio against the Nifty, and what's coming up.",
    example: "Swipe the cards. Tap one to read the filing's numbers.",
  },
  {
    icon: Sparkles,
    tint: "bg-tint-sky text-tint-sky-ink",
    eyebrow: "Ask",
    title: "Research from the source",
    body: "Ask about any listed company. Answers come from filings, results and transcripts, and every claim links back to the document.",
    example: "Try: “Why did Trent's margins fall?”",
  },
  {
    icon: Users,
    tint: "bg-tint-mint text-tint-mint-ink",
    eyebrow: "Network",
    title: "Who can explain it",
    body: "Your LinkedIn connections, mapped onto the companies you own. When something moves, FINN shows who to call.",
    example: "Look for “Talk to …” under a card.",
  },
];

function read(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return true; // storage blocked: don't nag on every page
  }
}

/** First-run intro: three screens, once per device. Settings can reopen it. */
export function Welcome() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const touch = useRef<number | null>(null);

  useEffect(() => {
    if (!read()) setOpen(true);
    const reopen = () => {
      setStep(0);
      setOpen(true);
    };
    window.addEventListener(WELCOME_EVENT, reopen);
    return () => window.removeEventListener(WELCOME_EVENT, reopen);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") setStep((s) => Math.min(STEPS.length - 1, s + 1));
      if (e.key === "ArrowLeft") setStep((s) => Math.max(0, s - 1));
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  const close = () => {
    try {
      localStorage.setItem(KEY, "1");
    } catch {}
    setOpen(false);
  };

  if (!open) return null;
  const last = step === STEPS.length - 1;

  return (
    <div role="dialog" aria-modal="true" aria-label="Welcome to FINN" className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 backdrop-blur-sm animate-fade-in sm:items-center">
      <div
        className="relative w-full max-w-app overflow-hidden rounded-t-3xl bg-bg pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl animate-sheet-up sm:rounded-3xl"
        onTouchStart={(e) => (touch.current = e.touches[0].clientX)}
        onTouchEnd={(e) => {
          if (touch.current === null) return;
          const dx = e.changedTouches[0].clientX - touch.current;
          touch.current = null;
          if (dx < -40) setStep((s) => Math.min(STEPS.length - 1, s + 1));
          if (dx > 40) setStep((s) => Math.max(0, s - 1));
        }}
      >
        <div className="flex items-center justify-between px-5 pt-5">
          <span className="inline-flex items-center gap-2">
            <LogoMark size={26} />
            <span className="font-display text-[15px] font-bold tracking-[0.12em]">FINN</span>
          </span>
          <button onClick={close} aria-label="Skip the intro" className="-mr-2 rounded-full p-2 text-muted active:bg-line/50">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-hidden">
          <div className="flex transition-transform duration-300 ease-out motion-reduce:transition-none" style={{ transform: `translateX(-${step * 100}%)` }}>
            {STEPS.map((s, i) => (
              <section key={s.eyebrow} aria-hidden={i !== step} className="w-full shrink-0 px-5 pt-6">
                <span className={`inline-flex size-12 items-center justify-center rounded-2xl ${s.tint}`}>
                  <s.icon size={24} />
                </span>
                <p className="eyebrow mt-4">
                  {i + 1} of {STEPS.length} · {s.eyebrow}
                </p>
                <h2 className="mt-1 font-display text-[26px] font-semibold leading-tight tracking-tight">{s.title}</h2>
                <p className="mt-2 text-[15px] leading-relaxed text-ink/80">{s.body}</p>
                <p className="mt-3 rounded-xl bg-surface px-3 py-2.5 text-[13px] text-muted ring-1 ring-line">{s.example}</p>
              </section>
            ))}
          </div>
        </div>

        <div className="mt-6 flex items-center justify-center gap-1.5" aria-hidden>
          {STEPS.map((s, i) => (
            <span key={s.eyebrow} className={`h-1.5 rounded-full transition-all duration-300 ${i === step ? "w-5 bg-accent" : "w-1.5 bg-line"}`} />
          ))}
        </div>

        <div className="mt-5 flex gap-2 px-5">
          {last ? (
            <>
              <Link href="/company/RELIANCE" onClick={close} className="flex-1 rounded-full border border-line bg-surface py-3 text-center text-sm font-medium active:opacity-70">
                Try a company
              </Link>
              <button onClick={close} className="flex-1 rounded-full bg-accent py-3 text-sm font-medium text-bg active:opacity-80">
                Open my Brief
              </button>
            </>
          ) : (
            <>
              <button onClick={close} className="rounded-full px-4 py-3 text-sm font-medium text-muted active:opacity-70">
                Skip
              </button>
              <button onClick={() => setStep(step + 1)} className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-accent px-6 py-3 text-sm font-medium text-bg active:opacity-80">
                Next <ArrowRight size={16} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** For Settings: "Show the intro again". */
export function ReplayWelcome() {
  return (
    <button onClick={() => window.dispatchEvent(new Event(WELCOME_EVENT))} className="card mx-4 flex w-[calc(100%-2rem)] items-center justify-between px-4 py-3 text-left text-sm active:opacity-70">
      Show the intro again
      <ArrowRight size={16} className="text-muted" />
    </button>
  );
}
