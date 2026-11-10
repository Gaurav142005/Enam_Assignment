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
