"""People named in filings (incoming CFO, resigning director…) as Person records the UI and graph understand."""

from __future__ import annotations

import json
import re
import sqlite3

from app.ingest import store
from app.models import Education, Person, Position

_YEAR = re.compile(r"(19|20)\d{2}")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def person_id(announcement_id: str, name: str) -> str:
    return f"f-{announcement_id}-{_slug(name)}"


def _years(s: str | None) -> tuple[int | None, int | None]:
    ys = [int(m.group(0)) for m in _YEAR.finditer(s or "")]
    return (ys[0] if ys else None, ys[1] if len(ys) > 1 else None)


def to_person(row: sqlite3.Row, company_name: str) -> Person:
    bg = json.loads(row["background"] or "{}")
    verb = {"appointed": "Incoming", "resigned": "Outgoing", "retired": "Retiring", "ceased": "Outgoing", "demise": "Late"}.get(row["change"] or "", "")
    role = row["role"] or "Management change"  # headline only; titles drop this placeholder
    positions = [Position(company=company_name, ticker=row["ticker"], title=role, start=_years(row["effective_date"])[0])]
    for r in bg.get("previous_roles") or []:
        if r.get("company"):
            s, e = _years(r.get("years"))
            positions.append(Position(company=r["company"], title=r.get("title") or "", start=s, end=e if s else None))
    education = []
    for ed in bg.get("education") or []:
        s, e = _years(ed)
        education.append(Education(school=_YEAR.sub("", ed).strip(" ,-()"), start=s, end=e or s))
    return Person(
        id=person_id(row["announcement_id"], row["name"]),
        name=row["name"],
        headline=f"{verb} {role}, {company_name}".strip(),
        bio=bg.get("background"),
        positions=positions,
        education=education,
        relationship=None,
        synthetic=False,
    )


def for_announcement(con: sqlite3.Connection, announcement_id: str, company_name: str) -> list[Person]:
    rows = con.execute("SELECT * FROM people_mentions WHERE announcement_id=?", (announcement_id,)).fetchall()
    return [to_person(r, company_name) for r in rows]


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
