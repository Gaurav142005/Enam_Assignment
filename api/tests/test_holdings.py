"""Editable portfolio: seed from the demo file, add / edit / remove / reset (offline; backfill stubbed)."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import companies, holdings

client = TestClient(app)


def _offline(monkeypatch):
    monkeypatch.setattr(holdings, "nse_listing", lambda: [("TATASTEEL", "Tata Steel Limited")])
    monkeypatch.setattr(holdings, "_sync_then_price", lambda t, fill: holdings._syncing.discard(t))


def test_seeded_from_demo_then_editable(monkeypatch):
    _offline(monkeypatch)
    start = client.get("/portfolio/holdings").json()
    assert len(start) == 18 and start[0]["ticker"] == "RELIANCE"

    r = client.post("/portfolio/holdings", json={"ticker": "tatasteel", "qty": 500, "avg_cost": 150})
    assert r.status_code == 201 and r.json()["name"] == "Tata Steel" and r.json()["syncing"]
    assert "TATASTEEL" in {c.ticker for c in companies.portfolio()}
    assert companies.positions()["TATASTEEL"]["qty"] == 500

    assert client.post("/portfolio/holdings", json={"ticker": "TATASTEEL", "qty": 1}).status_code == 422  # duplicate
    assert client.post("/portfolio/holdings", json={"ticker": "NOTREAL", "qty": 1}).status_code == 422  # not listed
    assert client.post("/portfolio/holdings", json={"ticker": "TATASTEEL", "qty": 0}).status_code == 422  # validation

    assert client.put("/portfolio/holdings/TATASTEEL", json={"ticker": "TATASTEEL", "qty": 800}).json()["avg_cost"] == 150
    assert client.delete("/portfolio/holdings/POLYCAB").status_code == 204
    assert "POLYCAB" not in companies.positions()
    assert client.delete("/portfolio/holdings/POLYCAB").status_code == 404

    assert len(client.post("/portfolio/holdings/reset").json()) == 18


def test_removing_everything_does_not_reseed():
    for h in client.get("/portfolio/holdings").json():
        client.delete(f"/portfolio/holdings/{h['ticker']}")
    companies.invalidate()
    assert client.get("/portfolio/holdings").json() == []
