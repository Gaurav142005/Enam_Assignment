"""Period returns from seeded EOD rows (no network)."""

from datetime import date, timedelta

from app.ingest import store
from app.services import market


def _seed(ticker: str, closes: list[float], end: date) -> None:
    rows = [
        {"ticker": ticker, "date": (end - timedelta(days=len(closes) - 1 - i)).isoformat(), "open": c, "high": c, "low": c, "close": c, "volume": 100}
        for i, c in enumerate(closes)
    ]
    with store.connect() as con:
        store.upsert(con, "eod", rows)


def test_period_returns():
    end = date(2026, 11, 6)
    _seed("TESTCO", [100.0] * 30 + [110.0, 121.0], end)  # flat for a month, then +10%, +10%
    with store.connect() as con:
        day, _, asof, close = market._period_return(con, "TESTCO", "1D")
        week, spark, _, _ = market._period_return(con, "TESTCO", "1W")
    assert (asof, close, day) == ("2026-11-06", 121.0, 10.0)
    assert week == 21.0 and spark[-1] == 121.0


def test_missing_history_is_none():
    with store.connect() as con:
        assert market._period_return(con, "NOPE", "1M") == (None, [], None, None)
