from fastapi import APIRouter

from app.models import Company
from app.services import companies

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=list[Company])
def get_portfolio() -> list[Company]:
    return companies.portfolio()


@router.get("/watchlist", response_model=list[Company])
def get_watchlist() -> list[Company]:
    return companies.watchlist()
