"""Inspect what the ingestion pipeline has stored for a company (debugging + the Pull phase builds on this)."""

import json

from fastapi import APIRouter, HTTPException

from app.ingest import store

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/{ticker}")
def company_data(ticker: str) -> dict:
    t = ticker.upper()
    with store.connect() as con:
        c = con.execute("SELECT * FROM companies WHERE ticker=?", (t,)).fetchone()
        if not c:
            raise HTTPException(404, f"{t} not ingested — run: uv run python -m app.ingest {t}")
        quarters = con.execute(
            "SELECT period, line, value FROM financials WHERE ticker=? AND statement='quarters' ORDER BY seq", (t,)
        ).fetchall()
        q: dict[str, dict] = {}
        for r in quarters:
            q.setdefault(r["line"], {})[r["period"]] = r["value"]
        last_px = con.execute("SELECT * FROM eod WHERE ticker=? ORDER BY date DESC LIMIT 1", (t,)).fetchone()
        n_px = con.execute("SELECT COUNT(*) FROM eod WHERE ticker=?", (t,)).fetchone()[0]
        cats = con.execute(
            "SELECT category, category_source, COUNT(*) n FROM announcements WHERE ticker=? GROUP BY 1, 2 ORDER BY n DESC", (t,)
        ).fetchall()
        recent = con.execute(
            "SELECT filed_at, category, nse_desc, text, summary, attachment_url, extra FROM announcements WHERE ticker=? ORDER BY filed_at DESC LIMIT 15", (t,)
        ).fetchall()
        docs = con.execute("SELECT kind, period, title, pages, url FROM documents WHERE ticker=? AND pages IS NOT NULL ORDER BY kind, rowid", (t,)).fetchall()
        listed = con.execute("SELECT kind, COUNT(*) FROM documents WHERE ticker=? GROUP BY kind", (t,)).fetchall()
        people = con.execute("SELECT name, role, change, effective_date, background, source FROM people_mentions WHERE ticker=?", (t,)).fetchall()
    return {
        "company": {k: (json.loads(c[k]) if k == "ratios" else c[k]) for k in c.keys()},
        "quarters": q,
        "prices": {"sessions": n_px, "last": dict(last_px) if last_px else None},
        "announcements": {
            "by_category": [dict(r) for r in cats],
            "recent": [{**dict(r), "extra": json.loads(r["extra"] or "{}")} for r in recent],
        },
        "documents": {"listed": {k: n for k, n in listed}, "fetched": [dict(r) for r in docs]},
        "people_mentions": [{**dict(r), "background": json.loads(r["background"] or "{}")} for r in people],
    }
