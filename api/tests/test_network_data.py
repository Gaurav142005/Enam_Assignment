"""LinkedIn import, manual connections and company-people matching (offline)."""

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.ingest import store
from app.ingest.people_sources import clean_name, resolve_ticker, same_person
from app.main import app
from app.services import company_people, graph

client = TestClient(app)
SAMPLE = Path(__file__).resolve().parent.parent / "app" / "data" / "network" / "sample_linkedin_connections.csv"
NSE = {"polycab": "POLYCAB", "dixon technologies": "DIXON", "hdfc bank": "HDFCBANK", "larsen and toubro": "LT"}


def _offline_index(monkeypatch):
    from app.ingest import people_sources

    people_sources.nse_companies.cache_clear()
    monkeypatch.setattr(people_sources, "nse_companies", lambda: NSE)


def test_names_and_matching():
    assert clean_name("Mr. Anup Bagchi B.Tech, PGDM") == "Anup Bagchi"
    assert same_person("V S Rangan", "Vedanthachari Srinivasa Rangan")
    assert same_person("Rakesh Talati", "Rakeshkumar Talati")
    assert not same_person("Bharat Jaisinghani", "Nikhil Jaisinghani")


def test_resolve_ticker(monkeypatch):
    _offline_index(monkeypatch)
    assert resolve_ticker("Polycab India Limited") == "POLYCAB"
    assert resolve_ticker("Dixon Technologies (India) Ltd") == "DIXON"
    assert resolve_ticker("Zomato") == "ETERNAL"  # former name, via alias
    assert resolve_ticker("McKinsey & Company") is None


def test_linkedin_import_sync_and_remove(monkeypatch):
    _offline_index(monkeypatch)
    data = SAMPLE.read_bytes()
    r = client.post("/network/import/linkedin", files={"file": ("Connections.csv", data, "text/csv")}).json()
    assert r["total"] == 15 and r["added"] == 15 and r["at_portfolio"] >= 5
    assert any(l["ticker"] == "POLYCAB" and l["in_portfolio"] for l in r["linked"])
    # they now show up as "who can help" for that company
    assert any(h.name == "Aditi Kulkarni" for h in graph.who_knows_company("POLYCAB", limit=10))
    # emails are never stored
    with store.connect() as con:
        assert "email" not in [c[1] for c in con.execute("PRAGMA table_info(people)")]

    # re-upload as a zip with one person removed → full sync
    lines = [l for l in data.decode().splitlines() if "rohit-bansal" not in l]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Basic_LinkedInDataExport/Connections.csv", "\n".join(lines))
    r2 = client.post("/network/import/linkedin", files={"file": ("export.zip", buf.getvalue(), "application/zip")}).json()
    assert (r2["total"], r2["updated"], r2["removed"]) == (14, 14, 1)

    assert client.delete("/network/import/linkedin").json()["removed"] == 14
    assert not any(p.source == "linkedin" for p in graph.people())


def test_bad_upload_is_explained():
    r = client.post("/network/import/linkedin", files={"file": ("x.csv", b"name,company\na,b", "text/csv")})
    assert r.status_code == 422 and "First Name" in r.json()["detail"]


def test_add_and_delete_connection(monkeypatch):
    _offline_index(monkeypatch)
    body = {"name": "Mr. Test Person", "current_title": "CFO", "current_company": "HDFC Bank Ltd", "context": "College friend",
            "strength": 0.8, "expertise": ["banking", " "], "past_roles": [{"company": "Polycab India", "title": "Analyst", "start": 2015, "end": 2018}]}
    p = client.post("/network/people", json=body).json()
    assert p["name"] == "Test Person" and p["source"] == "manual" and p["expertise"] == ["banking"]
    assert [pos["ticker"] for pos in p["positions"]] == ["HDFCBANK", "POLYCAB"]
    assert client.get(f"/network/people/{p['id']}").status_code == 200
    assert client.delete(f"/network/people/{p['id']}").status_code == 204
    assert client.delete("/network/people/ananya-iyer").status_code == 404  # demo people can't be deleted


def test_company_people_marks_connections_and_leavers(monkeypatch):
    _offline_index(monkeypatch)
    with store.connect() as con:
        store.upsert(con, "company_people", [
            {"id": "c-POLYCAB-test-cfo", "ticker": "POLYCAB", "name": "Test Cfo", "name_key": "test cfo", "role": "Chief Financial Officer",
             "kind": "executive", "status": "current", "since": None, "year_born": None, "sources": ["Yahoo Finance officers"],
             "as_of": "2024-12-31", "updated_at": store.now_iso()},
            {"id": "c-POLYCAB-old-director", "ticker": "POLYCAB", "name": "Old Director", "name_key": "old director",
             "role": "Non-executive independent director", "kind": "independent", "status": "current", "since": None, "year_born": None,
             "sources": ["NSE corporate-governance filing"], "as_of": "2024-12-31", "updated_at": store.now_iso()},
        ])
        store.upsert(con, "announcements", [{"id": "t1", "ticker": "POLYCAB", "filed_at": "2026-08-01T10:00:00+05:30", "nse_desc": "Cessation",
                                             "text": "", "attachment_url": None, "category": "management_change", "category_source": "nse",
                                             "summary": None, "extra": {}}])
        con.execute("INSERT INTO people_mentions VALUES ('t1','POLYCAB','Old Director','Director','resigned','2026-08-01',NULL,'xbrl')")
    client.post("/network/people", json={"name": "Test Cfo", "current_company": "Polycab India", "current_title": "CFO"})
    people = {p.name: p for p in company_people.for_company("POLYCAB")}
    assert people["Test Cfo"].connection is not None  # same name AND same employer → it's your connection
    assert people["Old Director"].status == "former"


def test_public_demo_blocks_uploads_but_offers_the_sample(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "PUBLIC_DEMO", True)
    assert client.get("/network/config").json() == {"public_demo": True}
    r = client.post("/network/import/linkedin", files={"file": ("Connections.csv", SAMPLE.read_bytes(), "text/csv")})
    assert r.status_code == 403
    assert client.post("/network/import/sample").json()["total"] == 15
