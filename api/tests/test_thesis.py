"""Theses: save, judged per filing once, shown on the Brief (offline; model stubbed)."""

import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import config, llm, state
from app.ingest import store
from app.main import app
from app.services import digest, thesis

client = TestClient(app)


def _seed():
    now = datetime.now(timezone.utc)
    rows = [
        {"id": "r1", "ticker": "POLYCAB", "filed_at": (now - timedelta(days=2)).isoformat(), "nse_desc": "Outcome of Board Meeting",
         "text": "Financial results for the quarter ended September 30, 2026", "attachment_url": None, "category": "results",
         "category_source": "rules", "summary": None,
         "extra": {"routine": False, "results": {"period": "Q2 FY27", "unit": "₹ cr", "rows": [{"metric": "Revenue", "value": 9899, "qoq_pct": 20.6, "yoy_pct": 52.8}]}}},
        {"id": "r2", "ticker": "POLYCAB", "filed_at": (now - timedelta(days=1)).isoformat(), "nse_desc": "Litigation", "text": "NCLAT order on insolvency petition",
         "attachment_url": None, "category": "litigation", "category_source": "nse", "summary": None, "extra": {"routine": False}},
    ]
    with store.connect() as con:
        store.upsert(con, "announcements", rows)


def test_thesis_checks_are_batched_cached_and_shown(monkeypatch):
    _seed()
    monkeypatch.setattr(config, "LLM_API_KEY", "test")
    calls = []

    def fake(model, system, prompt, **k):
        calls.append(prompt)
        ids = [x["id"] for x in json.loads(prompt.split("New filings:\n", 1)[1])]
        verdict = {"r1": ("supports", "Revenue +53% YoY confirms the growth runway"), "r2": ("neutral", "Procedural")}
        return json.dumps({"items": [{"id": i, "stance": verdict[i][0], "why": verdict[i][1]} for i in ids]}), 10, 5

    monkeypatch.setattr(llm, "_gemini", fake)
    monkeypatch.setattr(thesis.threading, "Thread", lambda target, args, **k: type("T", (), {"start": lambda self: target(*args)})())

    r = client.put("/portfolio/theses/POLYCAB", json={"text": "Wires & cables volume growth above 20% for three years"})
    assert r.status_code == 200 and len(calls) == 1  # both filings judged in one call
    assert [c["stance"] for c in client.get("/portfolio/theses/POLYCAB/checks").json()] == ["supports"]  # neutral hidden
    assert thesis.check("POLYCAB") == 0 and len(calls) == 1  # already judged against this thesis version

    d = digest.build(72, state.get_rules())
    card = next(i for i in d.attention if i.id == "r1")
    assert card.thesis and card.thesis.stance == "supports"

    client.put("/portfolio/theses/POLYCAB", json={"text": "Margins hold above 13% despite copper volatility"})
    assert len(calls) == 2  # a new thesis is a new question
    assert client.get("/portfolio/theses/POLYCAB").json()["text"].startswith("Margins")
    client.delete("/portfolio/theses/POLYCAB")
    assert client.get("/portfolio/theses/POLYCAB").json() is None
