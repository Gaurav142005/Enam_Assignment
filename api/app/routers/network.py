from fastapi import APIRouter, HTTPException

from app.models import NetworkHint, Person, ReconnectNudge, ThemeGroup
from app.services import filing_people, graph

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/people", response_model=list[Person])
def list_people() -> list[Person]:
    return graph.people()


@router.get("/people/{person_id}", response_model=Person)
def get_person(person_id: str) -> Person:
    if not (p := graph.get(person_id) or filing_people.get(person_id)):
        raise HTTPException(404, "person not found")
    return p


@router.get("/people/{person_id}/connections", response_model=list[NetworkHint])
def person_connections(person_id: str) -> list[NetworkHint]:
    """Second-degree reach / diligence: who I know who has crossed paths with this person."""
    if not (p := graph.get(person_id) or filing_people.get(person_id)):
        raise HTTPException(404, "person not found")
    return graph.who_knows_person(p)


@router.get("/company/{ticker}", response_model=list[NetworkHint])
def company_contacts(ticker: str) -> list[NetworkHint]:
    return graph.who_knows_company(ticker.upper(), limit=10)


@router.get("/themes", response_model=list[ThemeGroup])
def expertise_map() -> list[ThemeGroup]:
    return graph.themes()


@router.get("/reconnect", response_model=list[ReconnectNudge])
def reconnect() -> list[ReconnectNudge]:
    # TODO(network): feed from the live digest instead of the fixture tickers
    from app import state
    from app.services import digest

    d = digest.build(72, state.rules)
    return graph.reconnect({i.ticker for i in [*d.attention, *d.moves]})
