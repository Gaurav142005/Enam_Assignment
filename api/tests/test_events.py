"""Upcoming events: date extraction, forward vs past notices, and the digest's 'coming up' (offline)."""

from datetime import date, datetime, timedelta, timezone

from app import state
from app.ingest import events, store
from app.services import digest


def test_find_dates_formats():
    f = events.find_dates
    assert f("participating in the analyst conferences on 18th and 19th November 2026") == [date(2026, 11, 18), date(2026, 11, 19)]
    assert f("CLSA India Forum, scheduled to be held on November 16, 2026 at Mumbai") == [date(2026, 11, 16)]
    assert f("meeting on 16 November, 2026 and on 2.12.2026") == [date(2026, 11, 16), date(2026, 12, 2)]
    assert f("no dates here") == []
    assert events.find_time("call at 4:00 PM IST") == "16:00" and events.find_time("at 16.30 hrs") == "16:30"


def _ann(i, days_ago, cat, text, url=None):
    return {"id": i, "ticker": "POLYCAB", "filed_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(), "nse_desc": "x",
            "text": text, "attachment_url": url, "category": cat, "category_source": "nse", "summary": None, "extra": {"routine": True}}


def test_forward_notices_become_events_and_past_ones_dont():
    soon = date.today() + timedelta(days=5)
    s = f"{soon.day} {soon:%B} {soon.year}"
    with store.connect() as con:
        store.upsert(con, "announcements", [
            _ann("e1", 2, "investor_meetings", f"The Company will be participating in the Jefferies India Forum on {s}."),
            _ann("e2", 1, "earnings_call", f"Intimation of earnings conference call scheduled on {s} at 4:00 PM IST"),
            _ann("e3", 1, "earnings_call", f"Transcript of the earnings call held on {s}"),
        ])
        rows = {r["kind"]: r for r in events.from_filings(con, {"POLYCAB"}, read_pdfs=False)}
    assert set(rows) == {"investor_meetings", "earnings_call"}
    assert rows["investor_meetings"]["title"] == "Analyst / investor meetings: Jefferies India Forum"
    assert rows["earnings_call"]["time"] == "16:00" and rows["earnings_call"]["date"] == soon.isoformat()


def test_digest_lists_upcoming_soonest_first():
    today = date.today()
    with store.connect() as con:
        store.upsert(con, "announcements", [_ann("x", 1, "dividend", "placeholder")])  # makes the store 'live'
        store.upsert(con, "events", [
            {"id": "a", "ticker": "TITAN", "date": (today + timedelta(days=3)).isoformat(), "end_date": None, "time": None, "kind": "results",
             "title": "Results", "detail": None, "source": "NSE event calendar", "url": None, "updated_at": store.now_iso()},
            {"id": "b", "ticker": "DIXON", "date": (today + timedelta(days=1)).isoformat(), "end_date": None, "time": "16:00", "kind": "earnings_call",
             "title": "Earnings call", "detail": None, "source": "Exchange filing", "url": None, "updated_at": store.now_iso()},
            {"id": "c", "ticker": "TITAN", "date": (today - timedelta(days=2)).isoformat(), "end_date": None, "time": None, "kind": "agm",
             "title": "General meeting", "detail": None, "source": "Exchange filing", "url": None, "updated_at": store.now_iso()},
        ])
    up = digest.build(24, state.get_rules()).upcoming
    assert [u.id for u in up] == ["b", "a"]  # past events dropped, soonest first
    assert up[1].ask and up[1].ask.name == "Priya Desai"  # results coming: someone who knows Titan
