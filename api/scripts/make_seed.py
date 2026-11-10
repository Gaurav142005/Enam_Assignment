"""Build the demo data snapshot bundled into the Docker image (api/seed/finn.db.gz).

Copies the local store and strips anything personal: imported/added connections, the contact log, usage counters
and the Brief's "seen" bookmark. Public data stays: filings, prices, fundamentals, document text, leadership,
research reports and the model cache (so the demo doesn't spend model calls re-reading what's already read).

    uv run python scripts/make_seed.py
"""

from __future__ import annotations

import gzip
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "finn.db"
OUT = ROOT / "seed" / "finn.db.gz"


def main() -> int:
    if not SRC.exists():
        print(f"No local store at {SRC}. Run `make ingest-all` first.")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "finn.db"
        src = sqlite3.connect(SRC)
        out = sqlite3.connect(dst)
        src.backup(out)  # consistent copy even with WAL
        src.close()
        out.executescript("""
            DELETE FROM people;              -- the investor's own connections never ship
            DELETE FROM contact_log;
            DELETE FROM llm_usage;
            DELETE FROM settings WHERE key IN ('brief_seen_at');
            DELETE FROM research_jobs WHERE status != 'done';
            PRAGMA journal_mode=DELETE;
        """)
        out.commit()
        out.execute("VACUUM")
        out.close()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "rb") as f, gzip.open(OUT, "wb", compresslevel=9) as g:
            shutil.copyfileobj(f, g)
        print(f"{OUT.relative_to(ROOT.parent)}: {dst.stat().st_size / 1e6:.1f} MB → {OUT.stat().st_size / 1e6:.1f} MB gzipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
