"""Announcement categories, their base weight, and a cheap rule-based classifier.

Classification strategy (cost-aware, cheapest first):
  1. NSE's own `desc` label → NSE_FIXED (free, covers most filings).
  2. Ambiguous labels ("General Updates", "Outcome of Board Meeting") → text rules on the summary line.
  3. Still unsure → batched cheap-LLM call (ingest/classify.py), else NSE_DEFAULT.
"""

from __future__ import annotations

import re

from app.models import Category

# Base materiality weight. Tuned by judgment; leaves ~20 points of headroom under 100 for
# the investor's own rules + enrichment bonuses (priority.score) so the ranking stays spread out.
BASE_WEIGHT: dict[Category, int] = {
    "results": 80,
    "management_change": 78,
    "M&A": 76,
    "litigation": 74,
    "pledging": 70,
    "fund_raise": 62,
    "capex": 62,
    "credit_rating": 50,
    "insider_trading": 55,
    "press_release": 40,
    "bonus_split": 35,
    "dividend": 30,
    "earnings_call": 20,
    "investor_meetings": 15,
    "agm_egm": 15,
    "postal_ballot": 15,
    "unclassified": 5,
}

LABEL: dict[Category, str] = {
    "results": "Results",
    "management_change": "Management change",
    "M&A": "M&A",
    "litigation": "Litigation",
    "pledging": "Pledging",
    "fund_raise": "Fund raise",
    "capex": "Capex",
    "credit_rating": "Credit rating",
    "insider_trading": "Insider trading",
    "press_release": "Press release",
    "bonus_split": "Bonus / split",
    "dividend": "Dividend",
    "earnings_call": "Earnings call",
    "investor_meetings": "Investor meetings",
    "agm_egm": "AGM / EGM",
    "postal_ballot": "Postal ballot",
    "unclassified": "Routine filings",
}

# ── Classification ────────────────────────────────────────────────────────
# Layer 1: NSE's own `desc` label. Definite labels map straight to a category.
NSE_FIXED: dict[str, Category] = {
    "Financial Result Updates": "results",
    "Integrated Filing- Financial": "results",
    "Change in Management": "management_change",
    "Change in Director(s)": "management_change",
    "Change in Key Managerial Personnel": "management_change",
    "Appointment": "management_change",
    "Resignation": "management_change",
    "Resignation of Director/KMP/SMP": "management_change",
    "Cessation": "management_change",
    "Retirement": "management_change",
    "Demise": "management_change",
    "Acquisition": "M&A",
    "Amalgamation/Merger": "M&A",
    "Scheme of Arrangement": "M&A",
    "Sale or disposal": "M&A",
    "Other Restructuring": "M&A",
    "Joint Venture": "M&A",
    "Qualified Institutional Placement": "fund_raise",
    "Preferential issue": "fund_raise",
    "Issue of Securities": "fund_raise",
    "Buy back": "fund_raise",
    "Rights Issue": "fund_raise",
    "Corporate Insolvency Resolution Process": "litigation",
    "Action(s) taken or orders passed": "litigation",
    "Action(s) initiated or orders passed": "litigation",
    "Litigation": "litigation",
    "Trading Plan under PIT": "insider_trading",
    "Insider Trading": "insider_trading",
    "Credit Rating": "credit_rating",
    "Credit Rating- New": "credit_rating",
    "Credit Rating- Revision": "credit_rating",
    "Credit Rating- Others": "credit_rating",
    "Dividend": "dividend",
    "Bonus": "bonus_split",
    "Split": "bonus_split",
    "Commencement of commercial production/operations": "capex",
    "Capacity addition": "capex",
    "Bagging/Receiving of orders/contracts": "press_release",
    "Product launch": "press_release",
    "News Verification": "press_release",
    "Rumour Verification - Regulation 30(11)": "press_release",
    "Investor Presentation": "earnings_call",
    "ESOP/ESOS/ESPS": "unclassified",
    "Options to purchase securities": "unclassified",
    "Trading Window": "unclassified",
    "Certificate under SEBI (Depositories and Participants) Regulations, 2018": "unclassified",
    "Copy of Newspaper Publication": "unclassified",
    "Change in Auditors": "unclassified",
    "Address Change": "unclassified",
    "Amendment to AOA/MOA": "unclassified",
    "Monitoring Agency Report": "unclassified",
    "Suspension of Trading": "unclassified",
    "Conversion": "unclassified",
    "Giving guarantees/indemnity/ becoming a surety for third party": "unclassified",
}

