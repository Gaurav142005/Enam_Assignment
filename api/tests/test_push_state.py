"""Alert rules persist; 'new since last look'; move context; generic titles replaced by summaries (offline, seeded)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import state
from app.ingest import store
from app.main import app
from app.services import digest

client = TestClient(app)
IST = timezone(timedelta(hours=5, minutes=30))


def _seed(now: datetime) -> None:
    def ann(i, hours_ago, cat, desc, text, summary=None):
        return {"id": i, "ticker": "POLYCAB", "filed_at": (now - timedelta(hours=hours_ago)).isoformat(), "nse_desc": desc, "text": text,
                "attachment_url": f"https://example.test/{i}.pdf", "category": cat, "category_source": "nse", "summary": summary, "extra": {"routine": False}}

    with store.connect() as con:
        store.upsert(con, "announcements", [
            ann("a1", 30, "credit_rating", "Credit Rating", "Polycab India Limited has informed the Exchange about Credit Rating", "CRISIL upgraded long-term rating to AA+ from AA."),
            ann("a2", 2, "M&A", "Acquisition", "Polycab India Limited has informed the Exchange about Acquisition of 51% stake in Wiretech for Rs 240 crore"),
        ])


def test_rules_survive_a_restart():
    rules = client.get("/push/rules").json()
    client.put("/push/rules", json={**rules, "price_move_pct": 7.5})
    assert state.get_rules().price_move_pct == 7.5  # read back from SQLite, not process memory


def test_new_since_last_look_and_summary_titles():
    now = datetime.now(timezone.utc)
    _seed(now)
    state.put("brief_seen_at", (now - timedelta(hours=10)).isoformat())
    d = digest.build(72, state.get_rules())
    by_id = {i.id: i for i in d.attention}
    assert d.live and d.new_count == 1
    assert by_id["a2"].is_new and not by_id["a1"].is_new
    assert by_id["a1"].title == "CRISIL upgraded long-term rating to AA+ from AA"  # the model's line replaces the bare label
    assert by_id["a2"].title.startswith("Acquisition of 51% stake")
    client.post("/push/seen")
    assert digest.build(72, state.get_rules()).new_count == 0


def test_move_context_prefers_a_material_filing():
    close = datetime(2026, 11, 6, 15, 30, tzinfo=IST)
    with store.connect() as con:
        store.upsert(con, "announcements", [{"id": "m1", "ticker": "TITAN", "filed_at": close.replace(hour=11).isoformat(), "nse_desc": "Outcome of Board Meeting",
                                             "text": "Financial results for the quarter ended September 30, 2026", "attachment_url": "u", "category": "results",
                                             "category_source": "rules", "summary": None, "extra": {"routine": False}}])
        ctx, url = digest._move_context(con, "TITAN", close)
        none, _ = digest._move_context(con, "INFY", close)
    assert ctx.startswith("Filed that session: Financial results") and url == "u"
    assert none == "No filing or headline that session"
