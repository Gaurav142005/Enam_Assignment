"""Portfolio + research watchlist. Any NSE ticker resolves, not just the demo set."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.models import Company

DATA = Path(__file__).resolve().parent.parent / "data" / "portfolio.json"


@lru_cache
def _watchlist() -> list[Company]:
    raw = json.loads(DATA.read_text())
    return [Company(ticker=c["ticker"], name=c["name"], sector=c["sector"]) for c in raw["research_watchlist"]]


_cache: list[dict] | None = None


def invalidate() -> None:
    global _cache
    _cache = None


def demo_holdings() -> list[dict]:
    raw = json.loads(DATA.read_text())
    return [{"ticker": c["ticker"], "name": c["name"], "sector": c["sector"], "qty": c.get("qty") or 0, "avg_cost": c.get("avg_cost"),
             "bought": c.get("bought"), "added_at": None} for c in raw["portfolio"]]


def holdings() -> list[dict]:
    """The investor's holdings, in the order they were added. Seeded from the demo portfolio the first time."""
    global _cache
    if _cache is None:
        from app.ingest import store

        with store.connect() as con:
            rows = [dict(r) for r in con.execute("SELECT * FROM holdings ORDER BY added_at IS NOT NULL, added_at, rowid")]
            if not rows and not con.execute("SELECT 1 FROM settings WHERE key='holdings_seeded'").fetchone():
                rows = demo_holdings()
                store.upsert(con, "holdings", rows)
                con.execute("INSERT OR REPLACE INTO settings VALUES ('holdings_seeded', 'true', ?)", (store.now_iso(),))
        _cache = rows
    return _cache


def portfolio() -> list[Company]:
    return [Company(ticker=h["ticker"], name=h["name"], sector=h["sector"] or "—", in_portfolio=True) for h in holdings()]


def positions() -> dict[str, dict]:
    """ticker → {qty, avg_cost, bought}. Separate from Company: holdings are the investor's, not the company's."""
    return {h["ticker"]: {k: h.get(k) for k in ("qty", "avg_cost", "bought")} for h in holdings() if h.get("qty")}


def watchlist() -> list[Company]:
    held = {h["ticker"] for h in holdings()}
    return [c for c in _watchlist() if c.ticker not in held]


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


# Coarse peer groups from the sector labels: enough to answer "who do I know at a competitor?"
_GROUPS: dict[str, tuple[str, ...]] = {
    "lending": ("lending", "bank", "finance", "microfinance", "nbfc"),
    "chemicals": ("chemical", "agrochem"),
    "IT services": ("it services", "software"),
    "consumer": ("consumer", "retail", "paint", "jewel"),
    "electricals & electronics": ("cables", "electric", "electronics", "semiconductor"),
    "autos": ("auto",),
    "pharma": ("pharma",),
    "industrials": ("engineering", "defence", "construction", "conglomerate"),
}


def group_of(ticker: str) -> str | None:
    c = known().get(ticker)
    if not c:
        return None
    low = c.sector.lower()
    return next((g for g, keys in _GROUPS.items() if any(k in low for k in keys)), None)


def peers(ticker: str) -> list[Company]:
    g = group_of(ticker)
    return [c for c in known().values() if g and c.ticker != ticker and group_of(c.ticker) == g]


def group_keywords(group: str) -> tuple[str, ...]:
    return _GROUPS.get(group, ())
