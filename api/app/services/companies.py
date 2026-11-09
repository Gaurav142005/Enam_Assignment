"""Portfolio + research watchlist. Any NSE ticker resolves, not just the demo set."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.models import Company

DATA = Path(__file__).resolve().parent.parent / "data" / "portfolio.json"


@lru_cache
def _load() -> tuple[list[Company], list[Company]]:
    raw = json.loads(DATA.read_text())
    pick = lambda c: {k: c[k] for k in ("ticker", "name", "sector")}  # noqa: E731
    portfolio = [Company(**pick(c), in_portfolio=True) for c in raw["portfolio"]]
    watch = [Company(**pick(c)) for c in raw["research_watchlist"]]
    return portfolio, watch


def portfolio() -> list[Company]:
    return _load()[0]


@lru_cache
def positions() -> dict[str, dict]:
    """ticker → {qty, avg_cost, bought}. Separate from Company: holdings are the investor's, not the company's."""
    raw = json.loads(DATA.read_text())
    return {c["ticker"]: {k: c.get(k) for k in ("qty", "avg_cost", "bought")} for c in raw["portfolio"] if c.get("qty")}


def watchlist() -> list[Company]:
    return _load()[1]


def known() -> dict[str, Company]:
    return {c.ticker: c for c in [*watchlist(), *portfolio()]}


def resolve(ticker: str) -> Company:
    """Known ticker → its record. Unknown ticker → a bare record; research still runs on it."""
    t = ticker.upper().removesuffix(".NS")
    return known().get(t) or Company(ticker=t, name=t, sector="—")


def search(q: str, limit: int = 10) -> list[Company]:
    """Any NSE-listed company by ticker or name. Ranking: exact ticker → ticker prefix → name word-prefix → substring."""
    from app.ingest.people_sources import nse_listing

    q = q.strip()
    if not q:
        return []
    ql = q.lower()
    mine = known()
    pool: dict[str, Company] = {c.ticker: c for c in mine.values()}
    for sym, name in nse_listing():
        pool.setdefault(sym, Company(ticker=sym, name=name, sector="NSE listed"))

    def rank(c: Company) -> int | None:
        t, n = c.ticker.lower(), c.name.lower()
        if t == ql:
            return 0
        if t.startswith(ql):
            return 1
        if any(w.startswith(ql) for w in re.split(r"[^a-z0-9]+", n)) or n.startswith(ql):
            return 2
        if ql in n:
            return 3
        return None

    hits = [(r, c) for c in pool.values() if (r := rank(c)) is not None]
    hits.sort(key=lambda x: (x[0], x[1].ticker not in mine, len(x[1].name)))
    out = [c for _, c in hits[:limit]]
    if not out and re.fullmatch(r"[A-Za-z0-9&-]{2,20}", q):
        out = [Company(ticker=q.upper(), name=f"Research {q.upper()} on NSE", sector="—")]
    return out
