from fastapi.testclient import TestClient

from app.main import app
from app.services.taxonomy import classify

client = TestClient(app)


def test_digest_ranks_and_collapses():
    d = client.get("/push/digest?hours=24").json()
    assert d["attention"], "material items should surface"
    scores = [i["score"] for i in d["attention"]]
    assert scores == sorted(scores, reverse=True)
    assert all(i["priority"] != "routine" for i in d["attention"])
    assert d["routine"], "routine filings should be grouped, not dropped"


def test_window_filters():
    short = client.get("/push/digest?hours=4").json()
    assert all(i["ticker"] == "POLYCAB" for i in short["attention"])


def test_management_change_is_woven_with_network():
    d = client.get("/push/digest").json()
    cfo = next(i for i in d["attention"] if i["category"] == "management_change")
    assert cfo["person"]["name"] == "Rahul Verma"
    assert any(h["person_id"] == "ananya-iyer" for h in cfo["network"])


def test_rules_change_thresholds():
    rules = client.get("/push/rules").json()
    client.put("/push/rules", json={**rules, "price_move_pct": 10})
    moves = client.get("/push/digest").json()["moves"]
    assert not any(m["kind"] == "price_move" for m in moves)
    client.put("/push/rules", json=rules)


def test_research_works_for_any_ticker():
    r = client.get("/pull/research/TATASTEEL").json()
    assert r["company"]["ticker"] == "TATASTEEL"
    assert len(r["sections"]) == 9
    # offline: no fundamentals could be fetched, so sections degrade to pending instead of erroring
    assert r["fundamentals"] is None and all(s["status"] == "pending" for s in r["sections"])


def test_classifier():
    assert classify("Outcome of Board Meeting - Financial Results for Q2") == "results"
    assert classify("Appointment of Chief Financial Officer") == "management_change"
    assert classify("Something unusual") is None
