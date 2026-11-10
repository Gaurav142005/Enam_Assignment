from fastapi import APIRouter, HTTPException, Query

from app.models import Answer, AskIn, Company, ResearchJob, ResearchReport
from app.services import companies, deep_research, qa, research

router = APIRouter(prefix="/pull", tags=["pull"])


@router.get("/search", response_model=list[Company])
def search(q: str = Query("", max_length=40)) -> list[Company]:
    return companies.search(q)


@router.get("/research/{ticker}", response_model=ResearchReport)
def get_research(ticker: str) -> ResearchReport:
    return research.build(ticker)


@router.post("/deep/{ticker}", response_model=ResearchJob)
def start_deep_research(ticker: str, refresh: bool = False) -> ResearchJob:
    """Starts (or returns a fresh cached) deep-research run. Poll /pull/deep/jobs/{id}."""
    return deep_research.start(ticker, refresh=refresh)


@router.get("/deep/jobs/{job_id}", response_model=ResearchJob)
def deep_research_job(job_id: str) -> ResearchJob:
    if not (job := deep_research.get_job(job_id)):
        raise HTTPException(404, "job not found")
    return job


@router.get("/deep/{ticker}/latest", response_model=ResearchJob)
def latest_deep_research(ticker: str) -> ResearchJob:
    if not (job := deep_research.latest(ticker.upper())):
        raise HTTPException(404, "no research yet")
    return job


@router.post("/ask/{ticker}", response_model=Answer)
def ask_company(ticker: str, body: AskIn) -> Answer:
    """A question answered from the company's own transcripts, decks and annual report, with page cites."""
    return qa.ask(ticker, body.question)
