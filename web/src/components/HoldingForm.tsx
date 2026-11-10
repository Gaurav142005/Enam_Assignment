"use client";

import { useState } from "react";
import { apiDelete, apiPost, apiPutJson } from "@/lib/api";
import { inr } from "@/lib/format";
import type { HoldingRecord } from "@/lib/types";

const field = "w-full rounded-xl border border-line bg-bg px-3 py-2.5 text-[15px] outline-none placeholder:text-muted focus:border-accent";

/** Add or edit one holding. Average price defaults to the last close; the buy date to today. */
export function HoldingForm({
  ticker,
  existing,
  lastClose,
  onDone,
  onCancel,
}: {
  ticker: string;
  existing?: { qty: number; avg_cost: number | null; bought: string | null } | null;
  lastClose?: number | null;
  onDone: (h: HoldingRecord | null) => void;
  onCancel?: () => void;
}) {
  const [qty, setQty] = useState(existing ? String(existing.qty) : "");
  const [price, setPrice] = useState(existing?.avg_cost ? String(existing.avg_cost) : lastClose ? lastClose.toFixed(2) : "");
  const [bought, setBought] = useState(existing?.bought ?? new Date().toISOString().slice(0, 10));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const q = Number(qty);
  const p = Number(price);
  const valid = Number.isInteger(q) && q > 0 && (!price || p > 0);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    setBusy(true);
    setError(null);
    const body = { ticker, qty: q, avg_cost: price ? p : null, bought: bought || null };
    try {
      onDone(existing ? await apiPutJson<HoldingRecord>(`/portfolio/holdings/${ticker}`, body) : await apiPost<HoldingRecord>("/portfolio/holdings", body));
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm(`Remove ${ticker} from your portfolio?`)) return;
    setBusy(true);
    try {
      await apiDelete(`/portfolio/holdings/${ticker}`);
      onDone(null);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-muted">
          Shares
          <input className={`${field} mt-1`} inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value.replace(/[^\d]/g, ""))} placeholder="e.g. 500" required autoFocus />
        </label>
        <label className="text-xs text-muted">
          Avg price (₹)
          <input className={`${field} mt-1`} inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^\d.]/g, ""))} placeholder={lastClose ? lastClose.toFixed(2) : "last close"} />
        </label>
      </div>
      <label className="flex items-center justify-between gap-3 text-xs text-muted">
        Bought on
        <input type="date" max={new Date().toISOString().slice(0, 10)} className={`${field} w-auto`} value={bought} onChange={(e) => setBought(e.target.value)} />
      </label>
      {valid && q > 0 && (p || lastClose) ? (
        <p className="text-xs text-muted">
          Cost {inr(q * (p || lastClose || 0))}
          {lastClose ? ` · worth ${inr(q * lastClose)} at the last close` : ""}
        </p>
      ) : null}
      {error && <p className="text-sm text-down-ink">{error}</p>}
      <div className="flex items-center gap-2">
        <button type="submit" disabled={!valid || busy} className="flex-1 rounded-full bg-ink py-2.5 text-sm font-medium text-bg disabled:opacity-40">
          {busy ? "Saving…" : existing ? "Save" : "Add to portfolio"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="rounded-full border border-line px-4 py-2.5 text-sm">
            Cancel
          </button>
        )}
      </div>
      {existing && (
        <button type="button" onClick={remove} disabled={busy} className="w-full text-center text-xs font-medium text-down-ink">
          Remove from portfolio
        </button>
      )}
    </form>
  );
}
