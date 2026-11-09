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

# LLM — any free tier works. Gemini by default; any OpenAI-compatible endpoint (Groq, OpenRouter, Ollama) also works.
LLM_PROVIDER = os.getenv("FINN_LLM_PROVIDER", "gemini")  # "gemini" | "openai"
LLM_API_KEY = os.getenv("FINN_LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
LLM_BASE_URL = os.getenv("FINN_LLM_BASE_URL", "")  # only for provider=openai, e.g. https://api.groq.com/openai/v1
CHEAP_MODEL = os.getenv("FINN_CHEAP_MODEL", "gemini-3.5-flash-lite")
STRONG_MODEL = os.getenv("FINN_STRONG_MODEL", "gemini-3.8-flash")


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
