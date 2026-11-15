"""Shorter card titles: strip filing boilerplate so a headline reads in one glance.

Deterministic and conservative: it only removes legal wrapping (dates, "of the Company",
regulation names, press-release framing) and never rewrites what happened.
"""

from __future__ import annotations

import re

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
_DATE = r"(?:[A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4}|\d{1,2}(?:st|nd|rd|th)? [A-Z][a-z]+,? \d{4})"

_PRESS = re.compile(r"^(?:A )?press release dated " + _DATE + r",? titled\s*", re.I)
_CLARIFY = re.compile(r"^The Exchange has sought clarification from .+? with respect to (?:a |the )?(?:recent )?news (?:item|report)s? captioned\s*", re.I)
_LODR = re.compile(r"Securities and Exchange Board of India \(Listing Obligations and Disclosure Requirements\)(?: Regulations,? 2015)?", re.I)
_DESIGNATED = re.compile(r"\b(?:Whole[- ]time|Additional|Executive) Director \(designated as ([^)]+)\)", re.I)
_ALIAS = re.compile(r"\s*\(\s*['\"]?[A-Z][\w.&]*['\"]?\s*\)")  # "Nahar Retail ... ( Nahar )"
_DATED = re.compile(r",?\s*\b(?:dated|held on|at its meeting held on|on)\s+" + _DATE + r",?", re.I)
_QUARTER = re.compile(r"(?:period|quarter)(?: and (?:half[- ]?year|nine months|year))? ended (?:on )?(" + _DATE + r")", re.I)
_RESULTS = re.compile(r"financial results", re.I)
_PERFORMANCE = re.compile(r"financial results|\bperformance\b", re.I)
_POSSESSIVE = re.compile(r"\b([A-Z][a-z]+) s\b")  # apostrophe lost in NSE's feed: "India s No. 1"


def _fiscal(d: str) -> str | None:
    """'September 30, 2026' / '30th September 2026' → 'Q2 FY27' (Indian April–March year)."""
    words = re.findall(r"[A-Za-z]+|\d+", d)
    month = next((_MONTHS[w.lower()] for w in words if w.lower() in _MONTHS), None)
    year = next((int(w) for w in words if len(w) == 4 and w.isdigit()), None)
    if not month or not year:
        return None
    q = ((month - 4) % 12) // 3 + 1
    fy = year + 1 if month >= 4 else year
    return f"Q{q} FY{fy % 100:02d}"


def tidy(title: str, text: str | None = None) -> str:
    out = _tidy(title)
    if text and re.fullmatch(r"(?:Board approves )?[Rr]esults(?:: follow-up filing)?", out):
        alt = _tidy(text)  # the filing text often names the quarter the title left out
        if re.match(r"Q\d FY\d\d results", alt):
            return out.replace("results", alt.split(" · ")[0]).replace("Results", alt.split(" · ")[0])
    return out


def _tidy(title: str) -> str:
    t = title.strip().rstrip("…").strip()
    t = _PRESS.sub("", t)
    t = t.strip("'\"“”‘’ ").rstrip(".")
    if _CLARIFY.search(t):
        t = "NSE asks for clarification on a report: " + _CLARIFY.sub("", t).strip("'\"“” ")

    t = re.sub(r"^Please find (?:enclosed|attached)(?: herewith)? (?:the |a )?", "", t, flags=re.I)
    q = _QUARTER.search(t)
    fy = _fiscal(q.group(1)) if q else None
    if _PERFORMANCE.search(t) and (fy or _RESULTS.search(t)):
        label = f"{fy} results" if fy else "Results"
        if re.match(r"Outcome of Board Meeting", t, re.I):
            return f"Board approves {fy + ' ' if fy else ''}results"
        if re.match(r"In continuation of our letter", t, re.I):
            return f"{label}: follow-up filing"
        tail = []
        if re.search(r"dividend", t, re.I):
            tail.append("dividend declared")
        if re.search(r"press release", t, re.I):
            tail.append("press release")
        if fy or tail or re.match(r"(?:un-?audited |audited |consolidated |standalone |and |\(|\))*financial results", t, re.I):
            return label + (f" · {', '.join(tail)}" if tail else "")

    t = _LODR.sub("SEBI listing rules", t)
    t = _DESIGNATED.sub(r"\1", t)
    t = re.sub(r"\bBoard of Directors of the Company\b", "Board", t)
    t = re.sub(r"\s+of the Company\b", "", t)
    t = _ALIAS.sub("", t)
    t = _DATED.sub("", t)
    t = re.sub(r"\b(Private )?Limited\b", "", t)
    t = _POSSESSIVE.sub(r"\1's", t)
    t = re.sub(r"\bNon- ", "Non-", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,;:-")
    t = re.sub(r"\s+([,.)])", r"\1", t)
    if len(t) > 96:  # one clean cut at a word boundary beats the card's mid-word clamp
        t = t[:94].rsplit(" ", 1)[0].rstrip(",;:-") + "…"
    return t[:1].upper() + t[1:] if t else title

