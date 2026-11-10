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
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, Literal

import httpx

from app import config
from app.ingest import store

Tier = Literal["cheap", "strong"]


class Usage:
    """Per-job meter: how many model calls a feature really costs (cache hits are free)."""

    def __init__(self) -> None:
        self.calls = 0
        self.cached = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.by_tier: dict[str, int] = {"cheap": 0, "strong": 0}
        self.models: dict[str, int] = {}

    def as_dict(self) -> dict:
        return {"calls": self.calls, "cached": self.cached, "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "by_tier": self.by_tier, "models": self.models}
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


# httpx timeouts bound the gap between bytes, not the whole request: a "thinking" model that trickles bytes can run
# for minutes. Calls go through this pool so each one gets a true wall-clock deadline; an abandoned call finishes
# in the background and is simply ignored.
_calls = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm")


def _with_deadline(fn, *args, seconds: float, **kwargs):
    fut = _calls.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=seconds)
    except FutureTimeout as e:
        raise httpx.TimeoutException(f"no answer within {seconds:.0f}s") from e


# A model that just timed out or returned 503 is skipped for a while, so the next call doesn't wait on it again.
COOLDOWN_S = 600
_cool_until: dict[str, float] = {}


def _cool(model: str) -> None:
    _cool_until[model] = time.monotonic() + COOLDOWN_S
    log.warning("LLM model %s is overloaded; skipping it for %ds", model, COOLDOWN_S)


def _model(tier: Tier) -> str:
    return config.CHEAP_MODEL if tier == "cheap" else config.STRONG_MODEL


def _gemini(model: str, system: str, prompt: str, timeout: float = 60) -> tuple[str, int, int]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    r = httpx.post(url, params={"key": config.LLM_API_KEY}, json=body, timeout=timeout)
    if r.status_code == 429 and '"quota_limit_value": "0"' in r.text:
        _trip("Gemini quota for this key's project is 0 — create a free key at https://aistudio.google.com/apikey")
    if r.status_code in (401, 403):
        _trip(f"Gemini rejected the key ({r.status_code})")
    if r.status_code != 200:
        raise LLMError(f"gemini {r.status_code}: {r.text[:300]}")
    d = r.json()
    parts = d["candidates"][0]["content"]["parts"]
    meta = d.get("usageMetadata", {})
    return "".join(p.get("text", "") for p in parts), meta.get("promptTokenCount", 0), meta.get("candidatesTokenCount", 0)


def _openai_compat(model: str, system: str, prompt: str, timeout: float = 60) -> tuple[str, int, int]:
    base = config.LLM_BASE_URL.rstrip("/") or "https://api.groq.com/openai/v1"
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }
    r = httpx.post(f"{base}/chat/completions", json=body, headers={"Authorization": f"Bearer {config.LLM_API_KEY}"}, timeout=timeout)
    if r.status_code != 200:
        raise LLMError(f"llm {r.status_code}: {r.text[:300]}")
    d = r.json()
    u = d.get("usage", {})
    return d["choices"][0]["message"]["content"], u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def json_call(tier: Tier, system: str, prompt: str, *, tries: int = 3, usage: Usage | None = None) -> Any:
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
        if usage:
            usage.cached += 1
        return json.loads(hit["response"])

    call = _gemini if config.LLM_PROVIDER == "gemini" else _openai_compat
    full = [model] + [m for m in (config.CHEAP_FALLBACKS if tier == "cheap" else config.STRONG_FALLBACKS) if m != model]
    chain = [m for m in full if _cool_until.get(m, 0) <= time.monotonic()] or full[-1:]
    last: Exception | None = None
    parsed: Any = None
    done = False
    for m in chain:  # overloaded / slow model → next model immediately; rate limit → back off and retry the same one
        for attempt in range(tries):
            if not available():
                raise LLMError(_disabled or "LLM unavailable")
            try:
                budget = config.CHEAP_TIMEOUT if tier == "cheap" else config.STRONG_TIMEOUT
                out = _with_deadline(call, m, system, prompt, timeout=budget, seconds=budget)
                raw, t_in, t_out = out if isinstance(out, tuple) else (out, 0, 0)
                if usage:
                    usage.calls += 1
                    usage.by_tier[tier] += 1
                    usage.models[m] = usage.models.get(m, 0) + 1
                    usage.tokens_in += t_in
                    usage.tokens_out += t_out
                parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```"))
                done = True
                break
            except httpx.TimeoutException as e:
                last = e
                _cool(m)
                break  # a model that's hanging won't recover in seconds: move down the chain
            except (LLMError, json.JSONDecodeError, httpx.TransportError, KeyError) as e:
                last = e
                msg = str(e)
                if any(code in msg for code in (" 500", " 502", " 503", " 504", " 404")):
                    _cool(m)
                    break
                time.sleep(4 * (attempt + 1) if "429" in msg else 1)
        if done:
            break
    if not done:
        raise LLMError(f"{type(last).__name__}: {last}")

    try:
        with store.connect() as con:
            store.upsert(con, "llm_cache", [{"key": key, "model": model, "response": json.dumps(parsed), "created_at": store.now_iso()}])
    except sqlite3.OperationalError:  # a busy database must not cost us an answer we already have
        log.warning("llm cache write skipped (database busy)")
    return parsed


def probe() -> bool:
    """One tiny uncached call so a dead key is caught before a long ingestion run."""
    call = _gemini if config.LLM_PROVIDER == "gemini" else _openai_compat
    try:
        call(config.CHEAP_MODEL, 'Respond with JSON {"ok": true}', "ping", timeout=20)
        return True
    except (LLMError, httpx.TransportError):
        return _disabled is None  # only a permanent failure (zero quota, bad key) trips the breaker
