"""Announcement categories, their base weight, and a cheap rule-based classifier.

Classification strategy (cost-aware):
  1. NSE's own subject/category string → keyword rules below (free, catches most filings).
  2. Only filings the rules can't place go to a small LLM (see services/llm.py).
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

# Ordered: first match wins. Patterns run against the lower-cased subject line.
_RULES: list[tuple[Category, str]] = [
    ("results", r"financial results|quarterly results|outcome of board meeting.*results"),
    ("earnings_call", r"earnings call|conference call|concall|transcript"),
    ("management_change", r"appointment|resignation|cessation|chief financial|managing director|\bceo\b|\bcfo\b"),
    ("M&A", r"acquisition|amalgamation|merger|demerger|joint venture|scheme of arrangement"),
    ("litigation", r"litigation|show cause|penalty|order of|insolvency|nclt"),
    ("pledging", r"pledge|encumbrance"),
    ("fund_raise", r"\bqip\b|rights issue|preferential|buyback|commercial paper|non-convertible"),
    ("insider_trading", r"insider trading|reg(ulation)?\.? 7\(2\)|sast"),
    ("credit_rating", r"credit rating|\brating\b"),
    ("dividend", r"dividend"),
    ("bonus_split", r"bonus|sub-division|split"),
    ("capex", r"capacity expansion|capex|new plant|greenfield|brownfield"),
    ("investor_meetings", r"analyst|investor meet|institutional investor"),
    ("agm_egm", r"annual general meeting|\bagm\b|\begm\b"),
    ("postal_ballot", r"postal ballot"),
]


def classify(subject: str) -> Category | None:
    """Rule-based pass. Returns None when unsure — caller decides whether to escalate to an LLM."""
    s = subject.lower()
    for category, pattern in _RULES:
        if re.search(pattern, s):
            return category
    return None
