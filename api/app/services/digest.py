"""Builds the Push digest: rank → enrich → weave in the network → collapse the routine.

Reads the ingested store (app/ingest). On a fresh clone with nothing ingested it falls back to
synthetic fixtures, so the UI always runs.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ingest import eod, store
from app.models import AlertRules, Category, Digest, PushItem, ResultsCut, RoutineGroup
from app.services import companies, filing_people, graph
from app.services.priority import bucket, move_score, score
from app.services.taxonomy import LABEL

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "announcements.json"
IST = timezone(timedelta(hours=5, minutes=30))
NETWORK_CATEGORIES = {"M&A", "capex", "litigation", "results", "fund_raise", "pledging", "credit_rating"}


def _network_for(category: str | None, ticker: str, people: list) -> list:
    if people:
        hints = [h for p in people for h in graph.who_knows_person(p)]
        if hints:
            return hints[:3]
    if category in NETWORK_CATEGORIES or (category == "management_change"):
        return graph.who_knows_company(ticker)
    return []


# ── live (ingested) ────────────────────────────────────────────────────────

_BOILER = re.compile(r"^.*?\bhas (?:informed|submitted to|submitted)(?: to)? the exchange,?\s*(?:about|regarding|that|on)?\s*(?:the\s+)?", re.I)


def headline(text: str, nse_desc: str) -> str:
    """NSE one-liners are mostly boilerplate. Strip it; fall back to NSE's label when nothing specific is left."""
    t = _BOILER.sub("", text).strip(" .")
    t = t[:1].upper() + t[1:]
    if len(t.split()) < 3 or t.lower().rstrip(".") in {nse_desc.lower(), "general updates", "updates"}:
        return nse_desc
    first = _first_sentence(t)
    return first if len(first) <= 140 else first[:137].rsplit(" ", 1)[0] + "…"


_ABBREV = {"mr", "ms", "mrs", "dr", "no", "co", "ltd", "pvt", "st", "jr", "sr", "smt", "shri", "vs", "w.e.f", "u/s", "reg"}


def _first_sentence(t: str) -> str:
    """Split on '. ' but not after honorifics/abbreviations or initials ('Mr. V. N. Srivatsan')."""
    out = ""
    for part in re.split(r"(?<=\.) ", t):
        out = f"{out} {part}".strip()
        last = out.rstrip(".").rsplit(" ", 1)[-1].lower()
        if not (last in _ABBREV or len(last) == 1):
            break
    return out.rstrip(".")


def _people_title(people: list) -> str | None:
    """'Anup Bagchi appointed MD & CEO' beats 'Change in Management'."""
    if not people:
        return None
    p = people[0]
    role = p.positions[0].title if p.positions else ""
    role = "" if role.lower() in ("", "management change") else role
    first = p.headline.split()[0] if p.headline else ""
    if role:
        verb = {"Incoming": "appointed", "Outgoing": "steps down as", "Retiring": "retires as", "Late": "passed away —"}.get(first, "")
        title = f"{p.name} {verb} {role}".strip() if verb else f"{p.name}: {role}"
    else:
        title = f"{p.name} {({'Incoming': 'appointed', 'Outgoing': 'steps down', 'Retiring': 'retires', 'Late': 'passed away'}).get(first, '(management change)')}"
    if len(people) > 1:
        title += f" (+{len(people) - 1} more)"
    return title


def _live_announcements(since: datetime, rules: AlertRules) -> list[PushItem]:
    tickers = [c.ticker for c in companies.portfolio()]
    names = companies.known()
    items: list[PushItem] = []
    with store.connect() as con:
        q = f"SELECT * FROM announcements WHERE ticker IN ({','.join('?' * len(tickers))}) AND filed_at >= ? ORDER BY filed_at DESC"
        rows = con.execute(q, (*tickers, since.isoformat())).fetchall()
        for r in rows:
            extra = json.loads(r["extra"] or "{}")
            cat: Category = r["category"]
            name = names[r["ticker"]].name if r["ticker"] in names else r["ticker"]
            people = filing_people.for_announcement(con, r["id"], name) if cat == "management_change" else []
            results = ResultsCut.model_validate(extra["results"]) if extra.get("results") else None
            routine = bool(extra.get("routine"))
            network = [] if routine else _network_for(cat, r["ticker"], people)
            s = score(cat, rules, has_network=bool(network), has_enrichment=bool(people or results))
            if routine:
                s = min(s, 20.0)
            items.append(
                PushItem(
                    id=r["id"], kind="announcement", ticker=r["ticker"], company_name=name, category=cat,
                    priority=bucket(s), score=s,
                    title=_people_title(people) or headline(r["text"], r["nse_desc"]), summary=r["summary"],
                    at=datetime.fromisoformat(r["filed_at"]), source_url=r["attachment_url"], results=results,
                    person=people[0] if people else None, network=network,
                )
            )
    return _dedupe(items)


