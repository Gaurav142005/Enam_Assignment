"""screener.in company page → profile, multi-year financial tables, and primary-document links.

Only primary-source *links* and standardised financials are taken from screener; the documents
themselves (annual reports, concall transcripts) are fetched from BSE/company servers and read directly.
"""

from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser

from app.ingest import http

BASE = "https://www.screener.in/company"
STATEMENTS = ["quarters", "profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding"]


def _num(s: str) -> float | None:
    s = s.replace(",", "").replace("%", "").replace("₹", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _page(ticker: str, view: str) -> LexborHTMLParser:
    url = f"{BASE}/{ticker}/consolidated/" if view == "consolidated" else f"{BASE}/{ticker}/"
    return LexborHTMLParser(http.get(url, referer="https://www.screener.in/").text)


def _tables(t: LexborHTMLParser) -> list[dict]:
    rows: list[dict] = []
    for st in STATEMENTS:
        sec = t.css_first(f"section#{st}")
        table = sec.css_first("table") if sec else None  # first table only (shareholding has a yearly twin)
        if not table:
            continue
        trs = table.css("tr")
        periods = [th.text(strip=True) for th in trs[0].css("th")][1:]
        for tr in trs[1:]:
            cells = [td.text(strip=True) for td in tr.css("td")]
            if len(cells) != len(periods) + 1 or not cells[0]:
                continue
            line = re.sub(r"\s*\+$", "", cells[0]).strip()
            if line == "Raw PDF":
                continue
            for i, (p, v) in enumerate(zip(periods, cells[1:])):
                rows.append({"statement": st, "line": line, "period": p, "value": _num(v), "seq": i})
    return rows


def _documents(t: LexborHTMLParser) -> list[dict]:
    docs: list[dict] = []
    for blk in t.css("section#documents div.documents"):
        h = blk.css_first("h3")
        head = h.text(strip=True) if h else ""
        if head.startswith("Annual reports"):
            for a in blk.css("li > a"):
                m = re.search(r"(\d{4})", a.text())
                docs.append({"kind": "annual_report", "period": f"FY{m.group(1)}" if m else None,
                             "title": " ".join(a.text().split()), "url": a.attributes["href"]})
        elif head.startswith("Concalls"):
            for li in blk.css("li"):
                label = li.css_first("div")
                period = label.text(strip=True) if label else None
                for a in li.css("a"):
                    kind = {"Transcript": "transcript", "PPT": "presentation"}.get(a.text(strip=True))
                    if kind:
                        docs.append({"kind": kind, "period": period, "title": f"{period} concall {kind}", "url": a.attributes["href"]})
    seen: set[str] = set()
    return [d for d in docs if not (d["url"] in seen or seen.add(d["url"]))]


def fetch_company(ticker: str) -> dict:
    """Consolidated view when the company reports it, else standalone."""
    t = _page(ticker, "consolidated")
    view = "consolidated"
    tables = _tables(t)
    if sum(1 for r in tables if r["statement"] == "quarters" and r["value"] is not None) < 8:
        t, view = _page(ticker, "standalone"), "standalone"
        tables = _tables(t)

    h1 = t.css_first("h1")
    about = t.css_first(".company-profile .about") or t.css_first(".about")
    ratios = {}
    for li in t.css("#top-ratios li"):
        n, v = li.css_first(".name"), li.css_first(".value")
        if n and v:
            ratios[n.text(strip=True)] = " ".join(v.text().split())
    return {
        "name": h1.text(strip=True) if h1 else ticker,
        "about": " ".join(about.text().split()) if about else None,
        "ratios": ratios,
        "view": view,
        "financials": tables,
        "documents": _documents(t),
    }
