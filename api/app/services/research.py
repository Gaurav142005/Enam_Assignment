"""Pull: on-demand research on any NSE ticker, grounded in primary sources.

  Deterministic (now):  business, financial snapshot, trajectory, balance sheet, cash quality, shareholding
                        → services/fundamentals.py, arithmetic over standardised filings data
  LLM (next):           promised vs delivered, guidance, bull vs bear
                        → read from concall transcripts + annual reports (ingest/documents.py), page-cited
"""

from __future__ import annotations

from datetime import datetime, timezone

from app import llm
from app.models import Citation, ResearchReport, ResearchSection
from app.services import companies, fundamentals, graph, market

DETERMINISTIC = [
    ("business", "Business"),
    ("financials", "Financial snapshot"),
    ("trajectory", "Trajectory"),
    ("balance_sheet", "Balance sheet"),
    ("cash_quality", "Cash quality"),
    ("shareholding", "Shareholding"),
]
NEEDS_LLM = [
    ("narrative_vs_numbers", "Promised vs delivered", "Last four quarters of management guidance from concall transcripts, checked against reported numbers."),
    ("guidance", "Guidance", "What management has explicitly guided on growth, margins and capex, quoted with page references."),
    ("bull_bear", "Bull vs bear", "A tight case each way, built only from the filings and transcripts above."),
]


def build(ticker: str) -> ResearchReport:
    company = companies.resolve(ticker)
    f = fundamentals.build(company.ticker)
    if f and company.name == company.ticker:
        company = company.model_copy(update={"name": f.name})
    cite = [Citation(doc=f"screener.in {f.view} financials (compiled from annual reports & exchange filings)", url=f.source_url)] if f else []

    sections: list[ResearchSection] = []
    for key, title in DETERMINISTIC:
        if not f:
            sections.append(ResearchSection(key=key, title=title, status="pending"))  # type: ignore[arg-type]
            continue
        if key == "business":
            body = f.about
        elif key == "cash_quality" and f.is_lender:
            body = "Not meaningful for lenders: operating cash flow mostly reflects loan-book movements."
        else:
            body = None  # the UI renders the structured fundamentals + signals for these
        has = key in {"business", "financials"} or any(s.section == key for s in f.signals) or body
        sections.append(ResearchSection(key=key, title=title, status="ready" if has else "pending", body=body, citations=cite))  # type: ignore[arg-type]
    suffix = "" if llm.available() else " Needs a working LLM key (check with scripts/test_gemini.py)."
    sections += [ResearchSection(key=k, title=t, status="pending", body=what + suffix) for k, t, what in NEEDS_LLM]  # type: ignore[arg-type]

    return ResearchReport(
        company=company,
        fundamentals=f,
        position=market.position(company.ticker),
        sections=sections,
        network=graph.who_knows_company(company.ticker),
        generated_at=datetime.now(timezone.utc),
    )
