"""Ask the network directly: "who knows rural lending?", "anyone at Dixon?", "who can reach the Polycab CFO?".

Deterministic on purpose: the graph is small and structured, so matching companies, sectors, expertise, schools and roles
is instant, explainable, and sends no personal data to a model.
"""

from __future__ import annotations

import re

from app.ingest import store
from app.ingest.people_sources import same_person
from app.models import Company, Dossier, FilingRef, NetworkAnswer, NetworkHint, Person
from app.services import companies, filing_people, graph

_STOP = set(["who", "do", "i", "know", "can", "could", "would", "should", "the", "a", "an", "at", "in", "of", "for", "to", "and", "or", "is", "are", "my", "me", "any", "anyone", "someone", "somebody", "people", "person", "knows", "know", "about", "with", "from", "has", "have", "worked", "works", "working", "reach", "talk", "call", "ask", "on", "that", "which", "what", "best", "there"])

FUNCTIONS: dict[str, tuple[str, ...]] = {
    "finance": ("cfo", "finance", "financial", "treasury", "controller", "accounts", "audit"),
    "strategy": ("strategy", "strategic", "corporate development", "m&a"),
    "risk": ("risk", "credit", "compliance"),
    "investor relations": ("investor relations",),
    "operations": ("operations", "plant", "manufacturing", "supply chain", "coo", "projects"),
    "technology": ("digital", "information", "software", "technology", "engineer", "cto", "cio"),
    "sales & marketing": ("sales", "marketing", "brand", "category", "retail"),
    "leadership": ("ceo", "managing director", "chairman", "chairperson", "founder", "promoter"),
}


def function_of(title: str) -> str | None:
    low = f" {title.lower()} "
    return next((f for f, keys in FUNCTIONS.items() if any(re.search(rf"\b{re.escape(k)}\b", low) for k in keys)), None)


def _companies_in(q: str) -> list[Company]:
    low = f" {q.lower()} "
    hits = []
    for c in companies.known().values():
        names = {c.ticker.lower(), *[part.strip().lower() for part in re.split(r"[()]", c.name) if part.strip()]}
        names |= {n.split()[0] for n in names if len(n.split()[0]) >= 5}  # "polycab", "dixon", "infosys"
        names |= {" ".join(n.split()[:2]) for n in names if len(n.split()) > 2}  # "cg power", "sun pharmaceutical"
        if any(re.search(rf"\b{re.escape(n)}\b", low) for n in names):
            hits.append(c)
    return hits


def ask(q: str) -> NetworkAnswer:
    low = q.lower()
    words = [w for w in re.findall(r"[a-z&]+", low) if w not in _STOP and len(w) > 2]
    net = graph.people()
    scored: dict[str, tuple[float, NetworkHint]] = {}
    read: list[str] = []

    def add(h: NetworkHint, score: float) -> None:
        if h.person_id not in scored or score > scored[h.person_id][0]:
            scored[h.person_id] = (score, h)

    cos = _companies_in(q)
    fn = next((f for f, keys in FUNCTIONS.items() if f in low or any(re.search(rf"\b{re.escape(k)}\b", low) for k in keys)), None)
    for c in cos:
        read.append(f"people who know {c.name}")
        for h in graph.who_knows_company(c.ticker, limit=12, wide=not fn):  # a role + a company means insiders only
            add(h, {"insider": 3, "peer": 2, "expert": 1.5}.get(h.relation, 1) + h.strength)

    if fn:
        read.append(f"{fn} backgrounds")
        for p in net:
            pos = next((x for x in p.positions if function_of(x.title) == fn and (not cos or x.ticker in {c.ticker for c in cos})), None)
            if pos:
                add(graph._hint(p, f"{pos.title} at {pos.company}"), 2.5 + (p.relationship.strength if p.relationship else 0))

    sector_text = low
    for k in FUNCTIONS.get(fn or "", ()):  # "finance people" is a role, not the lending sector
        sector_text = sector_text.replace(k, " ")
    groups = [] if cos else [g for g in companies._GROUPS if g.lower() in sector_text or any(k in sector_text for k in companies.group_keywords(g))]
    themes = sorted({e for p in net for e in p.expertise if e.lower() in low or any(w in e.lower().split() for w in words)})
    if themes:
        read.append("go-to people for " + ", ".join(themes[:3]))
    for p in net:
        s = p.relationship.strength if p.relationship else 0
        tag = next((e for e in p.expertise if e in themes), None)
        if tag:
            add(graph._hint(p, f"Go-to for {tag}", relation="expert"), 2.2 + s)
        for g in groups:
            pos = next((x for x in p.positions if x.ticker and companies.group_of(x.ticker) == g), None)
            if pos:
                add(graph._hint(p, f"{pos.title or 'Works'} at {pos.company} ({g})", relation="peer"), 1.8 + s)
        school = next((e for e in p.education if any(w in e.school.lower().split() for w in words if len(w) > 3) or e.school.lower() in low), None)
        if school:
            add(graph._hint(p, f"Studied at {school.school}", relation="overlap"), 1.6 + s)
            if f"alumni of {school.school}" not in read:
                read.append(f"alumni of {school.school}")
        if any(w in p.name.lower().split() for w in words):
            add(graph._hint(p, p.headline), 3.5 + s)
    if groups and not themes:
        read.append("people in " + ", ".join(groups))

    results = [h for _, h in sorted(scored.values(), key=lambda x: -x[0])][:12]
    understood = ("Looking for " + "; ".join(dict.fromkeys(read))) if read else "Couldn't tie that to a company, sector, role, school or name in your network"
    return NetworkAnswer(query=q, understood=understood, results=results, companies=cos)


