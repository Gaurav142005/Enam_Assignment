"""People at listed companies: management + board, merged across public sources and kept current with filings.

  1. Yahoo Finance officers        → current management (title, birth year)
  2. NSE corporate-governance XBRL → the board as of the last governance filing
  3. Management-change filings     → joiners and leavers since then (ingested announcements)

Then matched against the investor's network: is this person a connection, and who can reach them?
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from app.ingest import store
from app.ingest.people_sources import clean_name, fetch_board, fetch_officers, name_key, same_person
from app.models import CompanyPeopleSummary, CompanyPerson, NetworkHint, Person, Position
from app.services import companies, graph
from app.services.filing_people import _change

log = logging.getLogger(__name__)
STALE_AFTER = timedelta(days=7)
LEFT = {"resigned", "retired", "ceased", "demise"}


def _pid(ticker: str, key: str) -> str:
    return f"c-{ticker}-{re.sub(r'[^a-z0-9]+', '-', key)}"


def _kind(role: str) -> str:
    r = role.lower()
    if "independent" in r:
        return "independent"
    if "non-executive" in r or "nominee" in r:
        return "director"
    return "executive"


def refresh(ticker: str) -> int:
    t = ticker.upper()
    merged: dict[str, dict] = {}
    as_of = None
    try:
        board, as_of = fetch_board(t)
    except Exception as e:  # each source is optional
        log.warning("board %s: %s", t, e)
        board = []
    try:
        officers = fetch_officers(t)
    except Exception as e:
        log.warning("officers %s: %s", t, e)
        officers = []
    for src in (board, officers):
        for p in src:
            k = _match_key(p["name"], merged)
            cur = merged.setdefault(k, {"name": p["name"], "role": p["role"], "board": False, "sources": [], "since": None, "year_born": None})
            if len(p["name"]) > len(cur["name"]):
                cur["name"] = p["name"]  # keep the fullest spelling
            if p["source"].startswith("NSE"):
                cur["board"] = True
            else:  # an officer title is more specific than a board category
                cur["role"] = p["role"]
            cur["since"] = cur["since"] or p.get("since")
            cur["year_born"] = cur["year_born"] or p.get("year_born")
            if p["source"] not in cur["sources"]:
                cur["sources"].append(p["source"])
    for v in merged.values():
        if v["board"] and "Yahoo Finance officers" in v["sources"] and not re.search(r"director|\bmd\b|chair", v["role"], re.I):
            v["role"] += " · Board member"
    now = store.now_iso()
    rows = [{"id": _pid(t, k), "ticker": t, "name": v["name"], "name_key": k, "role": v["role"], "kind": _kind(v["role"]),
             "status": "current", "since": v["since"], "year_born": v["year_born"], "sources": v["sources"], "as_of": as_of, "updated_at": now}
            for k, v in merged.items()]
    if rows:
        with store.connect() as con:
            con.execute("DELETE FROM company_people WHERE ticker=?", (t,))
            store.upsert(con, "company_people", rows)
    return len(rows)


def _match_key(name: str, merged: dict) -> str:
    """Find an existing entry for the same person (initials, longer first names), else a fresh key."""
    for k, v in merged.items():
        other = v["name"] if isinstance(v, dict) else v.name
        if same_person(name, other):
            return k
    return name_key(name)


_SENIORITY = [r"chair", r"managing director|\bmd\b|\bceo\b|chief executive", r"\bcfo\b|chief financial", r"\bcoo\b|chief operating",
              r"chief|president", r"executive director|whole[- ]time", r"head|vice president|\bvp\b", r"secretary|compliance"]


def _rank(cp: CompanyPerson) -> tuple:
    r = cp.role.lower()
    tier = next((i for i, pat in enumerate(_SENIORITY) if re.search(pat, r)), len(_SENIORITY))
    return (cp.status != "current", {"executive": 0, "director": 1, "independent": 2}[cp.kind], tier, cp.name)


def ensure(ticker: str) -> None:
    with store.connect() as con:
        row = con.execute("SELECT MAX(updated_at) FROM company_people WHERE ticker=?", (ticker,)).fetchone()
    if not row[0] or datetime.now(timezone.utc) - datetime.fromisoformat(row[0]) > STALE_AFTER:
        refresh(ticker)


def _company_name(ticker: str) -> str:
    c = companies.known().get(ticker)
    if c:
        return c.name
    with store.connect() as con:
        r = con.execute("SELECT name FROM companies WHERE ticker=?", (ticker,)).fetchone()
    return r["name"] if r else ticker


def _rows(ticker: str) -> list[CompanyPerson]:
    with store.connect() as con:
        base = con.execute("SELECT * FROM company_people WHERE ticker=?", (ticker,)).fetchall()
        changes = con.execute(
            "SELECT p.name, p.role, p.change, p.effective_date, a.filed_at FROM people_mentions p JOIN announcements a ON a.id=p.announcement_id "
            "WHERE p.ticker=? ORDER BY a.filed_at", (ticker,)).fetchall()
    people = {r["name_key"]: CompanyPerson(
        id=r["id"], ticker=ticker, name=r["name"], role=r["role"], kind=r["kind"], status=r["status"], since=r["since"],
        year_born=r["year_born"], sources=json.loads(r["sources"] or "[]"), as_of=r["as_of"]) for r in base}
    # Filings after the snapshot win: a resignation marks someone former; an appointment adds them.
    for ch in changes:
        if len(name_key(ch["name"])) < 4:
            continue
        when = (ch["effective_date"] or ch["filed_at"] or "")[:10]
        k = _match_key(ch["name"], people)
        if k in people:
            p = people[k]
            if _change(ch["change"]) in LEFT and (not p.as_of or when >= p.as_of):
                people[k] = p.model_copy(update={"status": "former", "sources": [*p.sources, f"Exchange filing {when}"]})
        elif _change(ch["change"]) == "appointed" and ch["role"]:
            role = re.sub(r"\s*\(.*?\)|\s+of$", "", ch["role"]).strip()
            people[k] = CompanyPerson(id=_pid(ticker, k), ticker=ticker, name=clean_name(ch["name"]), role=role, kind=_kind(role),  # type: ignore[arg-type]
                                      status="current", since=when, sources=[f"Exchange filing {when}"])
    return sorted(people.values(), key=_rank)


def _to_person(cp: CompanyPerson) -> Person:
    start = int(cp.since[:4]) if cp.since and cp.since[:4].isdigit() else None
    company = _company_name(cp.ticker)
    return Person(
        id=cp.id, name=cp.name,
        headline=f"{'Former ' if cp.status == 'former' else ''}{cp.role}, {company}",
        bio=f"Born {cp.year_born}." if cp.year_born else None,
        positions=[Position(company=company, ticker=cp.ticker, title=cp.role, start=start, end=None)],
        relationship=None, synthetic=False, source="company",
    )


def _connection(cp: CompanyPerson, net: list[Person]) -> NetworkHint | None:
    """Is this executive/director already one of your connections? Name must match AND an employer must match."""
    for p in net:
        if same_person(p.name, cp.name) and any(pos.ticker == cp.ticker for pos in p.positions):
            return NetworkHint(person_id=p.id, name=p.name, headline=p.headline, reason="Already one of your connections",
                               degree=1, strength=p.relationship.strength if p.relationship else 0.5)
    return None


def for_company(ticker: str) -> list[CompanyPerson]:
    t = ticker.upper()
    try:
        ensure(t)
    except Exception as e:
        log.warning("company people %s: %s", t, e)
    net = graph.people()
    out = []
    for cp in _rows(t):
        person = _to_person(cp)
        # Paths beyond "also worked here" (that's shown once, at company level): schools, earlier employers.
        paths = [h for h in graph.who_knows_person(person) if not h.reason.startswith(("both at", "both worked at"))]
        conn = _connection(cp, net)
        if not conn and cp.status == "current":
            from app.services.network_query import insider_paths

            seen = {h.person_id for h in paths}
            paths += [h for h in insider_paths(cp.role, t) if h.person_id not in seen]
        out.append(cp.model_copy(update={"connection": conn, "paths": paths[:2]}))
    return out


def as_person(pid: str) -> Person | None:
    m = re.match(r"^c-([A-Z0-9&-]+?)-([a-z0-9-]+)$", pid)
    if not m:
        return None
    for cp in _rows(m.group(1)):
        if cp.id == pid:
            return _to_person(cp)
    return None


def summary() -> list[CompanyPeopleSummary]:
    with store.connect() as con:
        counts = dict(con.execute("SELECT ticker, COUNT(*) FROM company_people WHERE status='current' GROUP BY ticker").fetchall())
    net = graph.people()
    out = []
    for c in companies.portfolio():
        n_conn = sum(1 for p in net if any(pos.ticker == c.ticker for pos in p.positions))
        out.append(CompanyPeopleSummary(ticker=c.ticker, name=c.name, people=counts.get(c.ticker, 0), connections=n_conn))
    return out
