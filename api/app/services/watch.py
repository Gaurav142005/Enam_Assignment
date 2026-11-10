"""The 'push' in Push: keep the portfolio's filings and prices fresh without being asked.

`refresh_portfolio()` re-pulls announcements + EOD for every holding (fundamentals, news and leadership refresh lazily
elsewhere). It runs on a timer while the API is up (FINN_AUTO_REFRESH_MIN, default 15; 0 disables) and on demand from
the Brief's refresh button. One run at a time.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from app import config, llm, state
from app.ingest import store
from app.ingest.pipeline import ingest_company
from app.services import companies

log = logging.getLogger(__name__)
_lock = threading.Lock()
_status: dict = {"running": False, "done": 0, "total": 0, "errors": 0}


def status() -> dict:
    return {**_status, "refreshed_at": state.get("refreshed_at")}


def refresh_portfolio() -> None:
    if not _lock.acquire(blocking=False):
        return
    try:
        tickers = [c.ticker for c in companies.portfolio()]
        _status.update(running=True, done=0, total=len(tickers), errors=0)
        use_llm = llm.available()
        for t in tickers:
            rep = ingest_company(t, days=30, with_documents=False, use_llm=use_llm, only={"prices", "filings"}, say=lambda m: None)
            _status["done"] += 1
            _status["errors"] += bool(rep.errors)
        try:
            from app.ingest import events

            events.refresh({c.ticker for c in [*companies.portfolio(), *companies.watchlist()]})
        except Exception:
            log.exception("events refresh failed")
        try:
            from app.services import thesis

            thesis.check_all()
        except Exception:
            log.exception("thesis checks failed")
        state.put("refreshed_at", store.now_iso())
    except Exception:  # a failed refresh must never take the API down
        log.exception("portfolio refresh failed")
    finally:
        _status["running"] = False
        _lock.release()


def start_refresh() -> dict:
    if not _status["running"]:
        threading.Thread(target=refresh_portfolio, name="refresh", daemon=True).start()
        _status["running"] = True
    return status()


def start_auto() -> None:
    minutes = config.AUTO_REFRESH_MIN
    if minutes <= 0:
        return

    def stale() -> bool:
        last = state.get("refreshed_at")
        return not last or datetime.now(timezone.utc) - datetime.fromisoformat(last) > timedelta(minutes=minutes)

    def loop() -> None:
        while True:
            time.sleep(60)  # check every minute; refresh only when the data is older than the interval
            try:
                if store.has_data() and stale():  # never surprise a fresh clone with a crawl; the investor ingests first
                    refresh_portfolio()
            except Exception:
                log.exception("auto-refresh check failed")

    threading.Thread(target=loop, name="auto-refresh", daemon=True).start()
