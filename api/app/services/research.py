"""Pull: on-demand research grounded ONLY in primary sources (annual reports + concall transcripts).

Pipeline (to build in the Pull phase):
  1. fundamentals.fetch_documents(ticker)   → AR + transcript PDFs from screener.in / IR site
  2. chunk + cache per (ticker, doc)        → never re-parse or re-embed a document
  3. cheap model extracts structured facts  → numbers, guidance statements, with page refs
  4. strong model writes each section       → only from extracted facts; every claim cites a page
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import ResearchReport, ResearchSection
from app.services import companies, graph

SECTIONS: list[tuple[str, str]] = [
    ("narrative_vs_numbers", "Promised vs delivered"),
    ("business", "Business snapshot"),
    ("financials", "Financial snapshot"),
    ("trajectory", "Trajectory"),
    ("balance_sheet", "Balance sheet"),
    ("cash_quality", "Cash quality"),
    ("guidance", "Guidance"),
    ("bull_bear", "Bull vs bear"),
]


def build(ticker: str) -> ResearchReport:
    company = companies.resolve(ticker)
    return ResearchReport(
        company=company,
        sections=[ResearchSection(key=k, title=t, status="pending") for k, t in SECTIONS],  # type: ignore[arg-type]
        network=graph.who_knows_company(company.ticker),
        generated_at=datetime.now(timezone.utc),
    )
