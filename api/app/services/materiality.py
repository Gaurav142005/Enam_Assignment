"""Can this filing move the share price? A deterministic call from what the filing is and says, plus what the market did.

Price-sensitive: results; company-level CEO / MD / CFO / Chair changes; real deals; equity raises and buybacks;
rating upgrades or downgrades; capex; pledges; promoter dealing; big orders; legal actions; bonus or split.
Not: divisional or independent-director appointments, rating reaffirmations, subsidiary paperwork, compliance reports,
trading plans, product launches and awards. Either way, a ≥3% move in the session the market saw it wins.
"""

from __future__ import annotations

import re

from app.models import Category

REACTION_PCT = 3.0

_SENIOR = re.compile(r"\b(ceo|chief executive|managing director|\bmd\b|cfo|chief financial|chair(?:man|person|woman)?|joint managing)\b", re.I)
_DIVISIONAL = re.compile(r"\b(division|divisional|complex|business unit|sbu|segment|vertical|subsidiary|region|regional|plant|zone|cluster|"
                         r"projects?|country|international business|helicopter|aircraft|unit)\b", re.I)
_OUTSIDE_BOARD = re.compile(r"\b(independent|non[- ]executive|nominee|additional director|company secretary|compliance officer|senior management)\b", re.I)
_PAPERWORK = re.compile(r"\b(incorporat\w*|dissol\w*|strike[- ]off|struck off|step[- ]down|name change|registered office|"
                        r"half[- ]yearly report|statement of deviation|utili[sz]ation|monitoring agency|compliance|intimation of record date)\b", re.I)
_RATING_MOVE = re.compile(r"\b(upgrad\w*|downgrad\w*|outlook (?:revised|changed)|revised (?:its |the )?outlook|(?:positive|negative) outlook|watch)\b", re.I)
_ORDER = re.compile(r"\b(orders?|contracts?|letter of award|LoA)\b", re.I)
_SOFT_PR = re.compile(r"\b(launch\w*|prize|awards?\b(?! of (?:a |an |the )?(?:contract|order))|recogni[sz]\w*|esg|csr|felicitat\w*|certificat\w*|conferred)\b", re.I)


def assess(category: Category | None, text: str, role: str | None = None, reaction_pct: float | None = None) -> tuple[bool, str]:
    """(price_sensitive, short reason). `text` is everything we know: title, summary, the exchange line."""
    if reaction_pct is not None and abs(reaction_pct) >= REACTION_PCT:
        return True, f"stock moved {reaction_pct:+.1f}% that session"
    c, t = category or "unclassified", text or ""
    if c == "results":
        return True, "results"
    if c == "management_change":
        r = role or t
        if _OUTSIDE_BOARD.search(r):
            return False, "board / non-executive change"
        if _SENIOR.search(r) and not _DIVISIONAL.search(r):
            return True, "top-management change"
        return False, "divisional or second-line change"
    if _PAPERWORK.search(t):
        return False, "paperwork"
    if c == "credit_rating":
        return (True, "rating moved") if _RATING_MOVE.search(t) else (False, "rating reaffirmed")
    if c == "insider_trading":
        return (False, "trading plan") if re.search(r"trading plan", t, re.I) else (True, "insider / promoter dealing")
    if c == "press_release":
        if _SOFT_PR.search(t) and not _ORDER.search(t):
            return False, "soft announcement"
        if _ORDER.search(t) or re.search(r"clarification|rumou?r|news (?:item|report)", t, re.I):
            return True, "order win or clarification"
        return False, "general announcement"
    if c in ("M&A", "fund_raise", "capex", "pledging", "litigation", "bonus_split"):
        return True, c.replace("_", " ")
    return False, "routine"
