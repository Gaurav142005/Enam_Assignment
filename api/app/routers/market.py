from fastapi import APIRouter, Query

from app.models import PerfPeriod, PortfolioPerformance, PriceHistory
from app.services import market

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/portfolio", response_model=PortfolioPerformance)
def portfolio_performance(period: PerfPeriod = "1M") -> PortfolioPerformance:
    return market.performance(period)


@router.get("/prices/{ticker}", response_model=PriceHistory)
def prices(ticker: str, range: str = Query("6M", pattern="^(1M|3M|6M|1Y|3Y|5Y)$")) -> PriceHistory:  # noqa: A002
    return market.history(ticker, range)
