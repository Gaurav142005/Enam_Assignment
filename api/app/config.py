"""Runtime settings, from env (see repo-root .env.example). Loaded once."""

from __future__ import annotations

import os
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.getenv("FINN_CACHE_DIR", API_ROOT / "cache"))
DB_PATH = Path(os.getenv("FINN_DB", CACHE_DIR / "finn.db"))
FILES_DIR = CACHE_DIR / "files"

# Demo network (synthetic people in data/network/people.json). Set FINN_DEMO_NETWORK=0 once real connections are imported.
DEMO_NETWORK = os.getenv("FINN_DEMO_NETWORK", "1") != "0"
AUTO_REFRESH_MIN = float(os.getenv("FINN_AUTO_REFRESH_MIN", "15"))
# Public demo: visitors can't upload their own LinkedIn export (everyone would see it); a sample import is offered instead.
PUBLIC_DEMO = os.getenv("FINN_PUBLIC_DEMO", "0") == "1"
# Web Push. Keys are generated and stored on first use if not provided; the subject is a contact the push services can reach.
VAPID_PUBLIC = os.getenv("FINN_VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE = os.getenv("FINN_VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.getenv("FINN_VAPID_SUBJECT", "mailto:finn@example.com")
# Tried in order when a model times out or is overloaded (Gemini returns 503 under load).
CHEAP_FALLBACKS = [m for m in os.getenv("FINN_CHEAP_FALLBACKS", "gemini-3.1-flash-lite").split(",") if m]
STRONG_FALLBACKS = [m for m in os.getenv("FINN_STRONG_FALLBACKS", "gemini-3.6-flash,gemini-3-flash-preview,gemini-3.5-flash-lite").split(",") if m]
# Per-model budget. A model that hasn't answered by then is overloaded; the next one in the chain gets the job.
CHEAP_TIMEOUT = float(os.getenv("FINN_CHEAP_TIMEOUT", "30"))
STRONG_TIMEOUT = float(os.getenv("FINN_STRONG_TIMEOUT", "40"))
# Deep research: wall-clock budget for the whole extraction stage (stragglers are skipped and noted).
EXTRACT_BUDGET = float(os.getenv("FINN_EXTRACT_BUDGET", "45"))

# LLM — any free tier works. Gemini by default; any OpenAI-compatible endpoint (Groq, OpenRouter, Ollama) also works.
LLM_PROVIDER = os.getenv("FINN_LLM_PROVIDER", "gemini")  # "gemini" | "openai"
LLM_API_KEY = os.getenv("FINN_LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
LLM_BASE_URL = os.getenv("FINN_LLM_BASE_URL", "")  # only for provider=openai, e.g. https://api.groq.com/openai/v1
CHEAP_MODEL = os.getenv("FINN_CHEAP_MODEL", "gemini-3.5-flash-lite")
STRONG_MODEL = os.getenv("FINN_STRONG_MODEL", "gemini-3.5-flash")


def _load_dotenv() -> None:
    """Tiny .env reader (repo root or api/), so `uv run` picks up keys without extra deps."""
    for p in (API_ROOT / ".env", API_ROOT.parent / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
# re-read after .env
LLM_PROVIDER = os.getenv("FINN_LLM_PROVIDER", LLM_PROVIDER)
LLM_API_KEY = os.getenv("FINN_LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or LLM_API_KEY
LLM_BASE_URL = os.getenv("FINN_LLM_BASE_URL", LLM_BASE_URL)
CHEAP_MODEL = os.getenv("FINN_CHEAP_MODEL", CHEAP_MODEL)
STRONG_MODEL = os.getenv("FINN_STRONG_MODEL", STRONG_MODEL)
DEMO_NETWORK = os.getenv("FINN_DEMO_NETWORK", "1") != "0"
