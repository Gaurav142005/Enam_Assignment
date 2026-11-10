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

## Security & privacy

- **What is stored about people:** name, role, employer, tenure, school, expertise tags, how the investor knows them, and when they last spoke. No emails, phone numbers or message content. Email addresses in a LinkedIn export are dropped on read.
- **Where it comes from, all permissible:** (1) the investor's own LinkedIn data export, uploaded by them; (2) connections they add by hand; (3) company leadership from public records (Yahoo Finance officers, NSE corporate-governance XBRL, exchange filings). FINN never logs into or scrapes LinkedIn; its terms forbid automated access. The demo network is synthetic.
- **Where it goes:** one SQLite file in this deployment. Connection data is never sent to a model: network questions, who-to-call and second-degree paths are computed deterministically. The only personal text a model sees is the public filing that announces an appointment.
- **Retention and control:** re-uploading an export is a full sync (people removed on LinkedIn disappear here); an import can be removed in one tap; any connection can be deleted from its page. Company-leadership records refresh weekly and carry their sources.
- **In a real deployment:** per-investor tenancy (row-level `owner_id`, never shared across users, including within a firm unless explicitly shared), SSO, encryption at rest, an audit log of who viewed which profile, a consent note on import, and a retention window for people the investor no longer lists.

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

## Cloud

| Piece | Where | Why |
|---|---|---|
| Web (Next.js) + API (FastAPI) | One container (Railway) with a persistent disk | SQLite and the PDF cache need a disk; background jobs (deep research, auto-refresh) need a long-lived process, which serverless functions don't give |
| Store | SQLite (WAL) → Postgres when multi-user | One investor, ~12 MB; zero ops |
| Scheduled work | In-process timer (`services/watch.py`, 15 min) | Re-pulls filings + prices for the portfolio; "Checked 4m ago" on the Brief |
| Models | Gemini free tier via one routing module | Flash-Lite for bulk, Flash for synthesis; fallback chain + cooldown when a model is overloaded |