def _dedupe(items: list[PushItem]) -> list[PushItem]:
    """Results day produces 3–5 filings (outcome, press release, deck…). Keep one card per company+category per day."""
    best: dict[tuple, PushItem] = {}
    for i in items:
        if i.priority == "routine":
            continue
        k = (i.ticker, i.category, i.at.astimezone(IST).date())
        cur = best.get(k)
        if cur is None or (bool(i.results or i.person), i.score) > (bool(cur.results or cur.person), cur.score):
            best[k] = i
    keep = {i.id for i in best.values()}
    return [i if i.priority == "routine" or i.id in keep else i.model_copy(update={"priority": "routine", "network": []}) for i in items]


def _live_moves(rules: AlertRules) -> list[PushItem]:
    names = companies.known()
    out: list[PushItem] = []
    with store.connect() as con:
        for c in companies.portfolio():
            m = eod.detect_move(con, c.ticker, price_move_pct=rules.price_move_pct, volume_multiple=rules.volume_multiple,
                                lookback=rules.volume_lookback_days)
            if not m:
                continue
            s = move_score(m["change_pct"] if m["price_hit"] else None, m["volume_multiple"] if m["vol_hit"] else None, rules)
            chg = m["change_pct"]
            title = (f"Volume {m['volume_multiple']:.1f}× its {m['lookback']}-day average" if m["vol_hit"]
                     else f"{'Up' if chg > 0 else 'Down'} {abs(chg):.1f}% on the day")
            if m["vol_hit"] and m["price_hit"]:
                title += f", price {chg:+.1f}%"
            at = datetime.fromisoformat(m["date"]).replace(hour=15, minute=30, tzinfo=IST)
            out.append(PushItem(
                id=f"eod-{c.ticker}-{m['date']}", kind="volume_spike" if m["vol_hit"] else "price_move", ticker=c.ticker,
                company_name=names[c.ticker].name, priority=bucket(s), score=s, title=title,
                summary=f"Closed ₹{m['close']:,.1f} ({chg:+.1f}%)", at=at, change_pct=chg,
                network=graph.who_knows_company(c.ticker, limit=1),
            ))
    return sorted(out, key=lambda i: -i.score)


# ── fixtures (fresh clone, nothing ingested) ───────────────────────────────


def _fixture_announcements(now: datetime, rules: AlertRules) -> list[PushItem]:
    raw = json.loads(FIXTURES.read_text())
    names = companies.known()
    items: list[PushItem] = []
    for a in raw["announcements"]:
        cat = a["category"]
        person = graph.get(a["person_id"]) if a.get("person_id") else None
        results = ResultsCut.model_validate(a["results"]) if a.get("results") else None
        network = _network_for(cat, a["ticker"], [person] if person else []) if cat in NETWORK_CATEGORIES or person else []
        s = score(cat, rules, has_network=bool(network), has_enrichment=bool(person or results))
        items.append(PushItem(
            id=a["id"], kind="announcement", ticker=a["ticker"], company_name=names[a["ticker"]].name, category=cat,
            priority=bucket(s), score=s, title=a["title"], summary=a.get("summary"), at=now - timedelta(hours=a["hours_ago"]),
            results=results, person=person, network=network, synthetic=True,
        ))
    return items


def _fixture_moves(now: datetime, rules: AlertRules) -> list[PushItem]:
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
        title = f"Volume {vol:.1f}× its {rules.volume_lookback_days}-day average" if vol_hit else f"{'Up' if chg > 0 else 'Down'} {abs(chg):.1f}% on the day"
        out.append(PushItem(
            id=m["id"], kind=m["kind"], ticker=m["ticker"], company_name=names[m["ticker"]].name, priority=bucket(s), score=s,
            title=title, summary=f"Closed ₹{m['close']:,.1f} ({chg:+.1f}%)", at=now - timedelta(hours=m["hours_ago"]),
            change_pct=chg, network=graph.who_knows_company(m["ticker"], limit=1), synthetic=True,
        ))
    return sorted(out, key=lambda i: -i.score)


# ── assemble ───────────────────────────────────────────────────────────────


def build(window_hours: int, rules: AlertRules) -> Digest:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=window_hours)
    if store.has_data():
        items, moves = _live_announcements(since, rules), _live_moves(rules)
    else:
        items = [i for i in _fixture_announcements(now, rules) if i.at >= since]
        moves = _fixture_moves(now, rules)
    moves = [m for m in moves if m.at >= since - timedelta(hours=72)]  # EOD: last session, even across a weekend

    attention = sorted((i for i in items if i.priority != "routine"), key=lambda i: (-i.score, -i.at.timestamp()))
    groups: dict[str, list[PushItem]] = {}
    for i in items:
        if i.priority == "routine":
            groups.setdefault(i.category or "unclassified", []).append(i)
    return Digest(
        window_hours=window_hours,
        generated_at=now,
        attention=attention,
        moves=moves,
        routine=[RoutineGroup(category=c, count=len(v), items=v) for c, v in sorted(groups.items(), key=lambda kv: LABEL[kv[0]])],  # type: ignore[arg-type]
    )
