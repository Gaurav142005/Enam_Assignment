"""The investor's thesis per company, and whether each new material filing supports or challenges it.

One batched cheap-model call per company per check; results are stored per (filing, thesis version), so a filing is
judged once against a given thesis. Editing the thesis re-checks the last 60 days.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta, timezone

from app import llm
from app.ingest import documents, store
from app.models import Thesis, ThesisCheck
from app.services.digest import headline

log = logging.getLogger(__name__)
MATERIAL = ("results", "M&A", "fund_raise", "management_change", "litigation", "capex", "credit_rating", "pledging", "insider_trading", "press_release")
_checking: set[str] = set()

SYSTEM = (
    "You check new stock-exchange filings against an equity investor's thesis on an Indian listed company. "
    "For each filing decide whether it supports the thesis, challenges it, or is not relevant to it (neutral). "
    "Judge only from the filing information given; never use outside knowledge. Be strict: routine items are neutral. "
    "`why`: one line (max 22 words) naming the specific fact from the filing that matters for the thesis. "
    'Return JSON: {"items": [{"id": str, "stance": "supports"|"challenges"|"neutral", "why": str}]}'
)


def _hash(text: str) -> str:
    return hashlib.sha1(text.strip().encode()).hexdigest()[:12]


def get(ticker: str) -> Thesis | None:
    with store.connect() as con:
        r = con.execute("SELECT * FROM theses WHERE ticker=?", (ticker.upper(),)).fetchone()
    return Thesis(ticker=r["ticker"], text=r["text"], updated_at=r["updated_at"], checking=r["ticker"] in _checking) if r else None


def all_theses() -> dict[str, Thesis]:
    with store.connect() as con:
        return {r["ticker"]: Thesis(ticker=r["ticker"], text=r["text"], updated_at=r["updated_at"]) for r in con.execute("SELECT * FROM theses")}


def save(ticker: str, text: str) -> Thesis:
    t = ticker.upper()
    with store.connect() as con:
        con.execute("INSERT OR REPLACE INTO theses VALUES (?,?,?)", (t, text.strip(), store.now_iso()))
    _checking.add(t)
    threading.Thread(target=_check_safely, args=(t,), name=f"thesis-{t}", daemon=True).start()
    return Thesis(ticker=t, text=text.strip(), updated_at=store.now_iso(), checking=True)


def delete(ticker: str) -> None:
    with store.connect() as con:
        con.execute("DELETE FROM theses WHERE ticker=?", (ticker.upper(),))


def _check_safely(ticker: str) -> None:
    try:
        check(ticker)
    except Exception:
        log.exception("thesis check %s failed", ticker)
    finally:
        _checking.discard(ticker)


def check(ticker: str, days: int = 60) -> int:
    """Judge material filings from the last `days` that haven't been judged against the current thesis. Returns how many."""
    th = get(ticker)
    if not th or not llm.available():
        return 0
    h = _hash(th.text)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with store.connect() as con:
        done = {r["announcement_id"] for r in con.execute("SELECT announcement_id FROM thesis_checks WHERE ticker=? AND thesis_hash=?", (ticker, h))}
        rows = [r for r in con.execute(
            f"SELECT * FROM announcements WHERE ticker=? AND filed_at>=? AND category IN ({','.join('?' * len(MATERIAL))}) ORDER BY filed_at DESC LIMIT 15",
            (ticker, since, *MATERIAL)) if r["id"] not in done and not json.loads(r["extra"] or "{}").get("routine")]
        # Results day brings 3–5 filings (outcome, press release, deck…): judge one per day and type.
        seen: set[tuple] = set()
        rows = [r for r in rows if not ((k := (r["filed_at"][:10], r["category"])) in seen or seen.add(k))]
        payload = []
        for r in rows[:10]:
            extra = json.loads(r["extra"] or "{}")
            item = {"id": r["id"], "date": r["filed_at"][:10], "type": r["category"], "headline": headline(r["text"], r["nse_desc"])}
            if r["summary"]:
                item["summary"] = r["summary"]
            if extra.get("results"):
                item["results"] = {x["metric"]: {"value_rs_cr": x["value"], "qoq_pct": x["qoq_pct"], "yoy_pct": x["yoy_pct"]} for x in extra["results"]["rows"]}
            if r["attachment_url"]:
                excerpt = documents.text(con, r["attachment_url"], max_pages=2)
                if excerpt:
                    item["excerpt"] = " ".join(excerpt.split())[:1200]
            payload.append(item)
    if not payload:
        return 0
    prompt = f"Company: {ticker}\nInvestor's thesis: {th.text}\n\nNew filings:\n{json.dumps(payload, ensure_ascii=False)}"
    try:
        out = llm.json_call("cheap", SYSTEM, prompt)
    except llm.LLMError as e:
        log.warning("thesis check %s: %s", ticker, e)
        return 0
    now = store.now_iso()
    rows_out = []
    ids = {p["id"] for p in payload}
    for x in llm.items(out):
        if x.get("id") in ids and x.get("stance") in ("supports", "challenges", "neutral"):
            rows_out.append({"announcement_id": x["id"], "ticker": ticker, "thesis_hash": h, "stance": x["stance"],
                             "why": (x.get("why") or "").strip()[:240], "created_at": now})
    with store.connect() as con:
        store.upsert(con, "thesis_checks", rows_out)
    return len(rows_out)


def checks_for(ticker: str, limit: int = 12) -> list[ThesisCheck]:
    th = get(ticker)
    if not th:
        return []
    with store.connect() as con:
        rows = con.execute(
            "SELECT c.*, a.filed_at, a.text, a.nse_desc, a.summary, a.attachment_url, a.category FROM thesis_checks c JOIN announcements a ON a.id=c.announcement_id "
            "WHERE c.ticker=? AND c.thesis_hash=? AND c.stance != 'neutral' ORDER BY a.filed_at DESC LIMIT ?", (ticker.upper(), _hash(th.text), limit)).fetchall()
    seen: set[tuple] = set()
    out = []
    for r in rows:
        if (k := (r["filed_at"][:10], r["category"])) in seen:
            continue  # one verdict per results day, not one per filing that day
        seen.add(k)
        out.append(ThesisCheck(announcement_id=r["announcement_id"], stance=r["stance"], why=r["why"], date=r["filed_at"][:10],
                               title=r["summary"] or headline(r["text"], r["nse_desc"]), url=r["attachment_url"]))
    return out


def lookup(ids: list[str]) -> dict[str, ThesisCheck]:
    """Current-thesis verdicts for these announcements (for the Brief)."""
    if not ids:
        return {}
    theses = {t: _hash(th.text) for t, th in all_theses().items()}
    if not theses:
        return {}
    with store.connect() as con:
        rows = con.execute(f"SELECT * FROM thesis_checks WHERE announcement_id IN ({','.join('?' * len(ids))})", ids).fetchall()
    return {r["announcement_id"]: ThesisCheck(announcement_id=r["announcement_id"], stance=r["stance"], why=r["why"])
            for r in rows if theses.get(r["ticker"]) == r["thesis_hash"] and r["stance"] != "neutral"}


def check_all() -> int:
    """After a refresh: judge any new material filings for every company with a thesis."""
    return sum(check(t) for t in all_theses())
