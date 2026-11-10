from fastapi import APIRouter, HTTPException

from app.models import Company, HoldingIn, HoldingRecord, Thesis, ThesisCheck, ThesisIn
from app.services import companies, holdings, thesis

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=list[Company])
def get_portfolio() -> list[Company]:
    return companies.portfolio()


@router.get("/watchlist", response_model=list[Company])
def get_watchlist() -> list[Company]:
    return companies.watchlist()


@router.get("/holdings", response_model=list[HoldingRecord])
def list_holdings() -> list[HoldingRecord]:
    return holdings.records()


@router.post("/holdings", response_model=HoldingRecord, status_code=201)
def add_holding(body: HoldingIn) -> HoldingRecord:
    """Add a company you own. Its data is fetched in the background; poll GET /portfolio/holdings for `syncing`."""
    try:
        return holdings.add(body)
    except holdings.HoldingError as e:
        raise HTTPException(422, str(e)) from e


@router.put("/holdings/{ticker}", response_model=HoldingRecord)
def edit_holding(ticker: str, body: HoldingIn) -> HoldingRecord:
    try:
        return holdings.update(ticker, body)
    except KeyError as e:
        raise HTTPException(404, "not in your portfolio") from e


@router.delete("/holdings/{ticker}", status_code=204)
def remove_holding(ticker: str) -> None:
    try:
        holdings.remove(ticker)
    except KeyError as e:
        raise HTTPException(404, "not in your portfolio") from e


@router.post("/holdings/reset", response_model=list[HoldingRecord])
def reset_holdings() -> list[HoldingRecord]:
    return holdings.reset()


@router.get("/theses", response_model=list[Thesis])
def list_theses() -> list[Thesis]:
    return list(thesis.all_theses().values())


@router.get("/theses/{ticker}", response_model=Thesis | None)
def get_thesis(ticker: str) -> Thesis | None:
    return thesis.get(ticker)


@router.put("/theses/{ticker}", response_model=Thesis)
def put_thesis(ticker: str, body: ThesisIn) -> Thesis:
    """Save your thesis; recent material filings are re-checked against it in the background."""
    return thesis.save(ticker, body.text)


@router.delete("/theses/{ticker}", status_code=204)
def delete_thesis(ticker: str) -> None:
    thesis.delete(ticker)


@router.get("/theses/{ticker}/checks", response_model=list[ThesisCheck])
def thesis_checks(ticker: str) -> list[ThesisCheck]:
    return thesis.checks_for(ticker)
