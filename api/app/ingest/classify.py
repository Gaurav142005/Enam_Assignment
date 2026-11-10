"""Announcement classification. Free layers first; the LLM only sees what rules can't place."""

from __future__ import annotations

import json
import logging

from app import llm
from app.models import Category
from app.services.taxonomy import BASE_WEIGHT, NSE_FIXED, classify, default_for, is_routine, text_rules

log = logging.getLogger(__name__)
CATEGORIES: list[str] = list(BASE_WEIGHT)

SYSTEM = (
    "You classify Indian stock-exchange (NSE) corporate announcements for an equity investor. "
    "Pick exactly one category per item from this list: " + ", ".join(CATEGORIES) + ". "
    "Use 'unclassified' for routine compliance paperwork that would not move the stock. "
    "Also return `routine`: true if, even within its category, the item is business-as-usual "
    "(e.g. a lender's regular debenture allotment, a scheduled-meeting intimation). "
    "Also return `summary`: one plain-English line (max 18 words) of what actually happened, or null if the text says nothing specific. "
    'Respond as JSON: {"items": [{"id": str, "category": str, "routine": bool, "summary": str|null}]}'
)


def classify_rows(rows: list[dict], *, pdf_text: dict[str, str] | None = None, use_llm: bool = True) -> None:
    """Mutates rows in place: sets category, category_source, routine (+ summary when the LLM gives one)."""
    pdf_text = pdf_text or {}
    pending: list[dict] = []
    for r in rows:
        cat = classify(r["text"], r["nse_desc"])
        source = "nse" if r["nse_desc"] in NSE_FIXED else "rules"
        if cat is None and r["id"] in pdf_text:
            cat = text_rules(pdf_text[r["id"]][:3000])
            source = "rules_pdf"
        if cat is None:
            pending.append(r)
            continue
        r.update(category=cat, category_source=source, routine=is_routine(cat, r["text"]))

    if pending and use_llm and llm.available():
        for i in range(0, len(pending), 25):
            batch = pending[i : i + 25]
            payload = [
                {"id": r["id"], "nse_label": r["nse_desc"], "text": r["text"][:400], "attachment_excerpt": pdf_text.get(r["id"], "")[:1500]}
                for r in batch
            ]
            try:
                out = llm.json_call("cheap", SYSTEM, json.dumps(payload, ensure_ascii=False))
                by_id = {str(x["id"]): x for x in llm.items(out) if "id" in x}
            except llm.LLMError as e:
                log.warning("LLM classification failed, using defaults: %s", e)
                by_id = {}
            for r in batch:
                x = by_id.get(r["id"])
                if x and x.get("category") in CATEGORIES:
                    r.update(category=x["category"], category_source="llm", routine=bool(x.get("routine")), summary=x.get("summary"))
    for r in pending:
        if "category" not in r:
            cat: Category = default_for(r["nse_desc"])
            r.update(category=cat, category_source="default", routine=cat == "unclassified")


SUMMARY_SYSTEM = (
    "You read excerpts of Indian stock-exchange (NSE) filings for an equity investor. For each item write `summary`: one plain-English "
    "line (max 16 words) saying what actually happened, with the key amount, counterparty or name. No boilerplate like 'the company has informed'. "
    "Use ONLY the text given; if it says nothing specific, return null. "
    'Respond as JSON: {"items": [{"id": str, "summary": str|null}]}'
)


def summarize_rows(rows: list[dict], pdf_text: dict[str, str]) -> int:
    """One batched cheap call: turn 'Updates' / 'Credit Rating' into what happened. Mutates rows; returns how many got a summary."""
    todo = [r for r in rows if r["id"] in pdf_text and not r.get("summary")]
    if not todo or not llm.available():
        return 0
    n = 0
    for i in range(0, len(todo), 12):
        batch = todo[i : i + 12]
        payload = [{"id": r["id"], "label": r["nse_desc"], "line": r["text"][:300], "excerpt": " ".join(pdf_text[r["id"]].split())[:1800]} for r in batch]
        try:
            out = llm.json_call("cheap", SUMMARY_SYSTEM, json.dumps(payload, ensure_ascii=False))
        except llm.LLMError as e:
            log.warning("filing summaries failed: %s", e)
            continue
        by_id = {str(x.get("id")): x.get("summary") for x in llm.items(out)}
        for r in batch:
            if by_id.get(r["id"]):
                r["summary"] = by_id[r["id"]].strip()
                n += 1
    return n
