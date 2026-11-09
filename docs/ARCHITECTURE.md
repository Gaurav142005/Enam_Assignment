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
- **Sources of people data, all permissible:** (1) the investor's own LinkedIn data export, uploaded by them; email addresses are dropped on read, and a whole import can be removed in one tap; (2) connections they add by hand; (3) company leadership from public records (Yahoo Finance officers, NSE corporate-governance XBRL, exchange filings). FINN never logs into or scrapes LinkedIn (its terms forbid automated access).
- Connection data never goes to an LLM. Re-uploading an export is a full sync, so people the investor removes from LinkedIn disappear from FINN too.
- Retention, consent, access control and an audit log: TBD in the writeup.

## LLMs & agents

**Deep research** (`services/deep_research.py`, Pull → "Run deep research") is the one agentic workflow: it plans a fixed
read of a company's primary sources, calls tools (exchange APIs, PDF readers, the model), and assembles a cited report.

| Stage | What | Model calls | Typical time |
|---|---|---|---|
| collect | 12 months of filings, prices, fundamentals, leadership | 0 | 5–10 s |
| documents | last 4 transcripts, 2 decks, latest annual report (only the ~30 most relevant AR pages are kept) | 0 | 1–10 s |
| movements | financial inflections, events + next-session market reaction, people, ownership, unexplained moves | 0 | <1 s |
| extract | one cheap call per document + one for filings, page-cited JSON | ~8 (Flash-Lite) | 10–45 s (budgeted) |
| synthesize | promised vs delivered, guidance, themes, risks, bull/bear, questions → routed to people in the network | 1 (Flash, falls back) | 5–40 s |

Measured: ~90k input / ~8k output tokens for a first run (≈ $0.01–0.02 at paid Flash-Lite/Flash prices; ~9 requests against
free-tier daily quotas of hundreds to ~1,000). Every call is cached by input hash, so a re-run with no new documents makes
0 calls and a new quarter re-reads only the new transcript plus one synthesis call. Overloaded models (503 / timeouts) are
skipped for 10 minutes and the next model in the chain answers; each stage has a wall-clock budget, so a slow provider
degrades the report (noted at the bottom) instead of blocking it.
- `app/llm.py` is the single routing point. A **cheap** model handles bulk extraction and classification fallback. A **strong** model handles promised-vs-delivered, bull/bear and network explanations.
- Results are cached by (model, prompt, input hash), so each document is processed only once.

## Cloud (to be written up)
- web → Vercel. api → Render / Fly (Python). SQLite → Postgres when it outgrows a single file. Scheduled fetches → cron on the API host.
