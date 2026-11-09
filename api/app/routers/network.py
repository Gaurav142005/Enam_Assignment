from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models import (CompanyPeopleSummary, CompanyPerson, ImportResult, NetworkHint, Person, PersonIn, ReconnectNudge,
                        ThemeGroup)
from app.services import company_people, connections, filing_people, graph

router = APIRouter(prefix="/network", tags=["network"])
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


@router.post("/import/linkedin", response_model=ImportResult)
async def import_linkedin(file: UploadFile = File(...)) -> ImportResult:
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
    return graph.who_knows_company(ticker.upper(), limit=10)


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

    d = digest.build(72, state.rules)
    return graph.reconnect({i.ticker for i in [*d.attention, *d.moves]})[:8]
