from fastapi import APIRouter

from app.models import NewsItem
from app.services import news

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/{ticker}", response_model=list[NewsItem])
def company_news(ticker: str) -> list[NewsItem]:
    return news.recent(ticker)
