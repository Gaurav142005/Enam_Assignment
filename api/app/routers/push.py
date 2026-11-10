from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app import state
from app.models import AlertRules, Digest
from app.services import digest, watch

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/digest", response_model=Digest)
def get_digest(hours: int = Query(24, ge=1, le=24 * 90)) -> Digest:
    return digest.build(hours, state.get_rules())


@router.post("/seen")
def mark_seen() -> dict[str, str]:
    """The investor has looked at the Brief; anything filed after this is 'new' next time."""
    now = datetime.now(timezone.utc).isoformat()
    state.put("brief_seen_at", now)
    return {"seen_at": now}


@router.get("/rules", response_model=AlertRules)
def get_rules() -> AlertRules:
    return state.get_rules()


@router.put("/rules", response_model=AlertRules)
def put_rules(rules: AlertRules) -> AlertRules:
    return state.set_rules(rules)


@router.post("/refresh")
def refresh() -> dict:
    """Re-pull filings and prices for the whole portfolio in the background. Poll GET /push/refresh."""
    return watch.start_refresh()


@router.get("/refresh")
def refresh_status() -> dict:
    return watch.status()
