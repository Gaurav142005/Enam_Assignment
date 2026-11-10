from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import state
from app.models import AlertRules, Digest
from app.services import digest, notify, watch

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


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: dict[str, str]


class Unsubscribe(BaseModel):
    endpoint: str


@router.get("/notifications")
def notifications_info() -> dict:
    """The VAPID public key the browser needs to subscribe, and how many devices are subscribed."""
    public, _ = notify.vapid_keys()
    return {"public_key": public, "devices": notify.count()}


@router.post("/notifications/subscribe")
def subscribe(body: SubscriptionIn, request: Request) -> dict:
    if not body.endpoint.startswith("https://") or not {"p256dh", "auth"} <= set(body.keys):
        raise HTTPException(422, "not a Web Push subscription")
    return {"devices": notify.subscribe(body.model_dump(), request.headers.get("user-agent"))}


@router.post("/notifications/unsubscribe")
def unsubscribe(body: Unsubscribe) -> dict:
    notify.unsubscribe(body.endpoint)
    return {"devices": notify.count()}


@router.post("/notifications/test")
def test_notification() -> dict:
    sent = notify.send("FINN", "Notifications are on. You'll hear about critical filings, thesis challenges and unusual moves.", "/", tag="test")
    return {"sent": sent}
