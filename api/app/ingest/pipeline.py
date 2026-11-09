"""Orchestrates ingestion for a company: fundamentals → prices → filings (+classify, enrich) → documents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from app.ingest import classify, documents, enrich, eod, http, nse, screener, store
from app.services.taxonomy import classify as free_classify

log = logging.getLogger(__name__)


def ingest_fundamentals(ticker: str) -> str:
    """screener.in → companies + financials + document links. Used by the CLI and on demand by the API."""
    company = screener.fetch_company(ticker)
    with store.connect() as con:
        store.upsert(con, "companies", [{"ticker": ticker, "name": company["name"], "isin": None, "about": company["about"],
                                         "ratios": company["ratios"], "screener_view": company["view"], "updated_at": store.now_iso()}])
        con.execute("DELETE FROM financials WHERE ticker=?", (ticker,))
        store.upsert(con, "financials", [{"ticker": ticker, **r} for r in company["financials"]])
        known = {r["url"] for r in con.execute("SELECT url FROM documents WHERE ticker=?", (ticker,))}
        store.upsert(con, "documents", [{"url": d["url"], "ticker": ticker, "kind": d["kind"], "period": d["period"],
                                         "title": d["title"], "sha": None, "pages": None, "fetched_at": None, "xbrl": None}
                                        for d in company["documents"] if d["url"] not in known])
    q = [r for r in company["financials"] if r["statement"] == "quarters"]
    kinds = {k: sum(1 for d in company["documents"] if d["kind"] == k) for k in ("annual_report", "transcript")}
    return (f"{company['name']} ({company['view']}): {len({r['period'] for r in q})} quarters, "
            f"{len(company['financials'])} data points, {kinds['annual_report']} annual reports, {kinds['transcript']} transcripts listed")


@dataclass
class Report:
    ticker: str
    steps: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


def ingest_company(
    ticker: str,
    *,
    days: int = 90,
    with_documents: bool = True,
    n_transcripts: int = 4,
    n_annual_reports: int = 1,
    pdf_days: int = 30,
    use_llm: bool = True,
    say: Callable[[str], None] = print,
) -> Report:
    ticker = ticker.upper().removesuffix(".NS")
    rep = Report(ticker)

    def step(name: str, fn: Callable[[], str]) -> None:
        try:
            rep.steps[name] = fn()
            say(f"  ✓ {name:<13} {rep.steps[name]}")
        except Exception as e:  # one broken source must not sink the others
            rep.errors[name] = f"{type(e).__name__}: {e}"
            say(f"  ✗ {name:<13} {rep.errors[name]}")

    def do_screener() -> str:
        return ingest_fundamentals(ticker)

    def do_news() -> str:
        from app.services import news

        items = news.refresh(ticker)
        return f"{len(items)} recent headlines"

    def do_eod() -> str:
        rows = eod.fetch_eod(ticker)
        if not rows:
            raise http.FetchError("no price history (is the ticker listed on NSE?)")
        with store.connect() as con:
            store.upsert(con, "eod", rows)
            store.upsert(con, "eod_meta", [{"ticker": ticker, "fetched_at": store.now_iso(), "period": "5y"}])
        last = rows[-1]
        return f"{len(rows)} sessions, last {last['date']} close ₹{last['close']:,.2f} vol {last['volume']:,}"

    def do_filings() -> str:
        rows = nse.fetch_announcements(ticker, date.today() - timedelta(days=days))
        cutoff = (date.today() - timedelta(days=pdf_days)).isoformat()
        pdf_text: dict[str, str] = {}
        xbrl: dict[str, str] = {}
        with store.connect() as con:
            # Read the attachment only where the one-line summary isn't enough.
            for r in rows:
                pre = free_classify(r["text"], r["nse_desc"])
                # Management changes: always (the person's profile is only in the PDF). Unknowns: recent ones only.
                wanted = pre == "management_change" or (pre is None and r["filed_at"][:10] >= cutoff)
                if r["attachment_url"] and wanted:
                    try:
                        documents.ingest(con, r["attachment_url"], ticker=ticker, kind="filing", period=r["filed_at"][:10],
                                         title=r["nse_desc"], max_pages=6)
                        pdf_text[r["id"]] = documents.text(con, r["attachment_url"])
                        if x := documents.xbrl(con, r["attachment_url"]):
                            xbrl[r["id"]] = x
                    except http.FetchError as e:
                        log.warning("attachment %s: %s", r["attachment_url"], e)
            classify.classify_rows(rows, pdf_text=pdf_text, use_llm=use_llm)

            n_people = n_results = 0
            for r in rows:
                extra: dict = {}
                if r["category"] == "results" and not r.get("routine"):
                    if cut := enrich.results_cut(con, ticker, r["filed_at"], r["text"]):
                        extra["results"] = cut
                        n_results += 1
                if r["category"] == "management_change" and r["id"] in pdf_text:
                    people, src = enrich.people_from_filing(r, pdf_text[r["id"]], xbrl=xbrl.get(r["id"]), use_llm=use_llm)
                    enrich.store_people(con, r, people, src)
                    n_people += len(people)
                r["extra"] = extra
            store.upsert(con, "announcements", [
                {"id": r["id"], "ticker": r["ticker"], "filed_at": r["filed_at"], "nse_desc": r["nse_desc"], "text": r["text"],
                 "attachment_url": r["attachment_url"], "category": r["category"], "category_source": r["category_source"],
                 "summary": r.get("summary"), "extra": {**r["extra"], "routine": bool(r.get("routine"))}}
                for r in rows
            ])
        src: dict[str, int] = {}
        for r in rows:
            src[r["category_source"]] = src.get(r["category_source"], 0) + 1
        return (f"{len(rows)} announcements in {days}d (classified by {src}); {len(pdf_text)} attachments read; "
                f"{n_results} results enriched; {n_people} people extracted")

    def do_documents() -> str:
        with store.connect() as con:
            picks = []
            for kind, n in (("transcript", n_transcripts), ("annual_report", n_annual_reports)):
                picks += con.execute(
                    "SELECT url, kind, period, title FROM documents WHERE ticker=? AND kind=? ORDER BY rowid LIMIT ?", (ticker, kind, n)
                ).fetchall()
            got, pages = [], 0
            for d in picks:
                try:
                    pages += documents.ingest(con, d["url"], ticker=ticker, kind=d["kind"], period=d["period"], title=d["title"])
                    con.commit()
                    got.append(d["period"] or d["title"])
                except http.FetchError as e:
                    log.warning("document %s: %s", d["url"], e)
        return f"{len(got)}/{len(picks)} documents, {pages} pages of text ({', '.join(got)})"

    say(f"\n▶ {ticker}")
    step("fundamentals", do_screener)
    step("prices", do_eod)
    step("filings", do_filings)
    step("news", do_news)
    if with_documents:
        step("documents", do_documents)
    return rep
