"""SQLite store: one file, no server. Raw documents live on disk, keyed by content hash.

Everything is upserted, so re-running ingestion is idempotent and cheap.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
  ticker TEXT PRIMARY KEY, name TEXT, isin TEXT, about TEXT,
  ratios TEXT,              -- JSON {name: value} from screener top ratios
  screener_view TEXT,       -- 'consolidated' | 'standalone'
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS eod (
  ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER,
  PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS announcements (
  id TEXT PRIMARY KEY,      -- NSE seq_id
  ticker TEXT, filed_at TEXT, nse_desc TEXT, text TEXT, attachment_url TEXT,
  category TEXT, category_source TEXT,   -- 'nse' | 'rules' | 'llm' | 'default'
  summary TEXT,
  extra TEXT                -- JSON: {"results": ResultsCut, ...}
);
CREATE INDEX IF NOT EXISTS ix_ann_ticker_time ON announcements (ticker, filed_at);
CREATE TABLE IF NOT EXISTS financials (
  ticker TEXT, statement TEXT, line TEXT, period TEXT, value REAL, seq INTEGER,
  PRIMARY KEY (ticker, statement, line, period)
);
CREATE TABLE IF NOT EXISTS documents (
  url TEXT PRIMARY KEY, ticker TEXT,
  kind TEXT,                -- 'annual_report' | 'transcript' | 'presentation' | 'filing'
  period TEXT, title TEXT,
  sha TEXT, pages INTEGER, fetched_at TEXT,
  xbrl TEXT                 -- structured SEBI XBRL shipped alongside some filings (zip attachments)
);
CREATE TABLE IF NOT EXISTS doc_pages (
  url TEXT, page INTEGER, text TEXT, PRIMARY KEY (url, page)
);
CREATE TABLE IF NOT EXISTS people_mentions (
  announcement_id TEXT, ticker TEXT, name TEXT, role TEXT, change TEXT,
  effective_date TEXT, background TEXT, source TEXT,
  PRIMARY KEY (announcement_id, name)
);
CREATE TABLE IF NOT EXISTS llm_cache (
  key TEXT PRIMARY KEY, model TEXT, response TEXT, created_at TEXT
);
"""


_MIGRATIONS = ["ALTER TABLE documents ADD COLUMN xbrl TEXT"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    for ddl in _MIGRATIONS:
        try:
            con.execute(ddl)
        except sqlite3.OperationalError:
            pass  # already applied
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert(con: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    cols = list(rows[0])
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
    con.executemany(sql, [tuple(json.dumps(r[c]) if isinstance(r[c], (dict, list)) else r[c] for c in cols) for r in rows])
    return len(rows)


def has_data() -> bool:
    if not config.DB_PATH.exists():
        return False
    with connect() as con:
        return con.execute("SELECT 1 FROM announcements LIMIT 1").fetchone() is not None