# Ambiguous labels: try text rules (layer 2) → LLM (layer 3) → this default.
NSE_DEFAULT: dict[str, Category] = {
    "Outcome of Board Meeting": "unclassified",
    "Press Release": "press_release",
    "Shareholders meeting": "agm_egm",
    "Analysts/Institutional Investor Meet/Con. Call Updates": "investor_meetings",
    "Record Date": "dividend",
    "Allotment of Securities": "fund_raise",
    "Disclosure under SEBI Takeover Regulations": "insider_trading",
    "Agreements": "press_release",
    "Memorandum of Understanding/Agreements": "press_release",
}

# Layer 2: text rules on the filing's summary line. Ordered; first match wins.
_RULES: list[tuple[Category, str]] = [
    ("earnings_call", r"transcript|audio recording|recording of|link of recording|earnings call|conference call|con\. ?call|concall"),
    ("results", r"financial results|quarterly results|results for the (quarter|period|year)|performance of the company for the quarter|(business|financial) performance .*quarter|update for q[1-4] ?fy"),
    ("unclassified", r"newspaper|statutory auditor|secretarial auditor|regulation 31\(4\)|loss of share certificate|duplicate share|\b(esop|esps|esos)\b|sebi/ho/ddhs"),
    ("management_change", r"appoint|resign|cessation|retire|demise|chief financial|chief executive|managing director|\b(ceo|cfo|kmp)\b"),
    ("M&A", r"acqui|amalgamation|merger|demerger|joint venture|scheme of arrangement|stake sale|divest|initial public offer|red herring|\bipo\b"),
    ("litigation", r"litigation|show cause|penalty|\border\b.*(passed|received)|insolvency|nclt|nclat|tribunal|search and seizure|tax demand"),
    ("pledging", r"pledge|encumbrance|regulation 31\([12]\)"),
    ("insider_trading", r"regulation 29|regulation 7\(2\)|insider trading|\bpit\b"),
    ("fund_raise", r"\bqip\b|qualified institutional|rights issue|preferential|buy-?back|commercial paper|non[- ]convertible|debenture|bonds?\b"),
    ("credit_rating", r"credit rating|\brating\b"),
    ("bonus_split", r"bonus|sub-division|split"),
    ("dividend", r"dividend"),
    ("capex", r"capacity expansion|capex|new plant|greenfield|brownfield|commercial production|commissioning"),
    ("postal_ballot", r"postal ballot"),
    ("agm_egm", r"annual general meeting|\bagm\b|\begm\b|extra-?ordinary general|voting results|scrutini[sz]er"),
    ("investor_meetings", r"analyst|investor(s)? meet|institutional investor|roadshow|investor conference|schedule of meet|conference with investors|participating in the conference"),
    ("press_release", r"media (statement|release)|press release|price increase|order win|bagged"),
]

# Filings in a material category that are business-as-usual (e.g. an NBFC's weekly NCD allotment).
_ROUTINE_WITHIN: list[tuple[Category, str]] = [
    ("results", r"is scheduled|will be held|to consider and approve|intimation of board meeting"),
    ("fund_raise", r"non[- ]convertible|debenture|commercial paper|\bncd"),
    ("management_change", r"senior management personnel|\bsmp\b|company secretary|compliance officer"),
]


def text_rules(text: str) -> Category | None:
    s = text.lower()
    for category, pattern in _RULES:
        if re.search(pattern, s):
            return category
    return None


def is_routine(category: Category, text: str) -> bool:
    s = text.lower()
    return any(c == category and re.search(p, s) for c, p in _ROUTINE_WITHIN)


def classify(subject: str, nse_desc: str | None = None) -> Category | None:
    """Layers 1–2 (free). Returns None when unsure; the caller may escalate to an LLM, then fall back."""
    if nse_desc in NSE_FIXED:
        return NSE_FIXED[nse_desc]
    return text_rules(subject)


def default_for(nse_desc: str | None) -> Category:
    return NSE_DEFAULT.get(nse_desc or "", "unclassified")
