"""Builds the Push digest: rank → enrich → weave in the network → collapse the routine."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models import AlertRules, Digest, PushItem, ResultsCut, RoutineGroup
from app.services import companies, graph
from app.services.priority import bucket, move_score, score
from app.services.taxonomy import LABEL

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "announcements.json"


def _announcements(now: datetime, rules: AlertRules) -> list[PushItem]:
    # TODO(push): replace fixtures with services.filings.fetch_announcements(...)
    raw = json.loads(FIXTURES.read_text())
    names = companies.known()
    items: list[PushItem] = []
    for a in raw["announcements"]:
        cat = a["category"]
        person = graph.get(a["person_id"]) if a.get("person_id") else None
        results = ResultsCut.model_validate(a["results"]) if a.get("results") else None

        # The weave: who in my network helps me understand this?
        if person:
            network = graph.who_knows_person(person)
        elif cat in {"M&A", "capex", "litigation", "results", "fund_raise"}:
            network = graph.who_knows_company(a["ticker"])
        else:
            network = []

        s = score(cat, rules, has_network=bool(network), has_enrichment=bool(person or results))
        items.append(
            PushItem(
                id=a["id"],
                kind="announcement",
                ticker=a["ticker"],
                company_name=names[a["ticker"]].name if a["ticker"] in names else a["ticker"],
                category=cat,
                priority=bucket(s),
                score=s,
                title=a["title"],
                summary=a.get("summary"),
                at=now - timedelta(hours=a["hours_ago"]),
                results=results,
                person=person,
                network=network,
                synthetic=True,
            )
        )
    return items


def _moves(now: datetime, rules: AlertRules) -> list[PushItem]:
    # TODO(push): replace fixtures with services.prices.detect_moves(portfolio, rules)
    raw = json.loads(FIXTURES.read_text())
    names = companies.known()
    out: list[PushItem] = []
    for m in raw["eod"]:
        chg, vol = m.get("change_pct"), m.get("volume_multiple")
        price_hit = chg is not None and abs(chg) >= rules.price_move_pct
        vol_hit = vol is not None and vol >= rules.volume_multiple
        if not (price_hit or vol_hit):
            continue
        s = move_score(chg if price_hit else None, vol if vol_hit else None, rules)
        title = (
            f"Volume {vol:.1f}× its {rules.volume_lookback_days}-day average"
            if vol_hit
            else f"{'Up' if chg > 0 else 'Down'} {abs(chg):.1f}% on the day"
        )
        out.append(
            PushItem(
                id=m["id"],
                kind=m["kind"],
                ticker=m["ticker"],
                company_name=names[m["ticker"]].name,
                priority=bucket(s),
                score=s,
                title=title,
                summary=f"Closed ₹{m['close']:,.1f} ({chg:+.1f}%)" if chg is not None else None,
                at=now - timedelta(hours=m["hours_ago"]),
                change_pct=chg,
                network=graph.who_knows_company(m["ticker"], limit=1),
                synthetic=True,
            )
        )
    return sorted(out, key=lambda i: -i.score)


def build(window_hours: int, rules: AlertRules) -> Digest:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=window_hours)
    items = [i for i in _announcements(now, rules) if i.at >= since]

    attention = sorted((i for i in items if i.priority != "routine"), key=lambda i: (-i.score, -i.at.timestamp()))
    groups: dict[str, list[PushItem]] = {}
    for i in items:
        if i.priority == "routine":
            groups.setdefault(i.category or "unclassified", []).append(i)

    return Digest(
        window_hours=window_hours,
        generated_at=now,
        attention=attention,
        moves=[m for m in _moves(now, rules) if m.at >= since],
        routine=[RoutineGroup(category=c, count=len(v), items=v) for c, v in sorted(groups.items(), key=lambda kv: LABEL[kv[0]])],  # type: ignore[arg-type]
    )
