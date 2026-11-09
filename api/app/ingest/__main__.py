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
    print(f"DB: {config.DB_PATH}")
    print(f"LLM: {f'{config.LLM_PROVIDER} ({config.CHEAP_MODEL} / {config.STRONG_MODEL})' if llm_on else 'off — rules only'}")
    failed = 0
    for t in dict.fromkeys(tickers):
        rep = ingest_company(t, days=a.days, with_documents=not a.light, use_llm=llm_on)
        failed += bool(rep.errors)
    print(f"\nDone: {len(set(tickers)) - failed} ok, {failed} with errors.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
