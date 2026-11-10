"""End-of-day price & volume from Yahoo Finance (yfinance, `<TICKER>.NS`), plus move detection."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, time, timedelta, timezone

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
MARKET_CLOSE = time(15, 45)  # small buffer after the 15:30 close


# Benchmarks live in the same table under a friendly key.
BENCHMARKS = {"NIFTY50": "^NSEI"}


def yahoo_symbol(ticker: str) -> str:
    return BENCHMARKS.get(ticker, f"{ticker}.NS")


def fetch_eod(ticker: str, period: str = "5y") -> list[dict]:
    import yfinance as yf  # ~60 MB with pandas: loaded on first price fetch, not at startup

    h = yf.Ticker(yahoo_symbol(ticker)).history(period=period, interval="1d", auto_adjust=False)
    now = datetime.now(IST)
    rows = []
    for ts, r in h.iterrows():
        d = ts.date()
        if d == now.date() and now.time() < MARKET_CLOSE:
            continue  # today's bar is still forming — not end-of-day yet
        rows.append(
            {"ticker": ticker, "date": d.isoformat(), "open": float(r["Open"]), "high": float(r["High"]),
             "low": float(r["Low"]), "close": float(r["Close"]), "volume": int(r["Volume"])}
        )
    return rows


def detect_move(con: sqlite3.Connection, ticker: str, *, price_move_pct: float, volume_multiple: float, lookback: int) -> dict | None:
    """Latest completed session vs the investor's thresholds. Returns a signal dict only when something fires."""
    rows = con.execute(
        "SELECT date, close, volume FROM eod WHERE ticker=? ORDER BY date DESC LIMIT ?", (ticker, lookback + 1)
    ).fetchall()
    if len(rows) < 2:
        return None
    today, prev = rows[0], rows[1]
    change = (today["close"] / prev["close"] - 1) * 100 if prev["close"] else 0.0
    hist = [r["volume"] for r in rows[1:] if r["volume"]]
    avg = sum(hist) / len(hist) if hist else 0
    vmult = today["volume"] / avg if avg else None
    price_hit = abs(change) >= price_move_pct
    vol_hit = vmult is not None and vmult >= volume_multiple
    if not (price_hit or vol_hit):
        return None
    return {
        "ticker": ticker, "date": today["date"], "close": today["close"], "change_pct": round(change, 2),
        "volume_multiple": round(vmult, 2) if vmult else None, "price_hit": price_hit, "vol_hit": vol_hit,
        "lookback": len(hist),
    }
