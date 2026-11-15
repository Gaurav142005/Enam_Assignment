"use client";

import { Children, useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

/** Horizontal card deck: swipe on touch, arrows / keys on desktop. The next card peeks so the gesture is discoverable. */
export function SwipeDeck({ children, label }: { children: React.ReactNode; label: string }) {
  const slides = Children.toArray(children);
  const track = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const n = slides.length;

  const onScroll = useCallback(() => {
    const el = track.current;
    if (!el || !el.children.length) return;
    const first = el.children[0] as HTMLElement;
    const step = first.offsetWidth + 12;
    setIndex(Math.max(0, Math.min(n - 1, Math.round(el.scrollLeft / step))));
  }, [n]);

  const go = (i: number) => {
    const el = track.current;
    const target = el?.children[Math.max(0, Math.min(n - 1, i))] as HTMLElement | undefined;
    if (el && target) el.scrollTo({ left: target.offsetLeft - el.offsetLeft - 16, behavior: "smooth" });
  };

  useEffect(() => setIndex(0), [n]);

  // "At a glance" links point at #card-<id>: bring that card into the deck's view and the deck onto the screen.
  useEffect(() => {
    const onHash = () => {
      const el = track.current;
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!el || !id) return;
      const i = Array.from(el.children).findIndex((c) => c.querySelector(`[id="${CSS.escape(id)}"]`));
      if (i < 0) return;
      go(i);
      el.parentElement?.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    window.addEventListener("hashchange", onHash);
    onHash();
    return () => window.removeEventListener("hashchange", onHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [n]);

  if (!n) return null;
  return (
    <section aria-roledescription="carousel" aria-label={label} className="scroll-mt-4">
      <div className="mb-2 flex items-center justify-end gap-1 px-4">
        <span className="num mr-1 text-xs text-muted" aria-live="polite">
          {index + 1} / {n}
        </span>
        <button onClick={() => go(index - 1)} disabled={index === 0} aria-label="Previous" className="rounded-full border border-line bg-surface p-1 text-muted disabled:opacity-30">
          <ChevronLeft size={16} />
        </button>
        <button onClick={() => go(index + 1)} disabled={index === n - 1} aria-label="Next" className="rounded-full border border-line bg-surface p-1 text-muted disabled:opacity-30">
          <ChevronRight size={16} />
        </button>
      </div>
      <div
        ref={track}
        onScroll={onScroll}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") go(index + 1);
          if (e.key === "ArrowLeft") go(index - 1);
        }}
        className="no-scrollbar flex snap-x snap-mandatory items-stretch gap-3 overflow-x-auto scroll-smooth px-4 pb-1 outline-none"
      >
        {slides.map((s, i) => (
          <div key={i} role="group" aria-roledescription="slide" aria-label={`${i + 1} of ${n}`} className="w-[88%] shrink-0 snap-center">
            {s}
          </div>
        ))}
      </div>
      {n > 1 && n <= 14 && (
        <div className="mt-3 flex justify-center gap-1.5" aria-hidden>
          {slides.map((_, i) => (
            <button key={i} tabIndex={-1} onClick={() => go(i)} className={`h-1.5 rounded-full transition-all ${i === index ? "w-5 bg-ink" : "w-1.5 bg-line"}`} />
          ))}
        </div>
      )}
    </section>
  );
}
