"""Recent headlines per company, refreshed on demand (3h cache). Context only — never an input to research."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.ingest import news as news_src
from app.ingest import store
from app.models import NewsItem
from app.services import companies

log = logging.getLogger(__name__)
STALE_AFTER = timedelta(hours=3)


def _name(ticker: str) -> str:
    known = companies.known().get(ticker)
    if known and known.name != ticker:
        return known.name
    with store.connect() as con:
        row = con.execute("SELECT name FROM companies WHERE ticker=?", (ticker,)).fetchone()
    return row["name"] if row else ticker


def refresh(ticker: str) -> list[dict]:
    rows = news_src.fetch(ticker, _name(ticker))
    now = store.now_iso()
    with store.connect() as con:
        store.upsert(con, "news", [{**r, "fetched_at": now} for r in rows])
    return rows


def recent(ticker: str, limit: int = 12) -> list[NewsItem]:
    t = ticker.upper()
    with store.connect() as con:
        last = con.execute("SELECT MAX(fetched_at) FROM news WHERE ticker=?", (t,)).fetchone()[0]
    if not last or datetime.now(timezone.utc) - datetime.fromisoformat(last) > STALE_AFTER:
        try:
            refresh(t)
        except Exception as e:  # news is garnish; never break the page for it
            log.warning("news refresh %s failed: %s", t, e)
    with store.connect() as con:
        rows = con.execute(
            "SELECT title, source, url, published_at FROM news WHERE ticker=? ORDER BY published_at DESC LIMIT ?", (t, limit)
        ).fetchall()
    return [NewsItem(**dict(r)) for r in rows]