def insider_paths(leader_role: str, ticker: str) -> list[NetworkHint]:
    """Second-degree reach into a company: your connections who worked there in the same function as this leader."""
    fn = function_of(leader_role)
    top = fn == "leadership"
    out = []
    for p in graph.people():
        pos = next((x for x in p.positions if x.ticker == ticker), None)
        if not pos:
            continue
        same_fn = fn and function_of(pos.title) == fn
        senior = bool(re.search(r"chief|cfo|head|president|director|vp\b|vice president", pos.title.lower()))
        if same_fn or (top and senior):
            when = f" ({pos.start}–{pos.end or 'now'})" if pos.start else ""
            why = f"Worked in {fn} there as {pos.title}{when}" if same_fn and not top else f"Was {pos.title} there{when}; senior enough to know them"
            out.append(graph._hint(p, why, degree=1, relation="overlap"))
    return sorted(out, key=lambda h: -h.strength)[:2]


def dossier(person: Person) -> Dossier:
    """Diligence before a meeting. Everything here is from filings and the investor's own graph."""
    ticker = next((pos.ticker for pos in person.positions if pos.ticker), None)
    role = person.positions[0].title if person.positions else ""
    paths = [] if person.relationship else graph.who_knows_person(person)
    if not person.relationship and ticker:
        seen = {h.person_id for h in paths}
        paths += [h for h in insider_paths(role, ticker) if h.person_id not in seen]
    refs: list[FilingRef] = []
    ask: list[str] = []
    if ticker:
        with store.connect() as con:
            rows = con.execute("SELECT p.name, p.change, p.role, p.background, a.filed_at, a.attachment_url FROM people_mentions p "
                               "JOIN announcements a ON a.id=p.announcement_id WHERE p.ticker=? ORDER BY a.filed_at DESC", (ticker,)).fetchall()
            job = con.execute("SELECT result FROM research_jobs WHERE ticker=? AND status='done' ORDER BY finished_at DESC LIMIT 1", (ticker,)).fetchone()
        for r in rows:
            if same_person(r["name"], person.name):
                verb = {"appointed": "Appointed", "resigned": "Resigned", "retired": "Retired", "ceased": "Stepped down", "redesignated": "Redesignated"}.get(filing_people._change(r["change"]), "Named in a filing")
                role_part = f" as {r['role']}" if r["role"] else ""
                refs.append(FilingRef(date=r["filed_at"][:10], title=f"{verb}{role_part}", url=r["attachment_url"]))
        start = person.positions[0].start if person.positions else None
        from datetime import date as _d

        if start and _d.today().year - start <= 1 and not person.relationship:
            ask.append(f"New in the role (since {start}): what are the priorities for the first year, and what changes from the predecessor?")
        fn = function_of(role)
        if job:
            import json

            qs = [q.get("question") for q in json.loads(job["result"]).get("questions", []) if q.get("question")]
            ask += qs[:3]
        elif fn == "finance":
            ask.append("Working capital and cash conversion: what moved this year, and what is the capex funding plan?")
        elif fn == "leadership":
            ask.append("Where does growth come from over the next three years, and what would make that plan slip?")
    shared = [] if person.relationship else [r.replace("fellow ", "You are both ").replace("both at", "You were both at").replace("both worked at", "You both worked at") for r in graph.overlaps(graph.investor(), person)]
    return Dossier(person=person, shared_with_you=shared, paths=paths[:4], in_filings=refs[:6], ask_about=ask[:4])
