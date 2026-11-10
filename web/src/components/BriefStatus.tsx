"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ago } from "@/lib/format";

type Status = { running: boolean; done: number; total: number; refreshed_at: string | null };

/** Freshness line for the Brief: when FINN last checked the exchange, a manual refresh, and the 'seen' bookmark. */
export function BriefStatus({ refreshedAt, newCount, live }: { refreshedAt: string | null; newCount: number; live: boolean }) {
  const router = useRouter();
  const [status, setStatus] = useState<Status | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Mark the Brief as seen a few seconds after it's on screen, so "New" means new since the last real look.
  useEffect(() => {
    if (!live) return;
    const t = setTimeout(() => fetch("/api/push/seen", { method: "POST" }).catch(() => {}), 4000);
    return () => clearTimeout(t);
  }, [live, refreshedAt]);

  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);

  const poll = () => {
    timer.current = setTimeout(async () => {
      const s = (await fetch("/api/push/refresh").then((r) => r.json())) as Status;
      setStatus(s);
      if (s.running) poll();
      else router.refresh();
    }, 1500);
  };

  const refresh = async () => {
    setStatus((await fetch("/api/push/refresh", { method: "POST" }).then((r) => r.json())) as Status);
    poll();
  };

  if (!live) return null;
  const running = status?.running;
  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      {newCount > 0 && <span className="rounded-full bg-accent px-2 py-0.5 font-semibold text-bg">{newCount} new</span>}
      <span aria-live="polite">
        {running ? `Checking the exchange… ${status.done}/${status.total}` : refreshedAt ? `Checked ${ago(refreshedAt)} ago` : "Not refreshed yet"}
      </span>
      <button onClick={refresh} disabled={running} aria-label="Refresh filings and prices" className="rounded-full p-1.5 text-muted active:bg-line/50 disabled:opacity-50">
        <RefreshCw size={14} className={running ? "animate-spin" : ""} />
      </button>
    </div>
  );
}
