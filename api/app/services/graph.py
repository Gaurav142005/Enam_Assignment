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
        _cache = merged
    return _cache


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


def _norm(name: str) -> str:
    return " ".join(_SUFFIX.sub(" ", name.lower()).replace("&", " and ").replace(",", " ").split())


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
                reasons.append(f"both studied at {ea.school}")
            elif set(range(ea.start, ea.end + 1)) & set(range(eb.start, eb.end + 1)):  # type: ignore[arg-type]
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
                when = f", {pos.start}–{pos.end or 'now'}" if pos.start else ""
                role = f"{pos.title} at {pos.company}" if pos.title else f"Works at {pos.company}"
                hints.append(_hint(p, f"{role}{when}"))
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
