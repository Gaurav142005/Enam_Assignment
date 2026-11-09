from fastapi import APIRouter, Query

from app.models import Company, ResearchReport
from app.services import companies, research

router = APIRouter(prefix="/pull", tags=["pull"])


@router.get("/search", response_model=list[Company])
def search(q: str = Query("", max_length=40)) -> list[Company]:
    return companies.search(q)


@router.get("/research/{ticker}", response_model=ResearchReport)
def get_research(ticker: str) -> ResearchReport:
    return research.build(ticker)
