"""Check whether a Gemini API key can actually generate content, and explain any failure.

Usage (from api/):
    uv run python scripts/test_gemini.py                      # key from ../.env or api/.env (GEMINI_API_KEY)
    uv run python scripts/test_gemini.py gemini-3.8-flash     # test specific model(s)

It never prints the key itself.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.8-flash", "gemini-2.5-flash"]


def load_key() -> tuple[str, str]:
    if k := os.getenv("GEMINI_API_KEY"):
        return k.strip(), "environment"
    here = Path(__file__).resolve().parent.parent
    for env in (here.parent / ".env", here / ".env"):
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'"), str(env)
    return "", "nowhere"


def explain_429(err: dict) -> str:
    """Google returns 429 for three very different reasons. Tell them apart."""
    meta, retry = {}, None
    for d in err.get("details", []):
        meta = d.get("metadata", meta) if "metadata" in d else meta
        if d.get("@type", "").endswith("QuotaFailure"):
            v = (d.get("violations") or [{}])[0]
            meta = {**meta, "quota_limit": v.get("quotaId", ""), "quota_limit_value": v.get("quotaValue", meta.get("quota_limit_value"))}
        if d.get("@type", "").endswith("RetryInfo"):
            retry = d.get("retryDelay")
    limit = str(meta.get("quota_limit_value", "?"))
    name = meta.get("quota_limit") or meta.get("quota_metric") or "?"
    if limit == "0":
        return (f"quota limit is 0 ({name}). This key's project has NO Gemini quota — waiting won't help.\n"
                "     → Create a key in Google AI Studio (https://aistudio.google.com/apikey), which comes with the free tier,\n"
                "       or enable billing on the Google Cloud project this key belongs to.")
    if "PerDay" in name or "per day" in err.get("message", "").lower():
        return f"daily quota used up ({name}, limit {limit}). Resets at midnight Pacific time."
    return f"rate-limited ({name}, limit {limit}/min). Transient — retry{f' after {retry}' if retry else ' in a minute'}."


def main() -> int:
    key, source = load_key()
    if not key:
        print("✗ No GEMINI_API_KEY found (env var, repo-root .env, or api/.env).")
        return 1
    kind = "AI Studio-style (AIza…)" if key.startswith("AIza") else "Google Cloud-style (AQ.…)" if key.startswith("AQ.") else "unrecognised format"
    print(f"Key: loaded from {source} · {len(key)} chars · {kind}")

    # 1. Is the key valid at all? (listing models costs no generation quota)
    r = httpx.get(f"{BASE}/models", params={"key": key, "pageSize": 200}, timeout=30)
    if r.status_code != 200:
        print(f"✗ List models → HTTP {r.status_code}: {r.json().get('error', {}).get('message', r.text)[:200]}")
        print("  The key itself is invalid, revoked, or the Generative Language API isn't enabled for it.")
        return 1
    available = {m["name"].split("/")[-1] for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])}
    print(f"✓ Key is valid — {len(available)} models available for generateContent")

    # 2. Can it actually generate? One tiny request per model.
    models = sys.argv[1:] or DEFAULT_MODELS
    ok = False
    for m in models:
        if m not in available:
            print(f"  · {m:24} not available to this key")
            continue
        try:
            r = httpx.post(f"{BASE}/models/{m}:generateContent", params={"key": key}, timeout=45,
                           json={"contents": [{"parts": [{"text": "Reply with exactly: ok"}]}]})
        except httpx.TimeoutException:
            print(f"  ✗ {m:24} no answer in 45 s (overloaded or slow right now; FINN falls back to the next model)")
            continue
        if r.status_code == 200:
            text = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"].get("parts", []))
            print(f"  ✓ {m:24} works → {text.strip()!r}")
            ok = True
        elif r.status_code == 429:
            print(f"  ✗ {m:24} 429 — {explain_429(r.json().get('error', {}))}")
        else:
            err = r.json().get("error", {}) if r.headers.get("content-type", "").startswith("application/json") else {}
            print(f"  ✗ {m:24} HTTP {r.status_code}: {err.get('message', r.text)[:200]}")

    print("\nResult:", "the key works ✓" if ok else "the key cannot generate content ✗")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
