"""Per-investor settings, persisted in SQLite (single investor in the prototype; keyed by user in a real deployment)."""

from __future__ import annotations

import json
from typing import Any

from app.ingest import store
from app.models import AlertRules


def get(key: str, default: Any = None) -> Any:
    with store.connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def put(key: str, value: Any) -> None:
    with store.connect() as con:
        con.execute("INSERT OR REPLACE INTO settings VALUES (?,?,?)", (key, json.dumps(value), store.now_iso()))


def get_rules() -> AlertRules:
    raw = get("alert_rules")
    return AlertRules.model_validate(raw) if raw else AlertRules()


def set_rules(rules: AlertRules) -> AlertRules:
    put("alert_rules", rules.model_dump())
    return rules
