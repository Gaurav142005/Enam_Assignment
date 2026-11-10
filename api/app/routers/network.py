from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app import config
from app.models import (
    CompanyPeopleSummary,
    CompanyPerson,
    ContactIn,
    Dossier,
    ImportResult,
    NetworkAnswer,
    NetworkHint,
    Person,
    PersonIn,
    ReconnectNudge,
    ThemeGroup,
)
from app.services import company_people, connections, filing_people, graph, network_query

router = APIRouter(prefix="/network", tags=["network"])
SAMPLE = Path(__file__).resolve().parent.parent / "data" / "network" / "sample_linkedin_connections.csv"
MAX_UPLOAD = 20 * 1024 * 1024  # LinkedIn exports are small; this is generous


@router.get("/people", response_model=list[Person])
def list_people(source: str | None = Query(None, pattern="^(synthetic|linkedin|manual)$")) -> list[Person]:
    people = graph.people()
    if source:
        people = [p for p in people if p.source == source]
    return sorted(people, key=lambda p: (-(p.relationship.strength if p.relationship else 0), p.name))


@router.post("/people", response_model=Person, status_code=201)
def add_person(body: PersonIn) -> Person:
    return connections.add(body)


@router.get("/people/{person_id}", response_model=Person)
def get_person(person_id: str) -> Person:
    if not (p := graph.get(person_id) or filing_people.get(person_id)):
        raise HTTPException(404, "person not found")
    return p


@router.delete("/people/{person_id}", status_code=204)
def delete_person(person_id: str) -> None:
    if not connections.delete(person_id):
        raise HTTPException(404, "only connections you imported or added can be removed")


@router.get("/people/{person_id}/connections", response_model=list[NetworkHint])
def person_connections(person_id: str) -> list[NetworkHint]:
    """Second-degree reach / diligence: who I know who has crossed paths with this person."""
    if not (p := graph.get(person_id) or filing_people.get(person_id)):
        raise HTTPException(404, "person not found")
    return graph.who_knows_person(p)


@router.get("/people/{person_id}/dossier", response_model=Dossier)
def person_dossier(person_id: str) -> Dossier:
    """Diligence on people: career, who knows them, what filings say, what to ask."""
    if not (p := graph.get(person_id) or filing_people.get(person_id)):
        raise HTTPException(404, "person not found")
    return network_query.dossier(p)


@router.post("/people/{person_id}/contact", response_model=Person)
def log_contact(person_id: str, body: ContactIn) -> Person:
    """Log a conversation: keeps 'last spoke' honest and quiets the reconnect nudge."""
    if not (p := graph.get(person_id)) or not p.relationship:
        raise HTTPException(404, "not one of your connections")
    graph.log_contact(person_id, body.on or date.today(), body.note)
    return graph.get(person_id)  # type: ignore[return-value]


@router.get("/ask", response_model=NetworkAnswer)
def ask_network(q: str = Query(..., min_length=2, max_length=200)) -> NetworkAnswer:
    return network_query.ask(q)


@router.get("/config")
def network_config() -> dict[str, bool]:
    return {"public_demo": config.PUBLIC_DEMO}


@router.post("/import/sample", response_model=ImportResult)
def import_sample() -> ImportResult:
    """Import the bundled sample export (made-up people at real companies) to see the import end to end."""
    return connections.import_linkedin(SAMPLE.read_bytes(), SAMPLE.name)


@router.post("/import/linkedin", response_model=ImportResult)
async def import_linkedin(file: UploadFile = File(...)) -> ImportResult:
    if config.PUBLIC_DEMO:
        raise HTTPException(403, "This is a public demo, so uploads are off: anything imported here would be visible to every visitor. Use the sample instead.")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "file too large")
    try:
        return connections.import_linkedin(data, file.filename or "")
    except connections.ImportError_ as e:
        raise HTTPException(422, str(e)) from e


@router.delete("/import/linkedin")
def remove_linkedin_import() -> dict[str, int]:
    return {"removed": connections.remove_import()}


@router.get("/company/{ticker}", response_model=list[NetworkHint])
def company_contacts(ticker: str) -> list[NetworkHint]:
    return graph.who_knows_company(ticker.upper(), limit=10, wide=True)


@router.get("/companies", response_model=list[CompanyPeopleSummary])
def companies_summary() -> list[CompanyPeopleSummary]:
    return company_people.summary()


@router.get("/companies/{ticker}/people", response_model=list[CompanyPerson])
def people_at_company(ticker: str) -> list[CompanyPerson]:
    return company_people.for_company(ticker.upper())


@router.get("/themes", response_model=list[ThemeGroup])
def expertise_map() -> list[ThemeGroup]:
    return graph.themes()


@router.get("/reconnect", response_model=list[ReconnectNudge])
def reconnect() -> list[ReconnectNudge]:
    from app import state
    from app.services import digest

    d = digest.build(96, state.get_rules())
    news: dict[str, str] = {}
    for i in [*d.attention, *d.moves]:  # ranked: the first item per company is the most material
        if i.ticker not in news:
            what = f"{i.results.period} results" if i.results else (CATEGORY_NOUN.get(i.category or "", "") or ("A sharp move" if i.kind != "announcement" else "News"))
            news[i.ticker] = what
    return graph.reconnect(news)[:8]


CATEGORY_NOUN = {"M&A": "A deal", "management_change": "A management change", "litigation": "A legal development", "capex": "A capex announcement",
                 "fund_raise": "A fund raise", "credit_rating": "A rating action", "press_release": "An announcement", "pledging": "A pledge change"}
