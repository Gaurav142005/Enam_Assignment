"""Portfolio + research watchlist. Any NSE ticker resolves, not just the demo set."""

from __future__ import annotations

import json
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


def search(q: str, limit: int = 8) -> list[Company]:
    q = q.strip().lower()
    if not q:
        return []
    hits = [c for c in known().values() if q in c.ticker.lower() or q in c.name.lower()]
    if not any(c.ticker.lower() == q for c in hits):
        hits.append(Company(ticker=q.upper(), name=f"Research {q.upper()} on NSE", sector="—"))
    return hits[:limit]
