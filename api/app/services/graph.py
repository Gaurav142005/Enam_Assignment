"""The investor's network as a small in-memory graph.

Edges are *inferred* from profiles, never hand-entered:
  - worked at the same company with overlapping tenure
  - studied at the same school with overlapping years
Degree 1 = someone the investor knows. Degree 2 = reachable through one of them.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.models import NetworkHint, Person, ReconnectNudge, ThemeGroup

DATA = Path(__file__).resolve().parent.parent / "data" / "network" / "people.json"


@lru_cache
def _load() -> tuple[dict[str, Person], dict[str, Person]]:
    raw = json.loads(DATA.read_text())
    network = {p["id"]: Person.model_validate(p) for p in raw["people"]}
    outside = {p["id"]: Person.model_validate(p) for p in raw.get("filing_people", [])}
    return network, outside


def people() -> list[Person]:
    return list(_load()[0].values())


def get(person_id: str) -> Person | None:
    network, outside = _load()
    return network.get(person_id) or outside.get(person_id)


def _years(start: int, end: int | None) -> range:
    return range(start, (end or date.today().year) + 1)


def overlaps(a: Person, b: Person) -> list[str]:
    """Human-readable reasons two people plausibly know each other."""
    reasons: list[str] = []
    for pa in a.positions:
        for pb in b.positions:
            if pa.company == pb.company:
                shared = set(_years(pa.start, pa.end)) & set(_years(pb.start, pb.end))
                if shared:
                    reasons.append(f"both at {pa.company} {min(shared)}–{max(shared)}")
    for ea in a.education:
        for eb in b.education:
            if ea.school == eb.school and set(range(ea.start, ea.end + 1)) & set(range(eb.start, eb.end + 1)):
                reasons.append(f"{ea.school} classmates ({eb.end})")
    return reasons


def _hint(p: Person, reason: str, degree: int = 1, via: str | None = None) -> NetworkHint:
    strength = p.relationship.strength if p.relationship else 0.3
    return NetworkHint(
        person_id=p.id,
        name=p.name,
        headline=p.headline,
        reason=reason,
        degree=degree,  # type: ignore[arg-type]
        via=via,
        strength=strength if degree == 1 else round(strength * 0.6, 2),
    )


def who_knows_company(ticker: str, limit: int = 3) -> list[NetworkHint]:
    """Who should I call? — people who have worked at the company."""
    hints: list[NetworkHint] = []
    for p in people():
        for pos in p.positions:
            if pos.ticker == ticker:
                when = f"{pos.start}–{pos.end or 'now'}"
                hints.append(_hint(p, f"{pos.title} at {pos.company}, {when}"))
                break
    hints.sort(key=lambda h: h.strength, reverse=True)
    return hints[:limit]


def who_knows_person(target: Person, limit: int = 3) -> list[NetworkHint]:
    """Second-degree reach — who in my network has crossed paths with this person."""
    hints = [_hint(p, "; ".join(r)) for p in people() if p.id != target.id and (r := overlaps(p, target))]
    hints.sort(key=lambda h: h.strength, reverse=True)
    return hints[:limit]


def themes() -> list[ThemeGroup]:
    """Expertise map: theme → go-to people."""
    groups: dict[str, list[NetworkHint]] = {}
    for p in people():
        for tag in p.expertise:
            groups.setdefault(tag, []).append(_hint(p, p.headline))
    return [ThemeGroup(theme=t, people=sorted(h, key=lambda x: -x.strength)) for t, h in sorted(groups.items())]


def reconnect(active_tickers: set[str], today: date | None = None) -> list[ReconnectNudge]:
    """Keep the network warm: people gone quiet whose (former) employer just had news."""
    today = today or date.today()
    nudges: list[ReconnectNudge] = []
    for p in people():
        last = p.relationship.last_contact if p.relationship else None
        days = (today - last).days if last else None
        hit = next((pos for pos in p.positions if pos.ticker in active_tickers), None)
        if hit and (days is None or days > 90):
            tie = "current employer" if hit.end is None else "former employer"
            since = f"last spoke {days} days ago" if days is not None else "no contact logged"
            nudges.append(
                ReconnectNudge(person=p, reason=f"News at {hit.company} ({tie}) — {since}", days_since_contact=days)
            )
    nudges.sort(key=lambda n: -(n.days_since_contact or 0))
    return nudges
