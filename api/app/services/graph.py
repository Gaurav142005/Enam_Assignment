"""The investor's network as a small in-memory graph.

Edges are *inferred* from profiles, never hand-entered:
  - worked at the same company with overlapping tenure
  - studied at the same school with overlapping years
Degree 1 = someone the investor knows. Degree 2 = reachable through one of them.
"""

from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from app import config
from app.ingest import store
from app.models import NetworkHint, Person, ReconnectNudge, ThemeGroup

DATA = Path(__file__).resolve().parent.parent / "data" / "network" / "people.json"


@lru_cache
def _demo() -> tuple[dict[str, Person], dict[str, Person]]:
    raw = json.loads(DATA.read_text())
    network = {p["id"]: Person.model_validate(p) for p in raw["people"]}
    outside = {p["id"]: Person.model_validate(p) for p in raw.get("filing_people", [])}
    return network, outside


_cache: dict[str, Person] | None = None


def invalidate() -> None:
    """Call after any write to the investor's connections."""
    global _cache
    _cache = None


def _network() -> dict[str, Person]:
    global _cache
    if _cache is None:
        from app.services import connections  # local import: connections → graph → connections

        merged = dict(_demo()[0]) if config.DEMO_NETWORK else {}
        merged.update({p.id: p for p in connections.load_all()})
        # Conversations the investor logged in FINN override whatever the profile source said.
        with store.connect() as con:
            log_ = {r["person_id"]: r["last_contact"] for r in con.execute("SELECT person_id, last_contact FROM contact_log")}
        for pid, when in log_.items():
            p = merged.get(pid)
            if p and p.relationship:
                merged[pid] = p.model_copy(update={"relationship": p.relationship.model_copy(update={"last_contact": date.fromisoformat(when)})})
        _cache = merged
    return _cache


@lru_cache
def investor() -> Person:
    """The investor's own profile (schools, employers): lets FINN notice what they personally share with someone."""
    raw = json.loads(DATA.read_text())["investor"]
    return Person(id="me", name="You", headline="", positions=raw.get("positions", []), education=raw.get("education", []))


def people() -> list[Person]:
    """Everyone in the investor's network (demo + imported + added by hand)."""
    return list(_network().values())


def get(person_id: str) -> Person | None:
    if p := _network().get(person_id) or _demo()[1].get(person_id):
        return p
    if person_id.startswith("c-"):
        from app.services import company_people

        return company_people.as_person(person_id)
    return None


def _years(start: int | None, end: int | None) -> range:
    if start is None:
        return range(0)
    return range(start, (end or date.today().year) + 1)


_SUFFIX = re.compile(r"\b(ltd|limited|pvt|private|inc|llp|india|co|company|corporation|the)\b\.?", re.I)


_SCHOOL = [(r"indian institutes? of technology", "iit"), (r"indian institutes? of management", "iim"), (r"indian school of business", "isb"),
           (r"\bbombay\b", "mumbai"), (r"\bmadras\b", "chennai"), (r"\bbengaluru\b", "bangalore")]


def _norm(name: str) -> str:
    low = name.lower()
    for pat, short in _SCHOOL:  # "Indian Institute of Technology, Kanpur" == "IIT Kanpur"
        low = re.sub(pat, short, low)
    return " ".join(_SUFFIX.sub(" ", low).replace("&", " and ").replace(",", " ").split())


def _same_org(a: str, b: str) -> bool:
    """'Havells India Ltd.' == 'Havells India' == 'havells'. Cheap normalisation; good enough for filings."""
    na, nb = _norm(a), _norm(b)
    return bool(na) and (na == nb or na.startswith(nb + " ") or nb.startswith(na + " "))


def overlaps(a: Person, b: Person) -> list[str]:
    """Human-readable reasons two people plausibly know each other."""
    reasons: list[str] = []
    for pa in a.positions:
        for pb in b.positions:
            if _same_org(pa.company, pb.company):
                ya, yb = _years(pa.start, pa.end), _years(pb.start, pb.end)
                shared = set(ya) & set(yb)
                if shared:
                    reasons.append(f"both at {pa.company} {min(shared)}–{max(shared)}")
                elif not ya or not yb:
                    reasons.append(f"both worked at {pa.company} (dates unclear)")
    for ea in a.education:
        for eb in b.education:
            if not _same_org(ea.school, eb.school):
                continue
            if None in (ea.start, ea.end, eb.start, eb.end):
                reasons.append(f"fellow {min(ea.school, eb.school, key=len)} alumni")
            elif set(range(ea.start, ea.end + 1)) & set(range(eb.start, eb.end + 1)):  # type: ignore[arg-type]
                reasons.append(f"{ea.school} classmates ({eb.end})")
    return reasons


