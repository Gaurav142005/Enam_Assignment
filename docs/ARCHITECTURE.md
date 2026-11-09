# FINN: architecture

Working notes. These become the architecture section of the covering writeup. The brief asks for four topics: **data pipelines**, **security & privacy**, **LLMs & agents** and **cloud**.

```
                ┌──────────────────────── web/ (Next.js, mobile-first) ────────────────────────┐
                │  Brief (Push)        Ask (Pull)             Network            Settings      │
                └───────────────────────────────┬──────────────────────────────────────────────┘
                                                │ JSON (contract: api/app/models.py ⇄ web/src/lib/types.ts)
                ┌───────────────────────────────▼──────────── api/ (FastAPI) ───────────────────┐
                │ routers/push      routers/pull           routers/network                      │
                │   digest.py         research.py             graph.py  ◀── woven into push+pull │
                │   priority.py       fundamentals.py                                            │
                │   taxonomy.py       llm.py (cheap ⇄ strong routing, cached)                    │
                │   filings.py                                                                   │
                │   prices.py                                                                    │
                └──────┬───────────────┬──────────────────┬───────────────────┬─────────────────┘
                       │               │                  │                   │
                  NSE / BSE       Yahoo Finance       screener.in        profiles (synthetic
                announcements    (yfinance, .NS)    ARs + transcripts     in demo; consented
                                                                           import in real life)
```

## Data pipelines

`uv run python -m app.ingest TICKER` (or `--portfolio --light`). Each source is its own step: if one fails, the others still run. Everything is upserted, so re-runs are idempotent, and documents are fetched and parsed only once (cached by URL, stored by content hash).

| Source | Fetch | Store | Notes |
|---|---|---|---|
| Fundamentals | screener.in company page (consolidated, else standalone) | `companies`, `financials` (long format: statement × line × period), `documents` (links) | 13 quarters + 10 years P&L / BS / CF / ratios / shareholding |
| EOD | yfinance `TICKER.NS`, 1y | `eod` | Today's bar is dropped until 15:45 IST (still forming) |
| Announcements | `nseindia.com/api/corporate-announcements` | `announcements` | Attachment read only when needed (see below) |
| Attachments | `nsearchives.nseindia.com` PDF or zip (PDF + SEBI XBRL) | `documents` + `doc_pages` (+ `xbrl`) | First 6 pages |
| Transcripts / ARs | BSE-hosted PDFs linked from screener | `doc_pages` (page-indexed, for citations) | Default: last 4 transcripts + latest AR |

**Classification: cheapest layer first.** Measured on 1,352 real announcements across the 18-company portfolio:
1. NSE's own label (`desc`), via `NSE_FIXED`. Free.
2. Text rules on the one-line summary (and on the PDF's first pages for vague labels). Free. Together, layers 1–2 leave about 15% unresolved.
3. The cheap LLM, batched 25 per call and cached, for the leftovers only. It also writes a one-line summary.
4. A per-label default.

A `routine` flag demotes business-as-usual items inside material categories (an NBFC's weekly NCD allotment, a results-date intimation).

**Enrichment**
- *Results* → Revenue / EBITDA (operating profit) / PBT / PAT for the quarter named in the filing, with QoQ and YoY, from screener's quarterly table (itself compiled from exchange filings). Lenders get no EBITDA row.
- *Management change* → people, best source first: **SEBI XBRL** (exact name, designation, change type, date, reason) → **LLM** over the PDF (which by SEBI rule carries the appointee's brief profile) → regex fallback.
- *Entity resolution* (filing person ↔ network): employer and school names are normalised (`Havells India Ltd.` = `Havells`), then matched on overlapping tenure or study years.

## Security & privacy (to be written up)
- The network is per investor and never shared across tenants. Profile data is minimal: role, employer, tenure, school, expertise tags.
- Retention, consent, access control and an audit log: TBD in the writeup.

## LLMs & agents (to be written up)
- `app/llm.py` is the single routing point. A **cheap** model handles bulk extraction and classification fallback. A **strong** model handles promised-vs-delivered, bull/bear and network explanations.
- Results are cached by (model, prompt, input hash), so each document is processed only once.

## Cloud (to be written up)
- web → Vercel. api → Render / Fly (Python). SQLite → Postgres when it outgrows a single file. Scheduled fetches → cron on the API host.
