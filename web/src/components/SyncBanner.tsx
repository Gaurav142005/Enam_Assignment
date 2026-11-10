"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import type { HoldingRecord } from "@/lib/types";

/** While a newly added holding is being backfilled, say so, and refresh the page when it's done. */
export function SyncBanner({ initial }: { initial: string[] }) {
  const router = useRouter();
  const [syncing, setSyncing] = useState(initial);
  const was = useRef(initial.length);

  useEffect(() => {
    if (!syncing.length) return;
    const t = setInterval(async () => {
      try {
        const hs = (await fetch("/api/portfolio/holdings").then((r) => r.json())) as HoldingRecord[];
        const now = hs.filter((h) => h.syncing).map((h) => h.ticker);
        setSyncing(now);
        if (now.length < was.current) router.refresh();
        was.current = now.length;
      } catch {}
    }, 3000);
    return () => clearInterval(t);
  }, [syncing.length, router]);

  if (!syncing.length) return null;
  return (
    <p className="mx-4 mb-3 flex items-center gap-2 rounded-xl bg-accent-soft/60 px-3 py-2.5 text-[13px]" aria-live="polite">
      <Loader2 size={15} className="animate-spin text-accent" />
      Fetching filings and prices for {syncing.join(", ")}…
    </p>
  );
}
