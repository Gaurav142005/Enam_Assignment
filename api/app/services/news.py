"""Recent headlines per company, refreshed on demand (3h cache). Context only — never an input to research."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from app.ingest import news as news_src
from app.ingest import store
from app.models import NewsItem
from app.services import companies

log = logging.getLogger(__name__)
STALE_AFTER = timedelta(hours=3)


# Not about the business: consumer service notices, personal stories, awards, market roundups.
_JUNK = re.compile(
    r"\b(bank holidays?|holiday|(?:car|home|personal|gold|education) loans?|which one offers|customers?|downtime|outage|net ?banking|stock price, news, quote|fd (?:interest )?rates?|interest rates? on|savings account|credit card|upi|branch(?:es)? (?:open|closed)|"
    r"prize|award(?:ed|s)?\b(?! (?:of )?(?:a |an |the )?(?:contract|order))|wins? .* (?:prize|award)|scholar|researchers?|"
    r"engineer|employee|arrested|heist|betting|murder|police|wedding|"
    r"stocks? to (?:buy|watch)|top picks|share price today live|sensex today|market live|trade setup|"
    r"mutual fund|flexi ?cap|fund (?:exits|buys|adds))\b",
    re.I,
)
# What moves a share price: numbers, deals, ratings, management, regulators, the stock itself.
_SIGNAL = re.compile(
    r"\b(results?|profit|revenue|earnings|margins?|guidance|q[1-4]|order|contract|deal|acqui\w+|merger|stake|block deal|"
    r"rating|upgrade|downgrade|target price|brokerage|buyback|dividend|ipo|fund ?rais\w*|qip|capex|expansion|"
    r"ceo|cfo|managing director|chairman|resign\w*|appoint\w*|re-appoint\w*|"
    r"rbi|sebi|penalty|probe|tax demand|lawsuit|court|ban|tariff|visa|"
    r"shares? (?:jump|surge|rise|rally|fall|slump|drop|sink|tumble|crash)\w*|stock (?:jumps|surges|falls|slumps|tumbles)|52-week)\b",
    re.I,
)
_ROUNDUP = re.compile(r"\b(and|&) (?:\d+|other \d+|\d+ other) (?:more|others|banks|stocks|companies)\b|\bother \d+\b|\b\d+ more\b", re.I)


def relevance(title: str) -> int:
    """-1 = drop; 0 = about the company; 1 = could matter to the share price."""
    if _JUNK.search(title):
        return -1
    if _ROUNDUP.search(title) or title.count(",") >= 3:
        return 0 if _SIGNAL.search(title) else -1
    return 1 if _SIGNAL.search(title) else 0


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


def recent(ticker: str, limit: int = 10) -> list[NewsItem]:
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
            "SELECT title, source, url, published_at FROM news WHERE ticker=? ORDER BY published_at DESC LIMIT 60", (t,)
        ).fetchall()
    # Price-relevant first, then the rest that's about the company; consumer notices and roundups are dropped.
    scored = [(relevance(r["title"]), i, r) for i, r in enumerate(rows)]
    keep = sorted((x for x in scored if x[0] >= 0), key=lambda x: (-x[0], x[1]))
    out: list[NewsItem] = []
    seen: list[set[str]] = []
    for _, _, r in keep:  # the same story from five outlets is one story
        words = {w for w in re.findall(r"[a-z0-9]+", r["title"].lower()) if len(w) > 3}
        if any(len(words & w) >= 0.5 * min(len(words), len(w)) for w in seen if w and words):
            continue
        seen.append(words)
        out.append(NewsItem(**dict(r)))
        if len(out) == limit:
            break
    return out
