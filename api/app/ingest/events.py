"""Upcoming events for tracked companies: what's coming, not just what happened.

  1. NSE event calendar      board meetings (results dates), one call for the whole market
  2. NSE corporate actions   dividend / bonus / split ex- and record dates, one call
  3. Forward-looking notices earnings calls, analyst meets, AGMs: dates read from the filing's text, or from the first
                             page of its PDF when the one-liner is generic ("Schedule of meet")

Deterministic: no model involved.
"""

from __future__ import annotations

import calendar
import hashlib
import logging
import re
from datetime import date, datetime, timedelta

from app.ingest import documents, http, store

log = logging.getLogger(__name__)
NSE = "https://www.nseindia.com/api"
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m} | {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
_MON = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ORD = r"(?:st|nd|rd|th)?"

# "18th and 19th November 2026", "16 November, 2026", "November 16, 2026", "16-11-2026", "16.11.2026"
_PATTERNS = [
    re.compile(rf"\b(\d{{1,2}}){_ORD}\s*(?:,|and|&|-|to)\s*(\d{{1,2}}){_ORD}\s+({_MON})\.?,?\s+(\d{{4}})", re.I),
    re.compile(rf"\b(\d{{1,2}}){_ORD}\s+({_MON})\.?,?\s+(\d{{4}})", re.I),
    re.compile(rf"\b({_MON})\.?\s+(\d{{1,2}}){_ORD},?\s+(\d{{4}})", re.I),
    re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b"),
]
_TIME = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(a\.?m\.?|p\.?m\.?|hrs|hours|ist)?", re.I)
_PAST = re.compile(r"\b(held on|was held|conducted on|transcript|recording|outcome of|audio|video recording|concluded)\b", re.I)
_FORWARD = re.compile(r"\b(will|shall|scheduled|schedule|intimation|participat|to be held|proposes?|upcoming|is fixed|has fixed|record date)\b", re.I)


def _d(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def find_dates(text: str) -> list[date]:
    """Every calendar date mentioned in the text, in order of appearance (ranges expanded to their days)."""
    found: list[tuple[int, date]] = []
    taken: list[tuple[int, int]] = []
    for i, pat in enumerate(_PATTERNS):
        for m in pat.finditer(text):
            if any(a <= m.start() < b for a, b in taken):
                continue
            g = m.groups()
            if i == 0:
                mon, yr = _MONTHS[g[2].lower()], int(g[3])
                days = [x for x in (_d(yr, mon, int(g[0])), _d(yr, mon, int(g[1]))) if x]
            elif i == 1:
                days = [x for x in [_d(int(g[2]), _MONTHS[g[1].lower()], int(g[0]))] if x]
            elif i == 2:
                days = [x for x in [_d(int(g[2]), _MONTHS[g[0].lower()], int(g[1]))] if x]
            else:
                days = [x for x in [_d(int(g[2]), int(g[1]), int(g[0]))] if x]
            if days:
                taken.append((m.start(), m.end()))
                found += [(m.start(), x) for x in days]
    return [x for _, x in sorted(found, key=lambda t: t[0])]


def find_time(text: str) -> str | None:
    for m in _TIME.finditer(text):
        h, mi, suffix = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower().replace(".", "")
        if suffix in ("pm",) and h < 12:
            h += 12
        if 7 <= h <= 21 and mi < 60 and (suffix or h >= 10):
            return f"{h:02d}:{mi:02d}"
    return None


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def _parse_nse_date(s: str | None) -> date | None:
    try:
        return datetime.strptime(s or "", "%d-%b-%Y").date()
    except ValueError:
        return None


def from_calendar(tracked: set[str]) -> list[dict]:
    r = http.get(f"{NSE}/event-calendar", params={"index": "equities"}, referer="https://www.nseindia.com/", accept="application/json")
    out = []
    for x in r.json() or []:
        d = _parse_nse_date(x.get("date"))
        if x.get("symbol") not in tracked or not d:
            continue
        purpose = (x.get("purpose") or "Board meeting").strip()
        kind = "results" if "result" in purpose.lower() else "board_meeting"
        title = {"results": "Results"}.get(kind, f"Board meeting: {purpose.lower()}")
        if kind == "results" and "dividend" in purpose.lower():
            title = "Results and dividend"
        out.append({"id": _id("cal", x["symbol"], d.isoformat(), purpose), "ticker": x["symbol"], "date": d.isoformat(), "end_date": None,
                    "time": None, "kind": kind, "title": title, "detail": (x.get("bm_desc") or "").strip() or None, "source": "NSE event calendar", "url": None})
    return out


def from_actions(tracked: set[str], days: int = 45) -> list[dict]:
    f, t = date.today(), date.today() + timedelta(days=days)
    r = http.get(f"{NSE}/corporates-corporateActions", params={"index": "equities", "from_date": f.strftime("%d-%m-%Y"), "to_date": t.strftime("%d-%m-%Y")},
                 referer="https://www.nseindia.com/", accept="application/json")
    out = []
    for x in r.json() or []:
        ex = _parse_nse_date(x.get("exDate"))
        if x.get("symbol") not in tracked or not ex:
            continue
        subject = (x.get("subject") or "Corporate action").strip()
        low = subject.lower()
        kind = "dividend" if "dividend" in low else "corporate_action"
        rec = _parse_nse_date(x.get("recDate"))
        out.append({"id": _id("ca", x["symbol"], ex.isoformat(), subject), "ticker": x["symbol"], "date": ex.isoformat(), "end_date": None, "time": None,
                    "kind": kind, "title": f"Ex-date: {subject}", "detail": f"Record date {rec:%d %b}" if rec else None, "source": "NSE corporate actions", "url": None})
    return out


_FILING_KIND = {"earnings_call": "earnings_call", "investor_meetings": "investor_meetings", "agm_egm": "agm", "dividend": "dividend", "bonus_split": "corporate_action"}
_FILING_TITLE = {"earnings_call": "Earnings call", "investor_meetings": "Analyst / investor meetings", "agm": "General meeting",
                 "dividend": "Dividend record date", "corporate_action": "Record date"}


def from_filings(con, tracked: set[str], lookback_days: int = 30, read_pdfs: bool = True) -> list[dict]:
    since = (date.today() - timedelta(days=lookback_days)).isoformat()
    marks = ",".join("?" * len(tracked))
    rows = con.execute(
        f"SELECT id, ticker, filed_at, nse_desc, text, attachment_url, category FROM announcements WHERE ticker IN ({marks}) AND filed_at >= ? "
        f"AND category IN ({','.join('?' * len(_FILING_KIND))})", (*tracked, since, *_FILING_KIND)).fetchall()
    out = []
    today = date.today()
    for r in rows:
        text = r["text"] or ""
        if _PAST.search(text) and not _FORWARD.search(text):
            continue  # a transcript or a recording link: the event is over
        filed = date.fromisoformat(r["filed_at"][:10])
        dates = [d for d in find_dates(text) if filed <= d <= filed + timedelta(days=120)]
        source_text = text
        if not dates and read_pdfs and r["attachment_url"]:
            try:
                documents.ingest(con, r["attachment_url"], ticker=r["ticker"], kind="filing", period=r["filed_at"][:10], title=r["nse_desc"], max_pages=2)
                source_text = documents.text(con, r["attachment_url"], max_pages=2)
                if _PAST.search(source_text[:600]) and not _FORWARD.search(source_text[:1500]):
                    continue
                dates = [d for d in find_dates(source_text) if filed < d <= filed + timedelta(days=120)]
            except http.FetchError as e:
                log.debug("event attachment %s: %s", r["attachment_url"], e)
        upcoming = sorted({d for d in dates if d >= today})
        if not upcoming:
            continue
        kind = _FILING_KIND[r["category"]]
        # Name the forum when the notice does ("CLSA India Forum", "Morgan Stanley conference").
        forum = re.search(r"((?:[A-Z][\w&.'-]+\s){1,5}(?:Forum|Conference|Summit|Investor Day|Analyst Day))", source_text)
        title = _FILING_TITLE[kind] + (f": {forum.group(1).strip()}" if forum and kind == "investor_meetings" else "")
        out.append({"id": _id("f", r["id"]), "ticker": r["ticker"], "date": upcoming[0].isoformat(),
                    "end_date": upcoming[-1].isoformat() if len(upcoming) > 1 and (upcoming[-1] - upcoming[0]).days <= 7 else None,
                    "time": find_time(source_text) if kind == "earnings_call" else None, "kind": kind, "title": title, "detail": None,
                    "source": "Exchange filing", "url": r["attachment_url"]})
    return out


def refresh(tracked: set[str]) -> int:
    """Rebuild upcoming events for the tracked companies. Each source is optional; one failing doesn't drop the others."""
    rows: list[dict] = []
    for name, fn in (("calendar", from_calendar), ("actions", from_actions)):
        try:
            rows += fn(tracked)
        except Exception as e:
            log.warning("events %s: %s", name, e)
    with store.connect() as con:
        try:
            rows += from_filings(con, tracked)
        except Exception as e:
            log.warning("events from filings: %s", e)
        # A results date in the calendar beats the same company's results notice; keep one per (ticker, date, kind).
        seen: set[tuple] = set()
        keep = []
        for r in sorted(rows, key=lambda r: r["source"] != "NSE event calendar"):
            k = (r["ticker"], r["date"], r["kind"])
            if k not in seen:
                seen.add(k)
                keep.append({**r, "updated_at": store.now_iso()})
        con.execute("DELETE FROM events WHERE date >= ?", (date.today().isoformat(),))
        store.upsert(con, "events", keep)
    return len(keep)


def upcoming(con, tickers: set[str], days: int = 14) -> list[dict]:
    today = date.today()
    marks = ",".join("?" * len(tickers))
    rows = con.execute(f"SELECT * FROM events WHERE ticker IN ({marks}) AND COALESCE(end_date, date) >= ? AND date <= ? ORDER BY date, time",
                       (*tickers, today.isoformat(), (today + timedelta(days=days)).isoformat())).fetchall()
    return [dict(r) for r in rows]

