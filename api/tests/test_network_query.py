"""Direct network questions, wider who-to-call, contact log, dossier (offline, demo network)."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import graph
from app.services import network_query as nq

client = TestClient(app)


def test_theme_company_role_and_school_questions():
    assert nq.ask("who knows rural lending?").results[0].name == "Kavya Reddy"
    dixon = nq.ask("anyone at Dixon")
    assert dixon.results[0].name == "Rohan Mehta" and dixon.results[0].relation == "insider"
    fin = nq.ask("finance people at Polycab")
    assert [h.name for h in fin.results] == ["Ananya Iyer"]  # role + company → insiders only, and "finance" isn't the lending sector
    assert {h.name for h in nq.ask("IIT Kanpur").results} == {"Rohan Mehta", "Meera Krishnan"}
    assert nq.ask("zzz qqq").results == []


def test_who_to_call_widens_to_peers_and_experts():
    hints = graph.who_knows_company("CGPOWER", limit=5)  # nobody worked there
    assert hints and all(h.relation in ("peer", "expert") for h in hints)
    assert graph.who_knows_company("CGPOWER", wide=False) == []
    assert all(h.relation == "insider" for h in graph.who_knows_company("POLYCAB"))  # know an insider → don't dilute with peers


def test_logging_a_conversation_quiets_the_nudge():
    before = graph.get("vikram-shah").relationship.last_contact
    r = client.post("/network/people/vikram-shah/contact", json={})
    assert r.status_code == 200 and r.json()["relationship"]["last_contact"] != str(before)
    assert all(n.person.id != "vikram-shah" for n in graph.reconnect({"DEEPAKNTR": "A deal"}))
    assert client.post("/network/people/rahul-verma/contact", json={}).status_code == 404  # not a connection


def test_dossier_for_outsider_shows_paths():
    d = client.get("/network/people/rahul-verma/dossier").json()
    assert any(h["person_id"] == "ananya-iyer" for h in d["paths"])


def test_school_names_normalise():
    assert graph._same_org("Indian Institute of Technology, Kanpur", "IIT Kanpur")
    assert graph._same_org("Indian Institute of Management Bangalore", "IIM Bangalore")
    assert not graph._same_org("IIT Kanpur", "IIT Bombay")


def test_dossier_reads_filings_and_notices_what_you_share():
    from app.ingest import store
    from app.services import filing_people

    with store.connect() as con:
        store.upsert(con, "announcements", [{"id": "d1", "ticker": "HDFCBANK", "filed_at": "2026-10-01T10:00:00+05:30", "nse_desc": "Change in Management",
                                             "text": "", "attachment_url": "https://example.test/d1.pdf", "category": "management_change",
                                             "category_source": "nse", "summary": None, "extra": {}}])
        bg = '{"background": "Three decades in banking.", "previous_roles": [{"company": "ICICI Bank", "title": "Executive Director", "years": "2017-2023"}], "education": ["Engineering degree from Indian Institute of Technology, Kanpur"]}'
        con.execute("INSERT INTO people_mentions VALUES ('d1','HDFCBANK','Mr. New Ceo','Managing Director & CEO','appointment','2026-10-01',?, 'llm')", (bg,))
    pid = filing_people.person_id("d1", "Mr. New Ceo")
    d = client.get(f"/network/people/{pid}/dossier").json()
    p = d["person"]
    assert p["name"] == "New Ceo" and p["source"] == "filing" and p["headline"].startswith("Incoming")
    assert p["education"][0] == {"school": "Indian Institute of Technology, Kanpur", "degree": "Engineering degree", "start": None, "end": None}
    assert d["shared_with_you"] == ["You are both IIT Kanpur alumni"]
    assert {h["name"] for h in d["paths"]} >= {"Rohan Mehta", "Meera Krishnan"}  # fellow alumni in the network
    assert d["in_filings"][0]["title"] == "Appointed as Managing Director & CEO"
