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

| Source | Fetch | Refresh | Store | Links to |
|---|---|---|---|---|
| EOD price/volume | yfinance `TICKER.NS` | Daily after 16:00 IST | SQLite `eod(ticker, date, close, volume)` | ticker |
| Announcements | NSE corporate-announcements JSON | Every 15 min in market hours | `filings(id, ticker, subject, category, url, filed_at)` | ticker; person names → `graph` |
| Fundamentals | screener.in documents + IR sites | On demand, then cached | PDF text by URL hash, page-indexed | ticker |
| Profiles | Synthetic JSON (demo) | Manual | `people.json` → in-memory graph | employer ticker, school |

**Entity resolution** (a name in a filing → a person): exact normalised name + employer match first. Fuzzy name + employer + tenure window second. Below a confidence threshold, show the bio as "possible match" rather than asserting it.

## Security & privacy (to be written up)
- The network is per investor and never shared across tenants. Profile data is minimal: role, employer, tenure, school, expertise tags.
- Retention, consent, access control and an audit log: TBD in the writeup.

## LLMs & agents (to be written up)
- `services/llm.py` is the single routing point. A **cheap** model handles bulk extraction and classification fallback. A **strong** model handles promised-vs-delivered, bull/bear and network explanations.
- Results are cached by (model, prompt, input hash), so each document is processed only once.

## Cloud (to be written up)
- web → Vercel. api → Render / Fly (Python). SQLite → Postgres when it outgrows a single file. Scheduled fetches → cron on the API host.
