# FINN: product decisions

Source brief: [brief/01-challenge-brief.pdf](brief/01-challenge-brief.pdf) · glossary: [brief/02-reference-glossary.pdf](brief/02-reference-glossary.pdf)
Deadline: **15 Nov 2026**.

## Point of view

**FINN is a briefing, not a dashboard.** An investor opens it a few times a day and should get the answer to *"what changed, does it matter, and who can tell me more?"* in under a minute. Three rules follow from that:

1. **Rank and bury.** Every item has a score. Material items get a card. Routine items are counted and collapsed, never deleted.
2. **Enrich, don't link.** A card shows the substance (the QoQ/YoY table, the incoming CFO's career) so the investor doesn't have to open the PDF.
3. **The network rides along.** The "Ask *X*" line sits on the card where the question comes up. It isn't hidden away in a separate contacts app.

## Navigation (mobile, one thumb)

| Tab | Layer | Job |
|---|---|---|
| **Brief** `/` | Push | Time-windowed digest (4h/24h/3d/7d) → *Needs your attention* · *Unusual moves* · *Routine* (collapsed). Thresholds via ⚙ → `/settings`. |
| **Ask** `/ask` → `/company/[ticker]` | Pull | Search any NSE ticker → research view. *Promised vs delivered* leads; *Who can help* sits on top. |
| **Network** `/network` → `/people/[id]` | Network | Reconnect nudges · expertise map · people. A person page shows their career and, for outsiders (e.g. a new CFO), who you know who knows them. |

## Core features (scope for the prototype)

### Portfolio
- [x] Holdings with quantity + average cost (`api/app/data/portfolio.json`): value, weight, unrealised and period P&L
- [x] Value-weighted period returns vs Nifty 50; leaders and laggards
- [x] Daily candle / line charts with volume for any NSE ticker
- [x] Company news (Google News RSS), shown as secondary context, never a research input

### Push
- [x] Windowed digest with priority ranking (`api/app/services/priority.py`)
- [x] Configurable EOD triggers: price ±X%, volume N× its N-day average
- [x] Announcement-type preferences feed into the ranking
- [x] **Management change** → incoming person's bio + who in my network overlaps with them
- [x] **Results** → Revenue / EBITDA / PBT / PAT, QoQ + YoY
- [x] **Material event** (M&A / capex / litigation) → best person to call, and why
- [x] Live NSE announcements feed
- [x] Live yfinance EOD
- [x] Results headline numbers (from standardised quarterly statements)
- [ ] One-line summaries for mid-priority filings

### Pull
- [x] Works for **any** NSE ticker (no hard-wiring to the demo set)
- [x] Section scaffold, with "Who can help" woven in
- [ ] **Promised vs delivered** across the last 4 quarters (the headline feature)
- [x] Business, financial snapshot, trajectory, balance sheet, cash quality, shareholding: deterministic, from statements
- [ ] Guidance, bull vs bear (LLM over transcripts)
- [ ] Every claim cites a primary-source page (AR / concall transcript only)

### Network
- [x] Edges are inferred from profiles (overlapping tenure at the same employer, overlapping years at the same school)
- [x] Who should I call (by company) · second-degree reach (by person) · expertise map · reconnect nudges
- [ ] Ask the network in natural language ("who knows rural lending in the South?")
- [ ] Supplier / customer / competitor reach (beyond "worked at the same company")
- [ ] Link strength explained (tenure overlap length, recency, relationship strength)

## Demo set

- **Portfolio (18):** RELIANCE, HDFCBANK, INFY, BAJFINANCE, CHOLAFIN, ASIANPAINT, TITAN, TRENT, SUNPHARMA, LT, HAL, MARUTI, KPITTECH, DIXON, POLYCAB, DEEPAKNTR, PIIND, ETERNAL
- **Research list (4, outside the portfolio):** CGPOWER (semis), AARTIIND (specialty chem), CREDITACC (rural lending), PERSISTENT (IT)
- **Network:** 8 synthetic people + 1 synthetic "filing person" (the incoming Polycab CFO). Their employers deliberately overlap the portfolio and the brief's example themes (specialty chemicals, rural lending, semiconductors).

Edit these in `api/app/data/`.

## Build order

1. ~~Skeleton~~ (this commit)
2. **Push:** live NSE feed + yfinance, classifier, results extraction
3. **Pull:** document fetch + cache, extraction, *promised vs delivered*
4. **Network:** richer graph, natural-language queries, link-strength explanations
5. Deploy (Vercel + Render/Fly), writeup, build-history export
