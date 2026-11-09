import type { Category } from "./types";

export const CATEGORY_LABEL: Record<Category, string> = {
  results: "Results",
  management_change: "Management change",
  "M&A": "M&A",
  litigation: "Litigation",
  pledging: "Pledging",
  fund_raise: "Fund raise",
  capex: "Capex",
  credit_rating: "Credit rating",
  insider_trading: "Insider trading",
  press_release: "Press release",
  bonus_split: "Bonus / split",
  dividend: "Dividend",
  earnings_call: "Earnings call",
  investor_meetings: "Investor meetings",
  agm_egm: "AGM / EGM",
  postal_ballot: "Postal ballot",
  unclassified: "Routine filings",
};

export function ago(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins}m`;
  const h = Math.round(mins / 60);
  return h < 48 ? `${h}h` : `${Math.round(h / 24)}d`;
}

export function pct(n: number | null): string {
  if (n === null) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
}

export function crore(n: number): string {
  return n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function initials(name: string): string {
  return name.split(" ").map((w) => w[0]).slice(0, 2).join("");
}

export function windowLabel(hours: number): string {
  if (hours < 24) return `${hours}h`;
  const d = hours / 24;
  return d === 1 ? "24h" : `${d}d`;
}

/** "2015–2020", "2019–now", or "" when the source gives no years. */
export function tenure(start: number | null, end: number | null, open = true): string {
  if (start === null) return end === null ? "" : String(end);
  return `${start}–${end ?? (open ? "now" : "")}`;
}
