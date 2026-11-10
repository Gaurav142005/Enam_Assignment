"""SQLite store: one file, no server. Raw documents live on disk, keyed by content hash.

Everything is upserted, so re-running ingestion is idempotent and cheap.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

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
CREATE TABLE IF NOT EXISTS eod_meta (
  ticker TEXT PRIMARY KEY, fetched_at TEXT, period TEXT
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
CREATE TABLE IF NOT EXISTS news (
  id TEXT PRIMARY KEY,      -- hash of normalised title (same story syndicated twice = one row)
  ticker TEXT, title TEXT, source TEXT, url TEXT, published_at TEXT, fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_news_ticker ON news (ticker, published_at);
CREATE TABLE IF NOT EXISTS people (           -- the investor's own connections (imported or added by hand)
  id TEXT PRIMARY KEY, name TEXT, headline TEXT,
  positions TEXT, education TEXT, expertise TEXT, relationship TEXT,   -- JSON
  source TEXT,              -- 'linkedin' | 'manual'
  linkedin_url TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS company_people (   -- management + board of listed companies (public sources)
  id TEXT PRIMARY KEY, ticker TEXT, name TEXT, name_key TEXT, role TEXT,
  kind TEXT,                -- 'executive' | 'director' | 'independent'
  status TEXT,              -- 'current' | 'former'
  since TEXT, year_born INTEGER, sources TEXT, as_of TEXT, updated_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_cp_ticker ON company_people (ticker);
CREATE TABLE IF NOT EXISTS research_jobs (
  id TEXT PRIMARY KEY, ticker TEXT, status TEXT, steps TEXT, result TEXT, error TEXT, started_at TEXT, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_rj_ticker ON research_jobs (ticker, finished_at);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS contact_log (     -- when the investor last spoke to someone (any source of person)
  person_id TEXT PRIMARY KEY, last_contact TEXT, note TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS llm_usage (       -- per day, per model: what FINN actually spent
  day TEXT, model TEXT, calls INTEGER, tokens_in INTEGER, tokens_out INTEGER, PRIMARY KEY (day, model)
);
CREATE TABLE IF NOT EXISTS holdings (          -- the investor's portfolio (seeded from data/portfolio.json on first use)
  ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, qty INTEGER, avg_cost REAL, bought TEXT, added_at TEXT
);
CREATE TABLE IF NOT EXISTS events (            -- upcoming: results dates, earnings calls, record dates, meetings
  id TEXT PRIMARY KEY, ticker TEXT, date TEXT, end_date TEXT, time TEXT, kind TEXT, title TEXT, detail TEXT,
  source TEXT, url TEXT, updated_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_date ON events (date);
CREATE TABLE IF NOT EXISTS theses (            -- why the investor owns it, in their words
  ticker TEXT PRIMARY KEY, text TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS thesis_checks (     -- each material filing judged against a thesis version
  announcement_id TEXT, ticker TEXT, thesis_hash TEXT, stance TEXT, why TEXT, created_at TEXT,
  PRIMARY KEY (announcement_id, thesis_hash)
);
CREATE TABLE IF NOT EXISTS push_subscriptions (  -- devices that asked for notifications (Web Push)
  endpoint TEXT PRIMARY KEY, subscription TEXT, user_agent TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS push_sent (            -- items already notified, so each is sent once
  item_id TEXT PRIMARY KEY, sent_at TEXT
);
CREATE TABLE IF NOT EXISTS llm_cache (
  key TEXT PRIMARY KEY, model TEXT, response TEXT, created_at TEXT
);
"""


_MIGRATIONS = ["ALTER TABLE documents ADD COLUMN xbrl TEXT"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_ready: set[str] = set()  # DB paths whose schema is already in place (per process)
_ready_lock = threading.Lock()


def _ensure_schema(con: sqlite3.Connection, path: str) -> None:
    """Create tables once per process, not on every connection: DDL takes a write lock, and with a background
    research job saving progress while the page polls, per-connection DDL serialised everything."""
    with _ready_lock:
        if path in _ready:
            return
        con.execute("PRAGMA journal_mode=WAL")  # readers never block the writer (and vice versa)
        con.executescript(SCHEMA)
        for ddl in _MIGRATIONS:
            try:
                con.execute(ddl)
            except sqlite3.OperationalError:
                pass  # already applied
        con.commit()
        _ready.add(path)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    path = str(config.DB_PATH)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    _ensure_schema(con, path)
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
