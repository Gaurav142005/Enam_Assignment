"""Corporate announcements from NSE (and BSE as a fallback).

To build in the Push phase:
  - fetch_announcements(tickers, since) → NSE corporate-announcements JSON (needs a session cookie
    from the NSE homepage first); normalise to {ticker, subject, attachment_url, filed_at}
  - classify with taxonomy.classify(); escalate unknowns to llm.cheap()
  - results PDFs → llm.cheap() extraction of Revenue / EBITDA / PBT / PAT for QoQ / YoY
  - management-change PDFs → extract the person's name → entity-resolve against graph
"""
