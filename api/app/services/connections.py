"""The investor's own connections: imported from their LinkedIn data export, or added by hand.

Privacy: stored only in this deployment's SQLite file; email addresses in the export are dropped on read;
a whole import can be removed in one call. Nothing here is sent to an LLM.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import datetime

from app.ingest import store
from app.ingest.people_sources import clean_name, nse_companies, org_key, resolve_ticker
from app.models import CompanyLink, ImportResult, Person, PersonIn, Position, Relationship
from app.services import companies, graph


class ImportError_(ValueError):
    pass


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def _extra_aliases() -> dict[str, str]:
    """Portfolio names incl. parenthetical former names ('Eternal (Zomato)')."""
    out = {}
    for c in [*companies.portfolio(), *companies.watchlist()]:
        for part in re.split(r"[()]", c.name):
            if part.strip():
                out[org_key(part)] = c.ticker
    return out


def _read_csv(data: bytes, filename: str) -> list[dict]:
    if data[:2] == b"PK" or filename.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next((n for n in z.namelist() if n.lower().endswith("connections.csv")), None)
            if not name:
                raise ImportError_("No Connections.csv inside that zip. In LinkedIn: Settings → Data privacy → Get a copy of your data → Connections.")
            data = z.read(name)
    text = data.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.lower().startswith("first name")), None)  # LinkedIn prepends a "Notes:" preamble
    if start is None:
        raise ImportError_("That doesn't look like LinkedIn's Connections.csv (no 'First Name' header).")
    return list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))


def _row_to_person(r: dict, aliases: dict[str, str]) -> Person | None:
    first, last = (r.get("First Name") or "").strip(), (r.get("Last Name") or "").strip()
    name = clean_name(f"{first} {last}")
    if len(name) < 2:
        return None
    url = (r.get("URL") or "").strip() or None
    company, title = (r.get("Company") or "").strip(), (r.get("Position") or "").strip()
    m = re.search(r"/in/([^/?#]+)", url or "")
    pid = f"li-{_slug(m.group(1))}" if m else f"li-{_slug(name + '-' + company)}"
    since = None
    try:
        since = datetime.strptime((r.get("Connected On") or "").strip(), "%d %b %Y")
    except ValueError:
        pass
    positions = [Position(company=company, ticker=resolve_ticker(company, aliases), title=title or "")] if company else []
    return Person(
        id=pid, name=name, headline=" · ".join(x for x in (title, company) if x) or "LinkedIn connection",
        positions=positions, education=[], expertise=[],
        relationship=Relationship(context=f"LinkedIn connection since {since:%b %Y}" if since else "LinkedIn connection", strength=0.4),
        synthetic=False, source="linkedin", linkedin_url=url,
    )


def _row(p: Person) -> dict:
    now = store.now_iso()
    return {"id": p.id, "name": p.name, "headline": p.headline,
            "positions": [x.model_dump() for x in p.positions], "education": [x.model_dump() for x in p.education],
            "expertise": p.expertise, "relationship": p.relationship.model_dump(mode="json") if p.relationship else None,
            "source": p.source, "linkedin_url": p.linkedin_url, "created_at": now, "updated_at": now}


def import_linkedin(data: bytes, filename: str) -> ImportResult:
    """Full sync: the uploaded file becomes the truth for LinkedIn-sourced connections.
    Relationship details you've edited in FINN (strength, last contact, notes) are kept for people still in the file."""
    aliases = _extra_aliases()
    incoming: dict[str, Person] = {}
    for r in _read_csv(data, filename):
        if p := _row_to_person(r, aliases):
            incoming[p.id] = p
    if not incoming:
        raise ImportError_("No connections found in that file.")
    with store.connect() as con:
        existing = {r["id"]: r for r in con.execute("SELECT id, relationship, expertise, created_at FROM people WHERE source='linkedin'")}
        rows = []
        for pid, p in incoming.items():
            row = _row(p)
            if old := existing.get(pid):
                rel = json.loads(old["relationship"] or "null")
                if rel and (rel.get("last_contact") or rel.get("strength") != 0.4 or not rel.get("context", "").startswith("LinkedIn")):
                    row["relationship"] = rel
                row["expertise"] = json.loads(old["expertise"] or "[]") or row["expertise"]
                row["created_at"] = old["created_at"]
            rows.append(row)
        gone = [pid for pid in existing if pid not in incoming]
        con.executemany("DELETE FROM people WHERE id=?", [(g,) for g in gone])
        store.upsert(con, "people", rows)
    graph.invalidate()

    port = {c.ticker for c in companies.portfolio()}
    names = {sym: name for name, sym in nse_companies().items()} | {c.ticker: c.name for c in [*companies.portfolio(), *companies.watchlist()]}
    counts: dict[str, int] = {}
    for p in incoming.values():
        for pos in p.positions:
            if pos.ticker:
                counts[pos.ticker] = counts.get(pos.ticker, 0) + 1
    linked = sorted((CompanyLink(ticker=t, name=names.get(t, t).title() if t not in port else names[t], count=n, in_portfolio=t in port)
                     for t, n in counts.items()), key=lambda l: (not l.in_portfolio, -l.count))
    return ImportResult(total=len(incoming), added=len(set(incoming) - set(existing)), updated=len(set(incoming) & set(existing)),
                        removed=len(gone), linked=linked[:25], at_portfolio=sum(n for t, n in counts.items() if t in port))


def remove_import() -> int:
    with store.connect() as con:
        n = con.execute("DELETE FROM people WHERE source='linkedin'").rowcount
    graph.invalidate()
    return n


def add(p: PersonIn) -> Person:
    aliases = _extra_aliases()
    positions = []
    if p.current_company or p.current_title:
        positions.append(Position(company=p.current_company or "", ticker=resolve_ticker(p.current_company or "", aliases),
                                  title=p.current_title or "", start=None))
    for r in p.past_roles:
        if r.company:
            positions.append(r.model_copy(update={"ticker": r.ticker or resolve_ticker(r.company, aliases)}))
    person = Person(
        id=f"m-{_slug(p.name)}-{datetime.now():%y%m%d%H%M%S}",
        name=clean_name(p.name),
        headline=" · ".join(x for x in (p.current_title, p.current_company) if x) or "Connection",
        positions=positions, education=p.education, expertise=[e.strip() for e in p.expertise if e.strip()],
        relationship=Relationship(context=p.context or "Added by you", strength=p.strength, last_contact=p.last_contact),
        synthetic=False, source="manual", linkedin_url=p.linkedin_url,
    )
    with store.connect() as con:
        store.upsert(con, "people", [_row(person)])
    graph.invalidate()
    return person


def delete(pid: str) -> bool:
    with store.connect() as con:
        n = con.execute("DELETE FROM people WHERE id=? AND source IN ('manual','linkedin')", (pid,)).rowcount
    graph.invalidate()
    return n > 0


def load_all() -> list[Person]:
    with store.connect() as con:
        rows = con.execute("SELECT * FROM people").fetchall()
    out = []
    for r in rows:
        out.append(Person(
            id=r["id"], name=r["name"], headline=r["headline"] or "",
            positions=json.loads(r["positions"] or "[]"), education=json.loads(r["education"] or "[]"),
            expertise=json.loads(r["expertise"] or "[]"), relationship=json.loads(r["relationship"] or "null"),
            synthetic=False, source=r["source"], linkedin_url=r["linkedin_url"],
        ))
    return out
