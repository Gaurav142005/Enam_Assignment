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
  if (hours < 24) return `${hours} hours`;
  const d = hours / 24;
  return d === 1 ? "24 hours" : `${d} days`;
}

/** "2015–2020", "2019–now", or "" when the source gives no years. */
export function tenure(start: number | null, end: number | null, open = true): string {
  if (start === null) return end === null ? "" : String(end);
  return `${start}–${end ?? (open ? "now" : "")}`;
}

export function rupees(n: number | null, digits = 2): string {
  if (n === null) return "—";
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

/** Text tone for a signed change: darker ink steps, never the mark color. */
export function tone(n: number | null): string {
  if (n === null || n === 0) return "text-muted";
  return n > 0 ? "text-up-ink" : "text-down-ink";
}

export function compact(n: number): string {
  return n.toLocaleString("en-IN", { notation: "compact", maximumFractionDigits: 1 });
}

export function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/** Indian-style compact rupees: ₹11.78 Cr, ₹14.5 L, ₹8,450. */
export function inr(n: number | null, signed = false): string {
  if (n === null) return "—";
  const sign = n < 0 ? "−" : signed ? "+" : "";
  const a = Math.abs(n);
  const body = a >= 1e7 ? `${(a / 1e7).toFixed(2)} Cr` : a >= 1e5 ? `${(a / 1e5).toFixed(1)} L` : a.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  return `${sign}₹${body}`;
}

/** Value in a series' unit, for chart readouts. */
export function unitValue(v: number | null, unit: string): string {
  if (v === null) return "—";
  if (unit === "₹ cr") return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} cr`;
  if (unit === "%") return `${v.toFixed(1)}%`;
  if (unit === "x") return `${v.toFixed(2)}x`;
  if (unit === "days") return `${v.toFixed(0)} days`;
  return v.toLocaleString("en-IN");
}

/** Annual "Mar 2026" → "FY26"; quarterly "Sep 2026" → "Sep 26"; TTM stays. */
export function periodLabel(p: string, annual = true): string {
  if (annual && p.startsWith("Mar ") && p.length === 8) return `FY${p.slice(-2)}`;
  const m = p.match(/^([A-Z][a-z]{2}) (\d{4})$/);
  return m ? `${m[1]} ${m[2].slice(-2)}` : p;
}
