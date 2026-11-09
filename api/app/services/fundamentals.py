"""Fundamentals for Pull: snapshot, trajectory, balance sheet, cash quality, shareholding.

Deterministic on purpose. These sections are arithmetic over standardised statements (screener.in,
compiled from annual reports and exchange filings), so no model is involved and every sentence
carries its own numbers. The LLM is reserved for what arithmetic can't do: narrative vs numbers,
guidance, bull/bear (read from transcripts).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from app.ingest import store
from app.ingest.pipeline import ingest_fundamentals
from app.models import Fundamentals, Metric, Point, Series, Signal

log = logging.getLogger(__name__)
STALE_AFTER = timedelta(hours=24)

# screener line aliases: non-lenders | lenders
ALIASES = {
    "revenue": ["Sales", "Revenue"],
    "op_profit": ["Operating Profit", "Financing Profit"],
    "margin": ["OPM %", "Financing Margin %"],
    "pat": ["Net Profit"],
    "eps": ["EPS in Rs"],
    "borrowings": ["Borrowings", "Borrowing"],
}


def ensure(ticker: str) -> bool:
    """Fundamentals for any NSE ticker: fetch from screener if missing or older than a day."""
    with store.connect() as con:
        row = con.execute("SELECT updated_at FROM companies WHERE ticker=?", (ticker,)).fetchone()
    if row and datetime.now(timezone.utc) - datetime.fromisoformat(row["updated_at"]) < STALE_AFTER:
        return True
    try:
        ingest_fundamentals(ticker)
        return True
    except Exception as e:
        log.warning("fundamentals %s: %s", ticker, e)
        return row is not None


class _Book:
    """statement → line → period → value, plus period order."""

    def __init__(self, rows):
        self.v: dict[str, dict[str, dict[str, float | None]]] = {}
        self.order: dict[str, list[str]] = {}
        seqs: dict[str, dict[str, int]] = {}
        for r in rows:
            self.v.setdefault(r["statement"], {}).setdefault(r["line"], {})[r["period"]] = r["value"]
            seqs.setdefault(r["statement"], {})[r["period"]] = r["seq"]
        self.order = {st: sorted(p, key=p.get) for st, p in seqs.items()}

    def line(self, st: str, key: str) -> dict[str, float | None]:
        lines = self.v.get(st, {})
        for name in ALIASES.get(key, [key]):
            if name in lines:
                return lines[name]
        return {}

    def fy(self, st: str) -> list[str]:
        return [p for p in self.order.get(st, []) if p.startswith("Mar ")]

    def series(self, st: str, key: str, name: str, unit, periods: list[str] | None = None) -> Series:
        d = self.line(st, key)
        ps = periods if periods is not None else self.order.get(st, [])
        return Series(key=key, name=name, unit=unit, points=[Point(period=p, value=d.get(p)) for p in ps])


def _cagr(a: float | None, b: float | None, years: int) -> float | None:
    if not a or not b or a <= 0 or b <= 0 or years <= 0:
        return None
    return ((b / a) ** (1 / years) - 1) * 100


def _cr(n: float | None) -> str:
    if n is None:
        return "—"
    return f"₹{n:,.0f} cr" if abs(n) < 1_00_000 else f"₹{n / 1_00_000:,.2f} lakh cr"


def _fy(p: str) -> str:
    return f"FY{p[-2:]}" if p.startswith("Mar ") else p


def build(ticker: str) -> Fundamentals | None:
    t = ticker.upper()
    if not ensure(t):
        return None
    with store.connect() as con:
        c = con.execute("SELECT * FROM companies WHERE ticker=?", (t,)).fetchone()
        rows = con.execute("SELECT statement, line, period, value, seq FROM financials WHERE ticker=?", (t,)).fetchall()
    if not c or not rows:
        return None
    b = _Book(rows)
    ratios = json.loads(c["ratios"] or "{}")
    is_lender = "Financing Profit" in b.v.get("profit-loss", {}) or "Deposits" in b.v.get("balance-sheet", {})
    fy = b.fy("profit-loss")[-11:]
    signals: list[Signal] = []

    # ── annual series ──
    equity = {p: (b.line("balance-sheet", "Equity Capital").get(p) or 0) + (b.line("balance-sheet", "Reserves").get(p) or 0)
              for p in b.order.get("balance-sheet", [])}
    borrow = b.line("balance-sheet", "borrowings")
    de = {p: (borrow.get(p) or 0) / equity[p] if equity.get(p) else None for p in equity}
    pl_periods = fy + (["TTM"] if "TTM" in b.order.get("profit-loss", []) else [])
    annual = [
        b.series("profit-loss", "revenue", "Revenue", "₹ cr", pl_periods),
        b.series("profit-loss", "op_profit", "Financing profit" if is_lender else "EBITDA", "₹ cr", pl_periods),
        b.series("profit-loss", "margin", "Financing margin" if is_lender else "EBITDA margin", "%", fy),
        b.series("profit-loss", "pat", "Net profit", "₹ cr", pl_periods),
        b.series("cash-flow", "Cash from Operating Activity", "Cash from operations", "₹ cr", fy),
        b.series("cash-flow", "Free Cash Flow", "Free cash flow", "₹ cr", fy),
        b.series("balance-sheet", "borrowings", "Borrowings", "₹ cr", fy),
        Series(key="equity", name="Net worth", unit="₹ cr", points=[Point(period=p, value=equity.get(p)) for p in fy]),
    ]
    if not is_lender:
        annual += [
            Series(key="de", name="Debt / equity", unit="x", points=[Point(period=p, value=round(de[p], 2) if de.get(p) is not None else None) for p in fy]),
            b.series("ratios", "ROCE %", "ROCE", "%", fy),
            b.series("ratios", "Working Capital Days", "Working-capital days", "days", fy),
            b.series("ratios", "Cash Conversion Cycle", "Cash conversion cycle", "days", fy),
        ]
    else:
        annual += [b.series("balance-sheet", "Deposits", "Deposits", "₹ cr", fy), b.series("ratios", "ROE %", "ROE", "%", fy)]

    qp = b.order.get("quarters", [])[-8:]
    quarterly = [
        b.series("quarters", "revenue", "Revenue", "₹ cr", qp),
        b.series("quarters", "op_profit", "Financing profit" if is_lender else "EBITDA", "₹ cr", qp),
        b.series("quarters", "margin", "Margin", "%", qp),
        b.series("quarters", "pat", "Net profit", "₹ cr", qp),
    ]
    if is_lender:
        quarterly += [b.series("quarters", "Gross NPA %", "Gross NPA", "%", qp), b.series("quarters", "Net NPA %", "Net NPA", "%", qp)]

    sp = b.order.get("shareholding", [])[-12:]
    holders = [("Promoters", "Promoters"), ("FIIs", "Foreign institutions"), ("DIIs", "Domestic institutions"), ("Government", "Government")]
    shareholding = [b.series("shareholding", k, n, "%", sp) for k, n in holders if k in b.v.get("shareholding", {})][:3]

    # ── signals: trajectory ──
    rev, pat, mar = b.line("profit-loss", "revenue"), b.line("profit-loss", "pat"), b.line("profit-loss", "margin")
    last = fy[-1] if fy else None
    for yrs in (5, 3):
        if last and len(fy) > yrs:
            start = fy[-1 - yrs]
            r_c, p_c = _cagr(rev.get(start), rev.get(last), yrs), _cagr(pat.get(start), pat.get(last), yrs)
            if r_c is not None:
                signals.append(Signal(section="trajectory", tone="positive" if r_c >= 12 else "negative" if r_c < 5 else "neutral",
                                      text=f"Revenue compounded {r_c:.0f}% a year over {yrs} years ({_cr(rev.get(start))} in {_fy(start)} → {_cr(rev.get(last))} in {_fy(last)})."))
                if p_c is not None:
                    gap = p_c - r_c
                    if gap >= 3:
                        signals.append(Signal(section="trajectory", tone="positive", text=f"Profit grew faster than revenue ({p_c:.0f}% vs {r_c:.0f}% a year): operating leverage is showing."))
                    elif gap <= -3:
                        signals.append(Signal(section="trajectory", tone="negative", text=f"Profit lagged revenue ({p_c:.0f}% vs {r_c:.0f}% a year): margins have been squeezed."))
            break
    if not is_lender and last and len(fy) >= 4:
        prior = [mar.get(p) for p in fy[-4:-1] if mar.get(p) is not None]
        if prior and mar.get(last) is not None:
            avg, now = sum(prior) / len(prior), mar[last]
            if abs(now - avg) >= 1.5:
                signals.append(Signal(section="trajectory", tone="positive" if now > avg else "negative",
                                      text=f"EBITDA margin {'expanded' if now > avg else 'compressed'} to {now:.0f}% in {_fy(last)}, against a {avg:.0f}% average over the prior three years."))
            else:
                signals.append(Signal(section="trajectory", tone="neutral", text=f"EBITDA margin steady at {now:.0f}% ({_fy(last)}), in line with the prior three years."))
    qrev, qpat = b.line("quarters", "revenue"), b.line("quarters", "pat")
    if len(qp) >= 5:
        lq, yq = qp[-1], qp[-5]
        rg, pg = _cagr(qrev.get(yq), qrev.get(lq), 1), _cagr(qpat.get(yq), qpat.get(lq), 1)
        if rg is not None and pg is not None:
            signals.append(Signal(section="trajectory", tone="positive" if rg > 10 and pg > 10 else "negative" if rg < 0 or pg < 0 else "neutral",
                                  text=f"Latest quarter ({lq}): revenue {rg:+.0f}% and net profit {pg:+.0f}% year on year."))

    # ── signals: balance sheet ──
    bs_last = b.order.get("balance-sheet", [])[-1:] or [None]
    bl = bs_last[0]
    if bl and not is_lender:
        d = de.get(bl)
        if d is not None:
            tone = "positive" if d < 0.3 else "negative" if d > 1 else "neutral"
            label = "effectively debt-free" if d < 0.1 else "low leverage" if d < 0.3 else "moderate leverage" if d <= 1 else "high leverage"
            signals.append(Signal(section="balance_sheet", tone=tone, text=f"Debt/equity {d:.2f}x as of {bl} ({label}): borrowings {_cr(borrow.get(bl))} against net worth {_cr(equity.get(bl))}."))
        wc = b.line("ratios", "Working Capital Days")
        if last and len(fy) >= 4 and wc.get(last) is not None and wc.get(fy[-4]) is not None:
            delta = wc[last] - wc[fy[-4]]
            if abs(delta) >= 10:
                signals.append(Signal(section="balance_sheet", tone="negative" if delta > 0 else "positive",
                                      text=f"Working-capital days {'rose' if delta > 0 else 'fell'} from {wc[fy[-4]]:.0f} to {wc[last]:.0f} over three years: {'more' if delta > 0 else 'less'} cash tied up in operations."))
        cwip, fa = b.line("balance-sheet", "CWIP").get(bl), b.line("balance-sheet", "Fixed Assets").get(bl)
        if cwip and fa and cwip / fa >= 0.2:
            signals.append(Signal(section="balance_sheet", tone="neutral", text=f"Capital work-in-progress is {cwip / fa * 100:.0f}% of fixed assets ({_cr(cwip)}): meaningful capacity is still being built."))
    elif bl and is_lender:
        dep = b.line("balance-sheet", "Deposits")
        if len(fy) >= 4 and dep.get(fy[-1]) and dep.get(fy[-4]):
            signals.append(Signal(section="balance_sheet", tone="neutral", text=f"Deposits grew {_cagr(dep[fy[-4]], dep[fy[-1]], 3):.0f}% a year over three years to {_cr(dep[fy[-1]])}."))
        gnpa = b.line("quarters", "Gross NPA %")
        if len(qp) >= 5 and gnpa.get(qp[-1]) is not None and gnpa.get(qp[-5]) is not None:
            ch = gnpa[qp[-1]] - gnpa[qp[-5]]
            signals.append(Signal(section="balance_sheet", tone="negative" if ch > 0.1 else "positive" if ch < -0.1 else "neutral",
                                  text=f"Gross NPA {gnpa[qp[-1]]:.2f}% in {qp[-1]}, {'up' if ch > 0 else 'down'} {abs(ch):.2f} pts year on year."))

    # ── signals: cash quality ──
    if not is_lender and len(fy) >= 5:
        cfo, fcf = b.line("cash-flow", "Cash from Operating Activity"), b.line("cash-flow", "Free Cash Flow")
        win = fy[-5:]
        sc, sp_ = sum(cfo.get(p) or 0 for p in win), sum(pat.get(p) or 0 for p in win)
        if sp_ > 0:
            ratio = sc / sp_
            signals.append(Signal(section="cash_quality", tone="positive" if ratio >= 0.9 else "negative" if ratio < 0.7 else "neutral",
                                  text=f"Over five years, operating cash flow was {ratio:.0%} of reported profit ({_cr(sc)} vs {_cr(sp_)}): profits {'are' if ratio >= 0.9 else 'are mostly' if ratio >= 0.7 else 'are not'} turning into cash."))
        sf = sum(fcf.get(p) or 0 for p in win)
        signals.append(Signal(section="cash_quality", tone="positive" if sf > 0 else "negative",
                              text=f"Cumulative free cash flow over five years: {_cr(sf)}{' after funding capex' if sf > 0 else ', so growth has needed outside funding'}."))

    # ── signals: shareholding ──
    for s in shareholding:
        vals = [(p.period, p.value) for p in s.points if p.value is not None]
        if len(vals) >= 5:
            (p0, v0), (p1, v1) = vals[-5], vals[-1]
            if abs(v1 - v0) >= 0.5:
                tone = "neutral" if s.key != "Promoters" else ("positive" if v1 > v0 else "negative")
                signals.append(Signal(section="shareholding", tone=tone, text=f"{s.name} {'raised' if v1 > v0 else 'cut'} their stake from {v0:.1f}% to {v1:.1f}% ({p0} → {p1})."))

    # ── snapshot ──
    keys = ("Market Cap", "Stock P/E", "ROE", "Dividend Yield", "High / Low") if is_lender else ("Market Cap", "Stock P/E", "ROCE", "ROE", "Dividend Yield", "High / Low")
    snap = [Metric(label=k, value=ratios[k].replace("₹ ", "₹").replace(" Cr.", " cr").replace(" %", "%")) for k in keys if k in ratios]
    if not is_lender and bl and de.get(bl) is not None:
        snap.insert(3, Metric(label="Debt / equity", value=f"{de[bl]:.2f}x"))
    if "TTM" in b.order.get("profit-loss", []):
        snap.insert(1, Metric(label="Revenue (TTM)", value=_cr(rev.get("TTM"))))
        snap.insert(2, Metric(label="Net profit (TTM)", value=_cr(pat.get("TTM"))))
    for m in snap:
        m.label = {"Market Cap": "Market cap", "Stock P/E": "P/E", "High / Low": "52-week range", "Dividend Yield": "Dividend yield"}.get(m.label, m.label)

    view = c["screener_view"] or "consolidated"
    return Fundamentals(
        ticker=t, name=c["name"], is_lender=is_lender, view=view, about=c["about"],
        source_url=f"https://www.screener.in/company/{t}/{'consolidated/' if view == 'consolidated' else ''}",
        updated_at=c["updated_at"], snapshot=snap, annual=annual, quarterly=quarterly, shareholding=shareholding, signals=signals,
    )
