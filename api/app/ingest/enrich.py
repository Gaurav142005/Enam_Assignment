"""Turn a raw filing into something the investor can act on without opening the PDF."""

from __future__ import annotations

import calendar
import html
import json
import logging
import re
import sqlite3
from datetime import date, datetime, timedelta

from app import llm

log = logging.getLogger(__name__)
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m} | {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}

# screener line names → headline metric. Lenders have no EBITDA; that row is simply omitted.
METRIC_LINES = {
    "Revenue": ["Sales", "Revenue"],
    "EBITDA": ["Operating Profit"],
    "PBT": ["Profit before tax"],
    "PAT": ["Net Profit"],
}


def fy_quarter(period: str) -> str:
    """'Sep 2026' → 'Q2 FY27' (Indian FY: Apr–Mar)."""
    mon, yr = period.split()
    m = MONTHS[mon.lower()]
    q = {6: 1, 9: 2, 12: 3, 3: 4}.get(m)
    fy = int(yr) + (1 if m >= 4 else 0)
    return f"Q{q} FY{fy % 100:02d}" if q else period


def _period_end(period: str) -> date | None:
    try:
        mon, yr = period.split()
        m, y = MONTHS[mon.lower()], int(yr)
        return date(y, m, calendar.monthrange(y, m)[1])
    except (ValueError, KeyError):
        return None


def _period_from_text(text: str) -> str | None:
    m = re.search(r"ended\s+(?:on\s+)?(?:\d{1,2}(?:st|nd|rd|th)?\s+)?([A-Za-z]{3,9})\.?\s*(?:\d{1,2}(?:st|nd|rd|th)?,?\s*)?(\d{4})", text, re.I)
    if m and m.group(1).lower() in MONTHS:
        return f"{calendar.month_abbr[MONTHS[m.group(1).lower()]]} {m.group(2)}"
    return None


