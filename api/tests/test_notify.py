"""Web Push: keys, subscriptions, what gets sent, sent once, dead subscriptions dropped (offline; push service stubbed)."""

from datetime import datetime, timedelta, timezone

import pywebpush
from fastapi.testclient import TestClient

from app.ingest import store
from app.main import app
from app.services import notify

client = TestClient(app)
SUB = {"endpoint": "https://push.example.test/abc", "keys": {"p256dh": "BPk", "auth": "xyz"}}


def _seed():
    now = datetime.now(timezone.utc)
    with store.connect() as con:
        store.upsert(con, "announcements", [
            {"id": "n1", "ticker": "TITAN", "filed_at": (now - timedelta(hours=3)).isoformat(), "nse_desc": "Outcome of Board Meeting",
             "text": "Financial results for the quarter ended September 30, 2026", "attachment_url": None, "category": "results", "category_source": "rules",
             "summary": None, "extra": {"routine": False, "results": {"period": "Q2 FY27", "unit": "₹ cr", "rows": [
                 {"metric": "Revenue", "value": 100, "qoq_pct": 1.0, "yoy_pct": 10.1}, {"metric": "PAT", "value": 10, "qoq_pct": 2.0, "yoy_pct": 113.7}]}}},
            {"id": "n2", "ticker": "INFY", "filed_at": (now - timedelta(hours=2)).isoformat(), "nse_desc": "Trading Window", "text": "Trading window closure",
             "attachment_url": None, "category": "unclassified", "category_source": "nse", "summary": None, "extra": {"routine": True}},
        ])


def test_keys_are_stable_and_subscriptions_validated():
    k1 = client.get("/push/notifications").json()["public_key"]
    assert len(k1) > 80 and client.get("/push/notifications").json()["public_key"] == k1  # generated once, then reused
    assert client.post("/push/notifications/subscribe", json={"endpoint": "http://x", "keys": {}}).status_code == 422
    assert client.post("/push/notifications/subscribe", json=SUB).json()["devices"] == 1


def test_only_what_crosses_the_bar_is_sent_and_only_once(monkeypatch):
    _seed()
    client.post("/push/notifications/subscribe", json=SUB)
    sent = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **k: sent.append(k["data"]))
    assert notify.notify_new() == 1  # the results card, not the routine trading-window notice
    assert "TITAN" in sent[0] and "PAT +114% YoY" in sent[0] and "Ask Priya Desai" in sent[0]
    assert notify.notify_new() == 0  # already sent


def test_gone_subscriptions_are_removed(monkeypatch):
    client.post("/push/notifications/subscribe", json=SUB)

    class Gone:
        status_code = 410

    def boom(**k):
        raise pywebpush.WebPushException("gone", response=Gone())

    monkeypatch.setattr(pywebpush, "webpush", boom)
    assert notify.send("t", "b") == 0 and notify.count() == 0
