"""Add, edit and remove holdings. A new holding is backfilled in the background (fundamentals, 5 years of prices,
90 days of filings, news, leadership) so it shows up in the Brief and the Portfolio within a minute."""

from __future__ import annotations

import logging
import re
import threading
from datetime import date

from app import llm
from app.ingest import store
from app.ingest.people_sources import nse_listing
from app.models import HoldingIn, HoldingRecord
from app.services import companies, graph

log = logging.getLogger(__name__)
_syncing: set[str] = set()
_lock = threading.Lock()
_SUFFIX = re.compile(r"\s+(limited|ltd\.?)$", re.I)


class HoldingError(ValueError):
    pass


def _listed(ticker: str) -> str | None:
    """NSE company name for a symbol, or None if it isn't listed."""
    return next((name for sym, name in nse_listing() if sym == ticker), None)


def _last_close(ticker: str) -> float | None:
    with store.connect() as con:
        r = con.execute("SELECT close FROM eod WHERE ticker=? ORDER BY date DESC LIMIT 1", (ticker,)).fetchone()
    return r["close"] if r else None


def records() -> list[HoldingRecord]:
    with store.connect() as con:
        have = {r["ticker"] for r in con.execute("SELECT DISTINCT ticker FROM eod")}
    return [HoldingRecord(**h, syncing=h["ticker"] in _syncing, has_data=h["ticker"] in have) for h in companies.holdings()]


def _sync(ticker: str) -> None:
    from app.ingest.pipeline import ingest_company
    from app.services import market

    try:
        market.ensure_prices(ticker, force=True)
        ingest_company(ticker, days=90, with_documents=False, use_llm=llm.available(), say=lambda m: None)
        sector = _sector(ticker)
        if sector:
            with store.connect() as con:
                con.execute("UPDATE holdings SET sector=? WHERE ticker=? AND (sector IS NULL OR sector IN ('', '—'))", (sector, ticker))
            companies.invalidate()
    except Exception:
        log.exception("backfill for %s failed", ticker)
    finally:
        _syncing.discard(ticker)
        graph.invalidate()


def _sector(ticker: str) -> str | None:
    try:
        import yfinance as yf

        info = yf.Ticker(f"{ticker}.NS").info or {}
        return info.get("industry") or info.get("sector")
    except Exception:
        return None


def add(body: HoldingIn) -> HoldingRecord:
    t = body.ticker.strip().upper().removesuffix(".NS")
    if any(h["ticker"] == t for h in companies.holdings()):
        raise HoldingError(f"{t} is already in your portfolio. Edit it instead.")
    known = next((c for c in [*companies.portfolio(), *companies.watchlist()] if c.ticker == t), None)
    name = known.name if known else _listed(t)
    if not name:
        raise HoldingError(f"{t} isn't an NSE-listed symbol.")
    name = _SUFFIX.sub("", name).strip()
    avg = body.avg_cost or _last_close(t)
    avg = round(avg, 2) if avg else None
    row = {"ticker": t, "name": name, "sector": known.sector if known else "—", "qty": body.qty, "avg_cost": avg,
           "bought": (body.bought or date.today()).isoformat(), "added_at": store.now_iso()}
    with store.connect() as con:
        store.upsert(con, "holdings", [row])
    companies.invalidate()
    graph.invalidate()
    with _lock:
        _syncing.add(t)
    threading.Thread(target=_sync_then_price, args=(t, body.avg_cost is None), name=f"sync-{t}", daemon=True).start()
    return HoldingRecord(**row, syncing=True, has_data=False)


def _sync_then_price(ticker: str, fill_cost: bool) -> None:
    _sync(ticker)
    if fill_cost:  # no price given and we had none yet: use the latest close once it's fetched
        close = _last_close(ticker)
        if close:
            with store.connect() as con:
                con.execute("UPDATE holdings SET avg_cost=? WHERE ticker=? AND avg_cost IS NULL", (round(close, 2), ticker))
            companies.invalidate()


def update(ticker: str, body: HoldingIn) -> HoldingRecord:
    t = ticker.upper()
    if not any(h["ticker"] == t for h in companies.holdings()):
        raise KeyError(t)
    with store.connect() as con:
        con.execute("UPDATE holdings SET qty=?, avg_cost=COALESCE(?, avg_cost), bought=COALESCE(?, bought) WHERE ticker=?",
                    (body.qty, body.avg_cost, body.bought.isoformat() if body.bought else None, t))
    companies.invalidate()
    return next(r for r in records() if r.ticker == t)


def remove(ticker: str) -> None:
    t = ticker.upper()
    with store.connect() as con:
        if con.execute("DELETE FROM holdings WHERE ticker=?", (t,)).rowcount == 0:
            raise KeyError(t)
    companies.invalidate()
    graph.invalidate()


def reset() -> list[HoldingRecord]:
    """Back to the demo portfolio (for a shared public demo that visitors have edited)."""
    with store.connect() as con:
        con.execute("DELETE FROM holdings")
        store.upsert(con, "holdings", companies.demo_holdings())
    companies.invalidate()
    graph.invalidate()
    return records()
