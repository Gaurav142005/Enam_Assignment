"""Data ingestion: NSE announcements, Yahoo EOD, screener.in fundamentals, primary-source documents.

Run:  uv run python -m app.ingest POLYCAB            # one company, everything
      uv run python -m app.ingest --portfolio --light # whole portfolio, no document downloads
"""
