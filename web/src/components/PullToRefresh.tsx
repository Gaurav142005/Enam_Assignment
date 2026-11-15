"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, useTransition } from "react";
import { RefreshCw } from "lucide-react";

const TRIGGER = 64; // px of (damped) pull that counts as "refresh"

/** Pull down at the top of the page to re-fetch it. Touch only; desktop keeps the refresh button. */
export function PullToRefresh({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [pull, setPull] = useState(0);
  const from = useRef<number | null>(null);

  const height = pending ? 44 : pull;
  return (
    <div
      onTouchStart={(e) => {
        from.current = window.scrollY <= 0 && !pending ? e.touches[0].clientY : null;
      }}
      onTouchMove={(e) => {
        if (from.current === null) return;
        const dy = e.touches[0].clientY - from.current;
        setPull(dy > 0 ? Math.min(dy * 0.5, 96) : 0);
      }}
      onTouchEnd={() => {
        if (pull >= TRIGGER) start(() => router.refresh());
        from.current = null;
        setPull(0);
      }}
    >
      <div
        aria-hidden={!pending}
        className={`flex items-end justify-center overflow-hidden ${from.current === null ? "transition-[height] duration-300 ease-out" : ""}`}
        style={{ height }}
      >
        <span className={`mb-2 flex size-8 items-center justify-center rounded-full bg-surface text-accent shadow ring-1 ring-line ${pull >= TRIGGER || pending ? "" : "text-muted"}`}>
          <RefreshCw size={16} className={pending ? "animate-spin" : ""} style={pending ? undefined : { transform: `rotate(${pull * 3}deg)` }} />
        </span>
        {pending && <span className="sr-only" role="status">Refreshing</span>}
      </div>
      {children}
    </div>
  );
}
