"""Company headlines from Google News RSS (free, no key).

SECONDARY source. Shown to the investor as context, labelled as news, and never fed into the Pull
research sections, which stay grounded in primary documents only (per the brief).
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from app.ingest import http

RSS = "https://news.google.com/rss/search"
_SUFFIX = re.compile(r"\b(ltd|limited|pvt|private|corporation|corp|co)\b\.?", re.I)


def search_terms(name: str, ticker: str) -> list[str]:
    """'Eternal (Zomato)' → ['Eternal', 'Zomato']; 'P I Industries Ltd' → ['PI Industries']."""
    terms = [t.strip() for t in re.split(r"[()]", name) if t.strip()]
    out = []
    for t in terms:
        t = _SUFFIX.sub("", t)
        t = re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", t)  # "P I Industries" → "PI Industries"
        t = " ".join(t.split()).strip(" &,-")
        if len(t) >= 3:
            out.append(t)
    return out or [ticker]


def fetch(ticker: str, name: str, days: int = 30, limit: int = 25) -> list[dict]:
    terms = search_terms(name, ticker)
    q = " OR ".join(f'"{t}"' for t in terms) + f" when:{days}d"
    r = http.get(RSS, params={"q": q, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}, accept="application/rss+xml,*/*")
    root = ET.fromstring(r.content)
    # Relevance guard: the headline must actually name the company (first word of any term, or the ticker).
    keys = {t.split()[0].lower() for t in terms} | {ticker.lower()}
    seen: dict[str, dict] = {}
    for it in root.iter("item"):
        source = (it.findtext("source") or "").strip()
        title = (it.findtext("title") or "").strip()
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        if not any(re.search(rf"\b{re.escape(k)}\b", title.lower()) for k in keys):
            continue
        try:
            published = parsedate_to_datetime(it.findtext("pubDate") or "").isoformat()
        except (TypeError, ValueError):
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        nid = hashlib.sha1(f"{ticker}:{norm}".encode()).hexdigest()[:16]
        if nid not in seen:
            seen[nid] = {"id": nid, "ticker": ticker, "title": title, "source": source, "url": it.findtext("link"), "published_at": published}
    return sorted(seen.values(), key=lambda x: x["published_at"], reverse=True)[:limit]