def log_contact(person_id: str, on: date, note: str | None = None) -> None:
    with store.connect() as con:
        con.execute("INSERT OR REPLACE INTO contact_log VALUES (?,?,?,?)", (person_id, on.isoformat(), note, store.now_iso()))
    invalidate()


def _hint(p: Person, reason: str, degree: int = 1, via: str | None = None, relation: str = "insider") -> NetworkHint:
    strength = p.relationship.strength if p.relationship else 0.3
    return NetworkHint(
        person_id=p.id,
        name=p.name,
        headline=p.headline,
        reason=reason,
        degree=degree,  # type: ignore[arg-type]
        via=via,
        strength=strength if degree == 1 else round(strength * 0.6, 2),
        relation=relation,  # type: ignore[arg-type]
    )


def who_knows_company(ticker: str, limit: int = 3, wide: bool | None = None) -> list[NetworkHint]:
    """Who should I call? Insiders (worked there). With no insider, widen to competitors, then sector experts.
    wide=True always widens (direct questions); wide=False never does (a route to a specific person must be an insider)."""
    from app.services import companies

    insiders: list[NetworkHint] = []
    seen: set[str] = set()
    for p in people():
        for pos in p.positions:
            if pos.ticker == ticker:
                when = f", {pos.start}–{pos.end or 'now'}" if pos.start else ""
                role = f"{pos.title} at {pos.company}" if pos.title else f"Works at {pos.company}"
                insiders.append(_hint(p, f"{role}{when}"))
                seen.add(p.id)
                break
    insiders.sort(key=lambda h: h.strength, reverse=True)
    if wide is False or (wide is None and insiders) or len(insiders) >= limit:
        return insiders[:limit]

    group = companies.group_of(ticker)
    peer_names = {c.ticker: c.name for c in companies.peers(ticker)}
    wider: list[NetworkHint] = []
    for p in people():
        if p.id in seen:
            continue
        pos = next((x for x in p.positions if x.ticker in peer_names), None)
        if pos:
            wider.append(_hint(p, f"{pos.title or 'Works'} at {pos.company}, a peer in {group}", relation="peer"))
            seen.add(p.id)
            continue
        if group:
            tag = next((e for e in p.expertise if any(k in e.lower() for k in companies.group_keywords(group))), None)
            if tag:
                h = _hint(p, f"Go-to for {tag}", relation="expert")
                wider.append(h.model_copy(update={"strength": round(h.strength * 0.8, 2)}))
                seen.add(p.id)
    wider.sort(key=lambda h: (h.relation != "peer", -h.strength))
    return (insiders + wider)[:limit]


def who_knows_person(target: Person, limit: int = 3) -> list[NetworkHint]:
    """Second-degree reach — who in my network has crossed paths with this person."""
    hints = []
    for p in people():
        if p.id == target.id or not (r := overlaps(p, target)):
            continue
        h = _hint(p, "; ".join(r), relation="overlap")
        if all(x.startswith("fellow ") for x in r):  # same school, years unknown: a warm opener, not proof they've met
            h = h.model_copy(update={"strength": round(h.strength * 0.6, 2)})
        hints.append(h)
    hints.sort(key=lambda h: h.strength, reverse=True)
    return hints[:limit]


def themes() -> list[ThemeGroup]:
    """Expertise map: theme → go-to people."""
    groups: dict[str, list[NetworkHint]] = {}
    for p in people():
        for tag in p.expertise:
            groups.setdefault(tag, []).append(_hint(p, p.headline))
    return [ThemeGroup(theme=t, people=sorted(h, key=lambda x: -x.strength)) for t, h in sorted(groups.items())]


def reconnect(news: dict[str, str], today: date | None = None) -> list[ReconnectNudge]:
    """Keep the network warm: people gone quiet whose (former) employer just had news. `news`: ticker → what happened."""
    today = today or date.today()
    nudges: list[ReconnectNudge] = []
    for p in people():
        last = p.relationship.last_contact if p.relationship else None
        days = (today - last).days if last else None
        hit = next((pos for pos in p.positions if pos.ticker in news), None)
        if hit and (days is None or days > 90):
            tie = "where they work" if hit.end is None else "their former employer"
            since = f"You last spoke {_ago(days)}" if days is not None else "No conversation logged"
            nudges.append(ReconnectNudge(person=p, reason=f"{news[hit.ticker]} at {hit.company}, {tie}. {since}.", days_since_contact=days))
    nudges.sort(key=lambda n: (-(n.person.relationship.strength if n.person.relationship else 0), -(n.days_since_contact or 0)))
    return nudges


def _ago(days: int) -> str:
    if days < 60:
        return f"{days} days ago"
    if days < 700:
        return f"{round(days / 30)} months ago"
    return f"{days / 365:.1f} years ago"
