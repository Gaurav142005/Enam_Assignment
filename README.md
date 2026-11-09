# FINN: Financial Investment Agent

A mobile-first investing companion built for the ENAM Holdings Founding AI Engineer build challenge.

- **Push:** what changed across my portfolio, ranked, with routine filings collapsed.
- **Pull:** on-demand research on any NSE company, grounded only in its own filings.
- **Network:** who in my network can help me understand it, woven into both of the above.

Product decisions: [docs/PRODUCT.md](docs/PRODUCT.md) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Brief: [docs/brief/](docs/brief/)

## Run it

Needs Node 20+, pnpm and [uv](https://docs.astral.sh/uv/).

```bash
make setup   # install web + api deps
make api     # FastAPI on :8000   (terminal 1)
make web     # Next.js on :3000   (terminal 2)
make test    # API tests
```

Open http://localhost:3000. Use your browser's device toolbar (phone width), or open it from a phone on the same Wi-Fi at `http://<your-lan-ip>:3000`.

## Layout

```
api/                        FastAPI backend (Python, uv)
  app/models.py             API contract (mirrored in web/src/lib/types.ts)
  app/routers/              push · pull · network · portfolio
  app/services/
    digest.py               Push: rank → enrich → weave network → collapse routine
    priority.py taxonomy.py Scoring + announcement categories (from the ENAM glossary)
    graph.py                Network: inferred edges, who-knows-company, second-degree reach, themes, reconnect
    research.py             Pull: section pipeline (primary sources only)
    filings.py prices.py fundamentals.py llm.py   Data sources + model routing (stubs → next phases)
  app/data/                 portfolio.json, network/people.json, fixtures/ (synthetic)
  tests/
web/                        Next.js 15 App Router, Tailwind, mobile-first
  src/app/                  /  (Brief)  /ask  /company/[ticker]  /network  /people/[id]  /settings
  src/components/           PushCard, ResultsTable, PersonBrief, NetworkLine, …
  src/lib/                  api client, types, formatters
docs/                       brief PDFs, product + architecture notes
```

## Data status

| Layer | Now | Next |
|---|---|---|
| Announcements | Synthetic fixtures | NSE live feed |
| EOD prices | Synthetic fixtures | yfinance |
| Fundamentals | — | screener.in ARs + transcripts |
| Network | Synthetic profiles (no real people) | — (stays synthetic for the demo) |
