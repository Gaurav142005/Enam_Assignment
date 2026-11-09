"""Fundamentals signals from seeded statements (offline)."""

from app.ingest import store
from app.services import fundamentals


def _seed(ticker: str) -> None:
    fy = [f"Mar {y}" for y in range(2020, 2027)]
    rows = []

    def add(st, line, vals, periods=fy):
        rows.extend({"ticker": ticker, "statement": st, "line": line, "period": p, "value": v, "seq": i} for i, (p, v) in enumerate(zip(periods, vals)))

    add("profit-loss", "Sales", [100, 120, 144, 173, 207, 249, 299])  # ~20%/yr
    add("profit-loss", "Net Profit", [10, 13, 17, 22, 28, 36, 47])  # faster than sales
    add("profit-loss", "OPM %", [12, 12, 12, 12, 12, 12, 16])
    add("balance-sheet", "Equity Capital", [10] * 7)
    add("balance-sheet", "Reserves", [90] * 7)
    add("balance-sheet", "Borrowings", [5] * 7)
    add("cash-flow", "Cash from Operating Activity", [10, 12, 15, 20, 25, 30, 40])
    add("cash-flow", "Free Cash Flow", [2, 3, 4, 5, 6, 7, 8])
    with store.connect() as con:
        store.upsert(con, "financials", rows)
        store.upsert(con, "companies", [{"ticker": ticker, "name": "Test Co", "isin": None, "about": "Makes tests.", "ratios": {"Stock P/E": "20"},
                                         "screener_view": "consolidated", "updated_at": store.now_iso()}])


def test_signals_from_statements():
    _seed("FUNDCO")
    f = fundamentals.build("FUNDCO")
    texts = " | ".join(s.text for s in f.signals)
    assert "Revenue compounded 20% a year over 5 years" in texts
    assert any(s.tone == "positive" and "operating leverage" in s.text for s in f.signals)
    assert any("expanded to 16%" in s.text for s in f.signals)
    assert any(s.section == "balance_sheet" and "debt-free" in s.text for s in f.signals)
    assert not f.is_lender and any(m.label == "Debt / equity" for m in f.snapshot)
