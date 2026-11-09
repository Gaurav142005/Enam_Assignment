"""Model routing. One place decides which model does which job, so cost stays visible.

  cheap  → bulk: classify ambiguous filings, extract people from management-change letters
  strong → reasoning: promised-vs-delivered, bull/bear (Pull phase)

Every call is cached in SQLite by hash(model, system, prompt), so a filing is never sent twice.
With no API key configured, `available()` is False and callers skip the LLM step gracefully.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Literal

import httpx

from app import config
from app.ingest import store

Tier = Literal["cheap", "strong"]
log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


_disabled: str | None = None  # circuit breaker: set when the provider says this key can never succeed


def available() -> bool:
    return bool(config.LLM_API_KEY) and _disabled is None


def _trip(reason: str) -> None:
    global _disabled
    if _disabled is None:
        _disabled = reason
        log.warning("LLM disabled for this run: %s", reason)


def _model(tier: Tier) -> str:
    return config.CHEAP_MODEL if tier == "cheap" else config.STRONG_MODEL


def _gemini(model: str, system: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    r = httpx.post(url, params={"key": config.LLM_API_KEY}, json=body, timeout=120)
    if r.status_code == 429 and '"quota_limit_value": "0"' in r.text:
        _trip("Gemini quota for this key's project is 0 — create a free key at https://aistudio.google.com/apikey")
    if r.status_code in (401, 403):
        _trip(f"Gemini rejected the key ({r.status_code})")
    if r.status_code != 200:
        raise LLMError(f"gemini {r.status_code}: {r.text[:300]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _openai_compat(model: str, system: str, prompt: str) -> str:
    base = config.LLM_BASE_URL.rstrip("/") or "https://api.groq.com/openai/v1"
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }
    r = httpx.post(f"{base}/chat/completions", json=body, headers={"Authorization": f"Bearer {config.LLM_API_KEY}"}, timeout=120)
    if r.status_code != 200:
        raise LLMError(f"llm {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def json_call(tier: Tier, system: str, prompt: str, *, tries: int = 3) -> Any:
    """Ask for JSON, get parsed JSON. Cached forever by (model, system, prompt)."""
    if not config.LLM_API_KEY:
        raise LLMError("no LLM API key configured (set GEMINI_API_KEY or FINN_LLM_API_KEY)")
    if _disabled:
        raise LLMError(_disabled)
    model = _model(tier)
    key = hashlib.sha256(f"{model}\0{system}\0{prompt}".encode()).hexdigest()
    with store.connect() as con:
        hit = con.execute("SELECT response FROM llm_cache WHERE key=?", (key,)).fetchone()
    if hit:
        return json.loads(hit["response"])

    call = _gemini if config.LLM_PROVIDER == "gemini" else _openai_compat
    last: Exception | None = None
    for attempt in range(tries):
        if not available():
            raise LLMError(_disabled or "LLM unavailable")
        try:
            raw = call(model, system, prompt)
            parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```"))
            break
        except (LLMError, json.JSONDecodeError, httpx.TransportError, KeyError) as e:
            last = e
            # free tiers rate-limit hard; back off and retry
            time.sleep(4 * (attempt + 1) if "429" in str(e) else 1)
    else:
        raise LLMError(str(last))

    with store.connect() as con:
        store.upsert(con, "llm_cache", [{"key": key, "model": model, "response": json.dumps(parsed), "created_at": store.now_iso()}])
    return parsed


def probe() -> bool:
    """One tiny uncached call so a dead key is caught before a long ingestion run."""
    call = _gemini if config.LLM_PROVIDER == "gemini" else _openai_compat
    try:
        call(config.CHEAP_MODEL, 'Respond with JSON {"ok": true}', "ping")
        return True
    except (LLMError, httpx.TransportError):
        return _disabled is None  # only a permanent failure (zero quota, bad key) trips the breaker
