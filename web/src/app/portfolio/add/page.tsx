"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { BackLink } from "@/components/BackLink";
import { HoldingForm } from "@/components/HoldingForm";
import { PageHeader } from "@/components/PageHeader";
import { TickerBadge } from "@/components/TickerBadge";
import { api } from "@/lib/api";
import { rupees } from "@/lib/format";
import type { Company, PriceHistory } from "@/lib/types";

/** Add a holding: find any NSE company, enter shares and price. Its filings and prices are fetched in the background. */
export default function AddHoldingPage() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [pick, setPick] = useState<Company | null>(null);
  const [close, setClose] = useState<number | null>(null);

  useEffect(() => {
    if (pick || q.trim().length < 2) return setResults([]);
    const t = setTimeout(() => {
      api<Company[]>(`/pull/search?q=${encodeURIComponent(q)}`).then((r) => setResults(r.filter((c) => c.sector !== "—"))).catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(t);
  }, [q, pick]);

  useEffect(() => {
    if (!pick) return;
    setClose(null);
    api<PriceHistory>(`/market/prices/${pick.ticker}?range=1M`)
      .then((h) => setClose(h.bars.at(-1)?.close ?? null))
      .catch(() => setClose(null));
  }, [pick]);

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact title="Add a holding" sub="Any NSE-listed company" />

      {!pick ? (
        <div className="px-4">
          <label className="card flex items-center gap-2 px-3 py-2.5 focus-within:border-accent">
            <Search size={18} className="shrink-0 text-muted" />
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ticker or company name" aria-label="Search companies" className="w-full bg-transparent text-[15px] outline-none placeholder:text-muted" />
          </label>
          {results.length > 0 && (
            <ul className="card mt-3 divide-y divide-line">
              {results.map((c) => (
                <li key={c.ticker}>
                  <button onClick={() => setPick(c)} disabled={c.in_portfolio} className="flex w-full items-center gap-3 px-4 py-3 text-left active:bg-line/40 disabled:opacity-50">
                    <TickerBadge ticker={c.ticker} size={32} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium">{c.ticker}</span>
                      <span className="block truncate text-xs text-muted">{c.name}</span>
                    </span>
                    {c.in_portfolio && <span className="text-[11px] text-muted">Already held</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <section className="card mx-4 p-4">
          <div className="mb-4 flex items-center gap-3">
            <TickerBadge ticker={pick.ticker} />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold">{pick.ticker}</span>
              <span className="block truncate text-xs text-muted">
                {pick.name}
                {close ? ` · last close ${rupees(close)}` : ""}
              </span>
            </span>
            <button onClick={() => setPick(null)} className="text-xs text-accent">
              Change
            </button>
          </div>
          <HoldingForm
            ticker={pick.ticker}
            lastClose={close}
            onDone={() => {
              router.push("/portfolio");
              router.refresh();
            }}
          />
          <p className="mt-3 text-[11px] text-muted">FINN pulls its filings, prices, fundamentals and leadership in the background; it appears in the Brief within a minute or two.</p>
        </section>
      )}
    </main>
  );
}
