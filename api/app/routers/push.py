from fastapi import APIRouter, Query

from app import state
from app.models import AlertRules, Digest
from app.services import digest

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/digest", response_model=Digest)
def get_digest(hours: int = Query(24, ge=1, le=24 * 30)) -> Digest:
    return digest.build(hours, state.rules)


@router.get("/rules", response_model=AlertRules)
def get_rules() -> AlertRules:
    return state.rules


@router.put("/rules", response_model=AlertRules)
def put_rules(rules: AlertRules) -> AlertRules:
    state.rules = rules
    return state.rules
