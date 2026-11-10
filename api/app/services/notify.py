"""Push notifications (Web Push / VAPID): the moment something crosses the investor's bar, without opening the app.

What's sent after each refresh, newest first, at most MAX_PER_RUN (then one summary):
  • critical items, and high-priority items in categories the investor marked in Alerts
  • any filing that challenges the investor's thesis
  • unusual price / volume moves past their thresholds
Each item is sent once (tracked by id). Works on Android and desktop browsers, and on iPhone once FINN is added to
the home screen (iOS 16.4+). Subscriptions that the push service reports as gone are removed.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta, timezone

from app import config, state
from app.ingest import store
from app.models import PushItem

log = logging.getLogger(__name__)
MAX_PER_RUN = 4
WINDOW_HOURS = 48  # never notify about something older than this, even on a first run


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def vapid_keys() -> tuple[str, str]:
    """(public key for the browser, private key PEM). From env if set, else generated once and kept in the store."""
    if config.VAPID_PUBLIC and config.VAPID_PRIVATE:
        return config.VAPID_PUBLIC, config.VAPID_PRIVATE
    saved = state.get("vapid")
    if saved:
        return saved["public"], saved["private"]
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid01

    v = Vapid01()
    v.generate_keys()
    public = _b64url(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    private = v.private_pem().decode()
    state.put("vapid", {"public": public, "private": private})
    return public, private


def subscribe(sub: dict, agent: str | None) -> int:
    with store.connect() as con:
        con.execute("INSERT OR REPLACE INTO push_subscriptions VALUES (?,?,?,?)", (sub["endpoint"], json.dumps(sub), agent, store.now_iso()))
        return con.execute("SELECT COUNT(*) FROM push_subscriptions").fetchone()[0]


def unsubscribe(endpoint: str) -> None:
    with store.connect() as con:
        con.execute("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))


def count() -> int:
    with store.connect() as con:
        return con.execute("SELECT COUNT(*) FROM push_subscriptions").fetchone()[0]


def send(title: str, body: str, url: str = "/", tag: str | None = None) -> int:
    """Deliver to every subscribed device. Returns how many accepted it."""
    from pywebpush import WebPushException, webpush

    _, private = vapid_keys()
    with store.connect() as con:
        subs = [(r["endpoint"], json.loads(r["subscription"])) for r in con.execute("SELECT endpoint, subscription FROM push_subscriptions")]
    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    ok = 0
    for endpoint, sub in subs:
        try:
            webpush(subscription_info=sub, data=payload, vapid_private_key=private, vapid_claims={"sub": config.VAPID_SUBJECT}, timeout=10, ttl=6 * 3600)
            ok += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):  # the device unsubscribed or the subscription expired
                unsubscribe(endpoint)
            else:
                log.warning("push to %s… failed: %s", endpoint[:40], e)
        except Exception as e:  # network trouble must not break a refresh
            log.warning("push failed: %s", e)
    return ok


def _worth_it(i: PushItem, categories: set[str]) -> bool:
    if i.thesis and i.thesis.stance == "challenges":
        return True
    if i.kind != "announcement":
        return True  # moves already passed the investor's own thresholds
    return i.priority == "critical" or (i.priority == "high" and (i.category or "") in categories)


def _message(i: PushItem) -> tuple[str, str]:
    if i.kind != "announcement":
        return f"{i.ticker} {i.change_pct:+.1f}%" if i.change_pct is not None else i.ticker, f"{i.title}. {i.context or ''}".strip()
    if i.results:
        rows = {r.metric: r for r in i.results.rows}
        rev, pat = rows.get("Revenue"), rows.get("PAT")
        nums = ", ".join(f"{k} {v.yoy_pct:+.0f}% YoY" for k, v in (("revenue", rev), ("PAT", pat)) if v and v.yoy_pct is not None)
        body = f"{i.results.period} results: {nums}" if nums else f"{i.results.period} results"
    else:
        body = i.summary or i.title
    if i.thesis and i.thesis.stance == "challenges":
        body = f"Challenges your thesis: {i.thesis.why}"
    elif i.network:
        body += f" · Ask {i.network[0].name}"
    title = f"{i.ticker} · {i.title if not i.results else i.company_name}"
    return title[:80], body[:180]


def notify_new() -> int:
    """After a refresh: push anything new that crosses the bar. Returns notifications sent."""
    if not count():
        return 0
    from app.services import digest

    rules = state.get_rules()
    d = digest.build(WINDOW_HOURS, rules)
    with store.connect() as con:
        sent = {r["item_id"] for r in con.execute("SELECT item_id FROM push_sent")}
    fresh = [i for i in [*d.attention, *d.moves] if i.id not in sent and _worth_it(i, set(rules.categories))]
    fresh.sort(key=lambda i: i.at, reverse=True)
    if not fresh:
        return 0
    n = 0
    for i in fresh[:MAX_PER_RUN]:
        title, body = _message(i)
        url = f"/company/{i.ticker}" if i.kind != "announcement" else f"/#card-{i.id}"
        n += bool(send(title, body, url, tag=i.id))
    if len(fresh) > MAX_PER_RUN:
        extra = len(fresh) - MAX_PER_RUN
        n += bool(send("FINN", f"{extra} more item{'s' if extra > 1 else ''} in your Brief", "/", tag="more"))
    with store.connect() as con:
        con.executemany("INSERT OR IGNORE INTO push_sent VALUES (?,?)", [(i.id, store.now_iso()) for i in fresh])
        con.execute("DELETE FROM push_sent WHERE sent_at < ?", ((datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),))
    return n
