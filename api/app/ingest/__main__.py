"""CLI: uv run python -m app.ingest POLYCAB [DIXON ...] | --portfolio | --watchlist  [--light] [--no-llm] [--days N]"""

from __future__ import annotations

import argparse
import logging
import sys

from app import config, llm
from app.ingest.pipeline import ingest_company
from app.services import companies


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m app.ingest", description="Ingest market data, filings and documents for NSE companies.")
    ap.add_argument("tickers", nargs="*", help="NSE symbols, e.g. POLYCAB DIXON")
    ap.add_argument("--portfolio", action="store_true", help="all portfolio companies")
    ap.add_argument("--watchlist", action="store_true", help="all research-list companies")
    ap.add_argument("--days", type=int, default=90, help="announcement look-back (default 90)")
    ap.add_argument("--light", action="store_true", help="skip transcript / annual-report downloads")
    ap.add_argument("--no-llm", action="store_true", help="rules only, no model calls")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="    %(levelname)s %(message)s")

    tickers = [t.upper() for t in a.tickers]
    if a.portfolio:
        tickers += [c.ticker for c in companies.portfolio()]
    if a.watchlist:
        tickers += [c.ticker for c in companies.watchlist()]
    if not tickers:
        ap.print_help()
        return 1

    llm_on = not a.no_llm and llm.available()
    if llm_on and not llm.probe():
        print(f"LLM: unusable ({llm._disabled}) — continuing rules-only")
        llm_on = False
    print(f"DB: {config.DB_PATH}")
    print(f"LLM: {f'{config.LLM_PROVIDER} ({config.CHEAP_MODEL} / {config.STRONG_MODEL})' if llm_on else 'off — rules only'}")
    failed = 0
    if a.portfolio:
        from app.services import market

        market.ensure_prices("NIFTY50", force=True)
        print("\n▶ NIFTY50 benchmark refreshed")
    for t in dict.fromkeys(tickers):
        rep = ingest_company(t, days=a.days, with_documents=not a.light, use_llm=llm_on)
        failed += bool(rep.errors)
    if a.portfolio and failed < len(set(tickers)):
        from app import state
        from app.ingest import events, store

        n = events.refresh({c.ticker for c in [*companies.portfolio(), *companies.watchlist()]})
        print(f"▶ {n} upcoming events")
        state.put("refreshed_at", store.now_iso())
    print(f"\nDone: {len(set(tickers)) - failed} ok, {failed} with errors.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
