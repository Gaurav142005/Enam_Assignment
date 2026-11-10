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
| **Brief** `/` | Push | Dated lede naming what matters → *Needs your attention* as a swipeable card deck (each card: title, one key line, best person to ask; details fold away) · *Unusual moves* tiles · *Routine* collapsed by type. Thresholds via ⚙ → `/settings`. |
| **Portfolio** `/portfolio` | — | Value, P&L, value-weighted returns vs Nifty 50, leaders/laggards with sparklines. |
| **Ask** `/ask` → `/company/[ticker]` | Pull | Search any of ~2,600 NSE companies → company page: position, price chart, who can help, leadership, then collapsible research sections that show their lead finding when closed. |
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
- [x] One-line summaries where the exchange's own line says nothing ("Updates" → what happened), from the filing PDF
- [x] New since you last looked; "checked Xm ago"; refresh on demand and every 15 minutes
- [x] Unusual moves carry the likely reason (same-session filing or headline) and who to ask
- [x] Alert rules persist

### Pull
- [x] Works for **any** NSE ticker (no hard-wiring to the demo set)
- [x] Section scaffold, with "Who can help" woven in
- [x] **Ask a company anything**: answered from its transcripts, decks and annual report with page cites; says so when the documents don't answer
- [x] **Deep research** (30–60 s job): 12-month movement timeline with market reactions, promised vs delivered, guidance, themes, risks, bull/bear, questions routed to your network; every claim page-cited
- [x] **Promised vs delivered** across the last 4 quarters (the headline feature)
- [x] Business, financial snapshot, trajectory, balance sheet, cash quality, shareholding: deterministic, from statements
- [x] Guidance, bull vs bear (LLM over transcripts)
- [x] Every claim cites a primary-source page (AR / concall transcript only)

### Network
- [x] Edges are inferred from profiles (overlapping tenure at the same employer, overlapping years at the same school)
- [x] Who should I call (by company) · second-degree reach (by person) · expertise map · reconnect nudges
- [x] Import the investor's own LinkedIn export (CSV or zip); re-upload syncs; employers resolved to NSE tickers
- [x] Add / remove connections by hand (career + education feed overlap detection)
- [x] Leadership of every portfolio company (management + board), marked where the investor already knows them
- [x] Ask the network directly ("who knows rural lending?", "finance people at Polycab", a school, a name)
- [x] Who to call widens from insiders to competitors to sector experts, labelled
- [x] Second-degree reach into leadership via connections who worked there in the same function
- [x] Diligence page per person: how to reach them, what filings say, what to ask
- [x] Log a conversation in one tap (drives the reconnect nudges); nudges say what happened
- [ ] Supplier / customer reach (needs relationship data beyond filings)

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
