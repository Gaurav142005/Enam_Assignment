"""People named in filings (incoming CFO, resigning director…) as Person records the UI and graph understand."""

from __future__ import annotations

import json
import re
import sqlite3

from app.ingest import store
from app.ingest.people_sources import clean_name
from app.models import Education, Person, Position

_YEAR = re.compile(r"(19|20)\d{2}")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def person_id(announcement_id: str, name: str) -> str:
    return f"f-{announcement_id}-{_slug(name)}"


def _years(s: str | None) -> tuple[int | None, int | None]:
    ys = [int(m.group(0)) for m in _YEAR.finditer(s or "")]
    return (ys[0] if ys else None, ys[1] if len(ys) > 1 else None)


def _change(raw: str | None) -> str:
    """Models and filings phrase it freely ('re-appointment', 'cessation'); fold to the five the UI knows."""
    c = (raw or "").lower()
    for key, norm in (("demise", "demise"), ("resign", "resigned"), ("retire", "retired"), ("cess", "ceased"), ("ceased", "ceased"), ("appoint", "appointed")):
        if key in c:
            return norm
    return c


def to_person(row: sqlite3.Row, company_name: str) -> Person:
    bg = json.loads(row["background"] or "{}")
    verb = {"appointed": "Incoming", "resigned": "Outgoing", "retired": "Retiring", "ceased": "Outgoing", "demise": "Late"}.get(_change(row["change"]), "")
    role = row["role"] or "Management change"  # headline only; titles drop this placeholder
    positions = [Position(company=company_name, ticker=row["ticker"], title=role, start=_years(row["effective_date"])[0])]
    for r in bg.get("previous_roles") or []:
        if r.get("company"):
            s, e = _years(r.get("years"))
            # A past role with no stated end year must not read as "…–now": show the tenure only when both ends are known.
            positions.append(Position(company=r["company"], title=r.get("title") or "", start=s if e else None, end=e))
    education = []
    for ed in bg.get("education") or []:
        s, e = _years(ed)
        text = _YEAR.sub("", ed).strip(" ,-()")
        m = re.match(r"(.+?)\s+(?:from|at)\s+(?:the\s+)?(.+)", text, re.I)  # "Engineering degree from IIT Kanpur"
        degree, school = (m.group(1).strip(), m.group(2).strip()) if m else ("", text)
        education.append(Education(school=school, degree=degree, start=s, end=e or s))
    return Person(
        id=person_id(row["announcement_id"], row["name"]),
        name=clean_name(row["name"]),
        headline=f"{verb} {role}, {company_name}".strip(),
        bio=bg.get("background"),
        positions=positions,
        education=education,
        relationship=None,
        synthetic=False,
        source="filing",
    )


def for_announcement(con: sqlite3.Connection, announcement_id: str, company_name: str) -> list[Person]:
    rows = con.execute("SELECT * FROM people_mentions WHERE announcement_id=?", (announcement_id,)).fetchall()
    # Lead with the incoming person: "who is this and where did they come from" is the question a change raises.
    order = {"appointed": 0, "resigned": 1, "retired": 1, "ceased": 1}
    people = [to_person(r, company_name) for r in sorted(rows, key=lambda r: order.get(_change(r["change"]), 2))]
    return [_fill_from_other_filings(con, p, rows[0]["ticker"], company_name) if not p.bio else p for p in people] if rows else people


def _fill_from_other_filings(con: sqlite3.Connection, p: Person, ticker: str, company_name: str) -> Person:
    """A board-approval filing and the later regulator-approval filing describe the same person; only one carries the profile."""
    from app.ingest.people_sources import same_person

    for r in con.execute("SELECT * FROM people_mentions WHERE ticker=? AND background IS NOT NULL ORDER BY rowid DESC", (ticker,)):
        if same_person(r["name"], p.name):
            other = to_person(r, company_name)
            if other.bio or len(other.positions) > 1:
                return p.model_copy(update={"bio": other.bio, "positions": [p.positions[0], *other.positions[1:]], "education": other.education or p.education})
    return p


def get(pid: str) -> Person | None:
    if not pid.startswith("f-") or not store.has_data():
        return None
    ann_id = pid.split("-")[1]
    with store.connect() as con:
        name = con.execute("SELECT c.name FROM announcements a LEFT JOIN companies c USING (ticker) WHERE a.id=?", (ann_id,)).fetchone()
        for p in for_announcement(con, ann_id, (name and name[0]) or ""):
            if p.id == pid:
                return p
    return None