def results_cut(con: sqlite3.Connection, ticker: str, filed_at: str, text: str) -> dict | None:
    """Headline numbers for the quarter this filing reports: value, QoQ %, YoY %."""
    rows = con.execute("SELECT line, period, value, seq FROM financials WHERE ticker=? AND statement='quarters'", (ticker,)).fetchall()
    if not rows:
        return None
    by_line: dict[str, dict[str, float | None]] = {}
    order: dict[str, int] = {}
    for r in rows:
        by_line.setdefault(r["line"], {})[r["period"]] = r["value"]
        order[r["period"]] = r["seq"]
    periods = sorted(order, key=order.get)  # oldest → newest

    filed = datetime.fromisoformat(filed_at).date()
    target = _period_from_text(text)
    if target not in order:
        # A quarter's results can't be out within ~9 days of it ending: a filing that early (e.g. a business update)
        # must not borrow numbers that weren't public yet.
        eligible = [p for p in periods if (e := _period_end(p)) and e + timedelta(days=9) <= filed]
        if not eligible:
            return None
        target = eligible[-1]
        if (e := _period_end(target)) and (filed - e).days > 75:
            return None  # the newest eligible quarter is stale: this filing isn't reporting it
    i = periods.index(target)
    prev = periods[i - 1] if i >= 1 else None
    mon, yr = target.split()
    yago = f"{mon} {int(yr) - 1}"

    def pct(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or b == 0:
            return None
        return round((a / b - 1) * 100 * (1 if b > 0 else -1), 1)

    out = []
    for metric, lines in METRIC_LINES.items():
        line = next((l for l in lines if l in by_line), None)
        if not line or by_line[line].get(target) is None:
            continue
        v = by_line[line]
        out.append({"metric": metric, "value": v[target], "qoq_pct": pct(v[target], v.get(prev)), "yoy_pct": pct(v[target], v.get(yago))})
    if not out:
        return None
    return {"period": fy_quarter(target), "unit": "₹ cr", "rows": out, "source": "screener.in quarterly (from exchange filings)"}


PEOPLE_SYSTEM = (
    "You read Indian listed-company filings about management changes. Extract every person whose role changes. "
    "Use ONLY the text provided; never add outside knowledge. "
    'Return JSON: {"people": [{"name": str, "role": str, "change": "appointed"|"resigned"|"retired"|"ceased"|"demise"|"redesignated"|"other", '
    '"effective_date": "YYYY-MM-DD"|null, "background": str|null (<=45 words, from the filing\'s brief profile), '
    '"previous_roles": [{"company": str, "title": str|null, "years": str|null}], "education": [str]}]}. '
    "Use an empty list if no person's role changes."
)

_NAME = re.compile(r"\b(?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+((?:[A-Z][A-Za-z'-]*\.?\s?){1,4})")
_NOT_NAME = {"managing", "director", "chief", "officer", "independent", "executive", "non", "whole", "time", "additional",
             "company", "bank", "limited", "ltd", "of", "the", "in", "as", "and", "mr", "ms", "mrs", "dr", "shri", "smt",
             "president", "head", "secretary", "chairman", "chairperson", "ceo", "cfo", "coo", "group", "senior"}
_CHANGE = [("demise", "demise"), ("resign", "resigned"), ("retire", "retired"), ("cessation", "ceased"),
           ("re-designat", "redesignated"), ("redesignat", "redesignated"), ("appoint", "appointed")]


def _clean_role(role: str) -> str | None:
    role = re.split(r"\s+(?:of the (?:company|bank|board)|w\.?e\.?f|with effect|effective|from|for a term|subject to)\b", role, flags=re.I)[0]
    role = " ".join(role.split()).strip(" -–")
    return role or None


def _regex_people(text: str) -> list[dict]:
    low = text.lower()
    change = next((c for k, c in _CHANGE if k in low), "other")
    found: dict[str, dict] = {}
    for m in _NAME.finditer(text):
        tokens = []
        for tok in m.group(1).split():
            if tok.lower().strip(".") in _NOT_NAME:
                break
            tokens.append(tok)
        name = " ".join(tokens).rstrip(".")
        if len(name.replace(".", "").replace(" ", "")) < 4:
            continue
        role_m = re.search(re.escape(m.group(1).strip()) + r"[^.\n]{0,40}?\bas\s+(?:the\s+)?([A-Z][^.,;\n]{3,60})", text)
        found.setdefault(name, {"name": name, "role": _clean_role(role_m.group(1)) if role_m else None, "change": change,
                                "effective_date": None, "background": None, "previous_roles": [], "education": []})
    # "Puri" and "V.N. Srivatsan" are the same people as "Leo Puri" and "V. N. Srivatsan": keep the fullest form.
    key = lambda n: set(re.sub(r"[.\s]+", " ", n.replace(".", ". ")).lower().split())
    names = sorted(found, key=lambda n: -len(key(n)))
    keep: list[str] = []
    for n in names:
        if not any(key(n) <= key(k) for k in keep):
            keep.append(n)
    return [found[n] for n in keep][:4]


_XBRL_FACT = re.compile(r'<in-capmkt:(\w+) contextRef="([^"]+)"[^>]*>([^<]*)</in-capmkt:\1>')


def people_from_xbrl(xml: str) -> list[dict]:
    """SEBI's structured change-in-management disclosure: exact names, roles, dates — no model needed."""
    by_ctx: dict[str, dict[str, str]] = {}
    for tag, ctx, val in _XBRL_FACT.findall(xml):
        m = re.search(r"ChangeInManagement(\d+)$", ctx)
        if m:
            by_ctx.setdefault(m.group(1), {})[tag] = html.unescape(" ".join(val.split()))
    people = []
    for f in by_ctx.values():
        name = f.get("NameOfDesignatedPerson")
        if not name:
            continue
        kind = (f.get("CategoryOfCessation") or f.get("TypeOfChange") or "").lower()
        change = next((c for k, c in _CHANGE if k in kind), "appointed" if "appoint" in kind else "other")
        background = next((v for t, v in f.items() if "Profile" in t or "Experience" in t), None)
        reason = next((v for t, v in f.items() if t.startswith("Reason")), None)
        people.append({
            "name": name, "role": f.get("DesignationOfDesignatedPerson"), "change": change,
            "effective_date": f.get("EffectiveDateOfReasonOfChange"),
            "background": background or (f"Reason given: {reason}" if reason else None),
            "previous_roles": [], "education": [],
        })
    return people


def people_from_filing(ann: dict, pdf_text: str, *, xbrl: str | None = None, use_llm: bool = True) -> tuple[list[dict], str]:
    """Who joined/left. Exact XBRL first; else the LLM reads the filing (SEBI requires a brief profile); regex last."""
    if xbrl and (people := people_from_xbrl(xbrl)):
        return people, "xbrl"
    if use_llm and llm.available() and pdf_text.strip():
        try:
            prompt = f"NSE summary: {ann['text']}\n\nFiling text:\n{pdf_text[:12000]}"
            out = llm.json_call("cheap", PEOPLE_SYSTEM, prompt)
            people = [p for p in out.get("people", []) if p.get("name")]
            return people, "llm"
        except llm.LLMError as e:
            log.warning("people extraction via LLM failed (%s); falling back to regex", e)
    return _regex_people(f"{ann['text']}\n{pdf_text[:4000]}"), "regex"


def store_people(con: sqlite3.Connection, ann: dict, people: list[dict], source: str) -> None:
    con.execute("DELETE FROM people_mentions WHERE announcement_id=?", (ann["id"],))
    for p in people:
        con.execute(
            "INSERT OR REPLACE INTO people_mentions VALUES (?,?,?,?,?,?,?,?)",
            (ann["id"], ann["ticker"], p["name"], p.get("role"), p.get("change"), p.get("effective_date"),
             json.dumps({k: p.get(k) for k in ("background", "previous_roles", "education")}), source),
        )
