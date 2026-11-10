"""Deep research: an on-demand, 30–60 s read of everything primary a company has published recently.

  1. collect     refresh filings (12 months), prices, fundamentals, leadership          (no model)
  2. documents   last 4 concall transcripts, last 2 investor decks, latest annual report (no model)
  3. movements   financial inflections, material events + the market's reaction,
                 management changes, ownership shifts, unexplained big moves            (no model)
  4. extract     one cheap-model call per document (+1 for filings), page-cited JSON   (~8 calls)
  5. synthesize  one strong-model call over the extracted facts + actual numbers        (1 call)

Primary sources only (transcripts, decks, annual reports, exchange filings). No news, no broker notes.
Every model call is cached by input hash: re-running a company with no new documents costs nothing.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta, timezone

from app import config, llm
from app.ingest import documents as docs_mod
from app.ingest import store
from app.ingest.pipeline import ingest_company
from app.models import (
    Cite,
    DeepResearch,
    GuidanceItem,
    Movement,
    NetworkHint,
    Point_,
    PromiseCheck,
    Question,
    ResearchJob,
    ResearchStats,
    ResearchStep,
    SourceDoc,
    Theme,
)
from app.services import companies, filing_people, fundamentals, graph
from app.services.digest import _people_title, headline

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
FRESH_FOR = timedelta(hours=12)
_runner = ThreadPoolExecutor(max_workers=2, thread_name_prefix="research")

MATERIAL = {"results", "M&A", "fund_raise", "management_change", "litigation", "capex", "credit_rating", "pledging", "insider_trading", "press_release"}
STEPS = [
    ("collect", "Refreshing filings, prices and fundamentals"),
    ("documents", "Reading transcripts, investor decks and the annual report"),
    ("movements", "Finding the major movements"),
    ("extract", "Extracting guidance, themes and risks"),
    ("synthesize", "Writing the analysis"),
]


# ── jobs ───────────────────────────────────────────────────────────────────


def _save(job: ResearchJob) -> None:
    with store.connect() as con:
        store.upsert(con, "research_jobs", [{
            "id": job.id, "ticker": job.ticker, "status": job.status,
            "steps": [s.model_dump() for s in job.steps],
            "result": job.result.model_dump(mode="json") if job.result else None,
            "error": job.error, "started_at": job.started_at.isoformat(),
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }])


def _load(row) -> ResearchJob:
    return ResearchJob(
        id=row["id"], ticker=row["ticker"], status=row["status"], steps=json.loads(row["steps"]),
        started_at=row["started_at"], finished_at=row["finished_at"], error=row["error"],
        result=DeepResearch.model_validate(json.loads(row["result"])) if row["result"] else None,
    )


def get_job(job_id: str) -> ResearchJob | None:
    with store.connect() as con:
        row = con.execute("SELECT * FROM research_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    job = _load(row)
    if job.status in ("queued", "running") and datetime.now(timezone.utc) - job.started_at > timedelta(minutes=6):
        job = job.model_copy(update={"status": "error", "error": "Interrupted (the server restarted). Run it again."})
    return job


def latest(ticker: str) -> ResearchJob | None:
    with store.connect() as con:
        row = con.execute("SELECT * FROM research_jobs WHERE ticker=? AND status='done' ORDER BY finished_at DESC LIMIT 1", (ticker,)).fetchone()
    return _load(row) if row else None


def recent(limit: int = 8) -> list[dict]:
    """Latest finished report per company, newest first (for the Ask tab)."""
    with store.connect() as con:
        rows = con.execute("SELECT ticker, MAX(finished_at) AS finished_at, result FROM research_jobs WHERE status='done' GROUP BY ticker "
                           "ORDER BY finished_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        res = json.loads(r["result"] or "{}")
        out.append({"ticker": r["ticker"], "name": res.get("name") or r["ticker"], "finished_at": r["finished_at"],
                    "summary": res.get("summary"), "movements": len(res.get("movements", []))})
    return out


def start(ticker: str, refresh: bool = False) -> ResearchJob:
    t = ticker.upper().removesuffix(".NS")
    if not refresh and (done := latest(t)) and done.finished_at and datetime.now(timezone.utc) - done.finished_at < FRESH_FOR:
        return done
    with store.connect() as con:
        row = con.execute("SELECT * FROM research_jobs WHERE ticker=? AND status IN ('queued','running') ORDER BY started_at DESC LIMIT 1", (t,)).fetchone()
    if row and (running := get_job(row["id"])) and running.status in ("queued", "running"):
        return running  # one run per company at a time
    job = ResearchJob(id=uuid.uuid4().hex[:12], ticker=t, status="queued", steps=[ResearchStep(key=k, label=l) for k, l in STEPS],
                      started_at=datetime.now(timezone.utc))
    _save(job)
    _runner.submit(_run, job)
    return job


class _Progress:
    def __init__(self, job: ResearchJob):
        self.job = job

    def step(self, key: str, status: str, detail: str | None = None) -> None:
        for s in self.job.steps:
            if s.key == key:
                s.status = status  # type: ignore[assignment]
                if detail is not None:
                    s.detail = detail
        self.job.status = "running"
        _save(self.job)


def _run(job: ResearchJob) -> None:
    p = _Progress(job)
    try:
        job.result = research(job.ticker, p)
        job.status = "done"
    except Exception as e:  # surface, don't swallow: the UI shows the error and a retry
        log.exception("deep research %s failed", job.ticker)
        job.status, job.error = "error", f"{type(e).__name__}: {e}"
    job.finished_at = datetime.now(timezone.utc)
    _save(job)


# ── documents ──────────────────────────────────────────────────────────────

_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _period_key(period: str | None) -> tuple[int, int]:
    if not period:
        return (0, 0)
    if m := re.match(r"FY(\d{4})", period):
        return (int(m.group(1)), 3)
    if m := re.match(r"([A-Za-z]{3}) (\d{4})", period):
        return (int(m.group(2)), _MON.get(m.group(1).lower(), 0))
    return (0, 0)


def _pick_documents(ticker: str) -> list[dict]:
    with store.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT url, kind, period, title FROM documents WHERE ticker=? AND kind IN ('transcript','presentation','annual_report')", (ticker,))]
    out = []
    for kind, n, prefix in (("transcript", 4, "T"), ("presentation", 2, "P"), ("annual_report", 1, "A")):
        picks = sorted((r for r in rows if r["kind"] == kind), key=lambda r: _period_key(r["period"]), reverse=True)[:n]
        for i, r in enumerate(picks, 1):
            out.append({**r, "id": f"{prefix}{i}"})
    return out


_AR_KEYS = {
    r"management discussion|md&a|outlook|strategy|strategic": 3, r"segment": 2, r"capex|capital expenditure|capacity": 2,
    r"risk|threat|challenge": 2, r"related party": 3, r"contingent liabilit": 3, r"key audit matter|qualified opinion|emphasis of matter": 3,
    r"guidance|target|aspir": 2, r"order book|market share|new product|launch": 1, r"working capital|receivable|inventor": 1,
}


def _pages(url: str) -> list[tuple[int, str]]:
    with store.connect() as con:
        return [(r["page"], r["text"]) for r in con.execute("SELECT page, text FROM doc_pages WHERE url=? ORDER BY page", (url,))]


def _select_ar_pages(pages: list[tuple[int, str]], n: int = 30) -> list[tuple[int, str]]:
    """Annual reports run 300–500 pages. Send only the narrative pages that matter, so a run stays cheap."""
    scored = []
    for no, text in pages:
        low = text.lower()
        words = len(low.split())
        if words < 120:
            continue
        digits = sum(c.isdigit() for c in low) / max(len(low), 1)
        s = sum(w * len(re.findall(p, low)) for p, w in _AR_KEYS.items())
        if digits > 0.18:  # dense statement tables: numbers come from the standardised financials instead
            s *= 0.3
        scored.append((s, no, text))
    top = sorted(scored, reverse=True)[:n]
    return sorted(((no, text) for _, no, text in top), key=lambda x: x[0])


def _marked(pages: list[tuple[int, str]], limit: int) -> str:
    out, size = [], 0
    for no, text in pages:
        chunk = f"\n[p.{no}] " + " ".join(text.split())
        if size + len(chunk) > limit:
            break
        out.append(chunk)
        size += len(chunk)
    return "".join(out)


# ── movements (deterministic) ──────────────────────────────────────────────


def _session_reaction(con, ticker: str, when: datetime) -> tuple[float | None, str | None]:
    """Close-to-close move on the first session the market could react (after 15:30 IST → next session), and that session's date."""
    local = when.astimezone(IST)
    d = local.date().isoformat()
    op = ">" if local.hour * 60 + local.minute >= 15 * 60 + 30 else ">="
    s = con.execute(f"SELECT date, close FROM eod WHERE ticker=? AND date {op} ? ORDER BY date LIMIT 1", (ticker, d)).fetchone()
    if not s:
        return None, None
    prev = con.execute("SELECT close FROM eod WHERE ticker=? AND date < ? ORDER BY date DESC LIMIT 1", (ticker, s["date"])).fetchone()
    return (round((s["close"] / prev["close"] - 1) * 100, 1) if prev and prev["close"] else None), s["date"]


def _quarter_end(period: str) -> str:
    y, m = _period_key(period)
    if not y:
        return period
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return (nxt - timedelta(days=1)).isoformat()


def movements(ticker: str) -> list[Movement]:
    out: list[Movement] = []
    f = fundamentals.build(ticker)

    # Financial inflections over the last four quarters.
    if f:
        q = {s.key: {p.period: p.value for p in s.points} for s in f.quarterly}
        periods = [p.period for p in f.quarterly[0].points] if f.quarterly else []
        rev, pat, mar = q.get("revenue", {}), q.get("pat", {}), q.get("margin", {})

        def yoy(series: dict, p: str) -> float | None:
            mon, yr = p.split()
            prev = series.get(f"{mon} {int(yr) - 1}")
            cur = series.get(p)
            return (cur / prev - 1) * 100 if cur and prev and prev > 0 else None

        # quarterly series only holds 8; pull year-ago values from the full statement store
        with store.connect() as con:
            full = con.execute("SELECT line, period, value FROM financials WHERE ticker=? AND statement='quarters'", (ticker,)).fetchall()
        allq: dict[str, dict[str, float]] = {}
        for r in full:
            allq.setdefault(r["line"], {})[r["period"]] = r["value"]
        rev_all = allq.get("Sales") or allq.get("Revenue") or rev
        pat_all = allq.get("Net Profit") or pat
        for p in periods[-4:]:
            idx = periods.index(p)
            prev_p = periods[idx - 1] if idx else None
            for label, series in (("Revenue", rev_all), ("Net profit", pat_all)):
                g, g0 = yoy(series, p), yoy(series, prev_p) if prev_p else None
                if g is not None and g0 is not None and abs(g - g0) >= 10:
                    up = g > g0
                    out.append(Movement(date=_quarter_end(p), kind="financial", tone="positive" if up else "negative",
                                        title=f"{label} growth {'accelerated' if up else 'slowed'} to {g:+.0f}% YoY",
                                        detail=f"{p}: from {g0:+.0f}% the quarter before."))
            if prev_p and mar.get(p) is not None and mar.get(prev_p) is not None and abs(mar[p] - mar[prev_p]) >= 2:
                up = mar[p] > mar[prev_p]
                out.append(Movement(date=_quarter_end(p), kind="financial", tone="positive" if up else "negative",
                                    title=f"Margin {'expanded' if up else 'compressed'} to {mar[p]:.0f}%",
                                    detail=f"{p}: from {mar[prev_p]:.0f}% the quarter before."))
            vals = [v for v in rev_all.values() if v is not None]
            if rev_all.get(p) and vals and rev_all[p] >= max(vals) and p == periods[-1]:
                out.append(Movement(date=_quarter_end(p), kind="financial", tone="positive", title="Record quarterly revenue",
                                    detail=f"{p}: ₹{rev_all[p]:,.0f} cr, the highest in the last {len(vals)} quarters."))
        for s in f.signals:
            if s.section == "shareholding" and f.shareholding:
                last = f.shareholding[0].points[-1].period
                out.append(Movement(date=_quarter_end(last), kind="ownership", tone=s.tone, title=s.text.split(" (")[0], detail=s.text))

    # Material events in the last year, with the market's reaction.
    since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    name = companies.known().get(ticker).name if ticker in companies.known() else ticker
    seen: set[tuple] = set()
    event_dates: list[date] = []
    with store.connect() as con:
        rows = con.execute("SELECT * FROM announcements WHERE ticker=? AND filed_at>=? ORDER BY filed_at DESC", (ticker, since)).fetchall()
        for r in rows:
            extra = json.loads(r["extra"] or "{}")
            if r["category"] not in MATERIAL or extra.get("routine"):
                continue
            when = datetime.fromisoformat(r["filed_at"])
            key = (when.astimezone(IST).date(), r["category"])
            if key in seen:
                continue
            seen.add(key)
            people = filing_people.for_announcement(con, r["id"], name) if r["category"] == "management_change" else []
            title = _people_title(people) or headline(r["text"], r["nse_desc"])
            if extra.get("results"):
                rs = {x["metric"]: x for x in extra["results"]["rows"]}
                rv, pt = rs.get("Revenue", {}).get("yoy_pct"), rs.get("PAT", {}).get("yoy_pct")
                title = f"{extra['results']['period']} results" + (f": revenue {rv:+.0f}%, PAT {pt:+.0f}% YoY" if rv is not None and pt is not None else "")
            react, session = _session_reaction(con, ticker, when)
            tone = "positive" if (react or 0) >= 2 else "negative" if (react or 0) <= -2 else "neutral"
            out.append(Movement(date=key[0].isoformat(), kind="people" if people else "event", category=r["category"], title=title,
                                detail=r["summary"], tone=tone, reaction_pct=react, source_id=r["id"]))
            event_dates.append(key[0])
            if session:
                event_dates.append(date.fromisoformat(session))

        # Big moves with no filing nearby: worth asking about.
        px = con.execute("SELECT date, close FROM eod WHERE ticker=? AND date>=? ORDER BY date", (ticker, since[:10])).fetchall()
    moves = []
    for a, b in zip(px, px[1:]):
        if a["close"]:
            chg = (b["close"] / a["close"] - 1) * 100
            if abs(chg) >= 5:
                moves.append((abs(chg), b["date"], chg))
    for _, d, chg in sorted(moves, reverse=True)[:4]:
        dd = date.fromisoformat(d)
        if any(abs((dd - e).days) <= 2 for e in event_dates):
            continue
        out.append(Movement(date=d, kind="market", tone="positive" if chg > 0 else "negative",
                            title=f"Stock {'jumped' if chg > 0 else 'fell'} {abs(chg):.1f}% with no filing nearby",
                            detail="No exchange disclosure within two days; a question worth asking.", reaction_pct=round(chg, 1)))
    return _collapse(sorted(out, key=lambda m: m.date, reverse=True))


def _collapse(moves: list[Movement]) -> list[Movement]:
    """A drawn-out case files every few days. Keep one entry per (month, category): the one the market reacted to most."""
    groups: dict[tuple, list[Movement]] = {}
    order: list[tuple] = []
    for m in moves:
        k = (m.date[:7], m.category) if m.kind == "event" and m.category in ("litigation", "press_release", "credit_rating", "fund_raise") else (id(m),)
        if k not in groups:
            order.append(k)
        groups.setdefault(k, []).append(m)
    out = []
    for k in order:
        g = groups[k]
        lead = max(g, key=lambda m: abs(m.reaction_pct or 0))
        if len(g) > 1:
            lead = lead.model_copy(update={"detail": f"{(lead.detail + ' · ') if lead.detail else ''}+{len(g) - 1} related filing{'s' if len(g) > 2 else ''} this month",
                                           "cites": [c for m in g for c in m.cites][:3]})
        out.append(lead)
    return sorted(out, key=lambda m: m.date, reverse=True)


# ── model steps ────────────────────────────────────────────────────────────

_RULE = "Use ONLY the text provided; never outside knowledge. Cite the page number from the [p.N] markers. Be specific: numbers, periods, names."

MAP_PROMPTS = {
    "transcript": (
        "You read an Indian listed company's earnings-call transcript for an equity investor. " + _RULE + " Return JSON: "
        '{"guidance": [{"metric": str, "value": str, "horizon": str|null, "page": int}], '
        '"delivered": [{"claim": str, "page": int}], '
        '"themes": [{"title": str, "detail": str (<=30 words), "page": int}], '
        '"analyst_concerns": [{"concern": str, "answer": str (<=25 words), "page": int}], '
        '"tone": "confident"|"cautious"|"defensive"|"mixed"}'
    ),
    "presentation": (
        "You read an Indian listed company's investor presentation. " + _RULE + " Return JSON: "
        '{"kpis": [{"name": str, "value": str, "period": str|null, "page": int}], '
        '"strategy": [{"title": str, "detail": str (<=30 words), "page": int}], '
        '"guidance": [{"metric": str, "value": str, "horizon": str|null, "page": int}]}'
    ),
    "annual_report": (
        "You read selected pages of an Indian listed company's annual report. " + _RULE + " Return JSON: "
        '{"strategy": [{"title": str, "detail": str (<=30 words), "page": int}], '
        '"capex": [{"detail": str, "page": int}], '
        '"risks": [{"title": str, "detail": str (<=30 words), "page": int}], '
        '"red_flags": [{"type": "related_party"|"contingent_liability"|"auditor"|"other", "detail": str, "page": int}]}'
    ),
}

FILINGS_PROMPT = (
    "You read short excerpts of Indian stock-exchange filings for an equity investor. " + _RULE.replace(" Cite the page number from the [p.N] markers.", "") +
    ' For each item return {"id": str, "summary": str (<=20 words, what actually happened, with amounts), "importance": 1|2|3}. '
    'Return JSON: {"items": [...]}'
)

SYNTH_PROMPT = (
    "You are an equity analyst writing for a portfolio manager. You get: actual reported numbers, a list of dated movements, "
    "and facts extracted from the company's own transcripts, presentations and annual report (each fact carries a doc id and page). "
    "Analyse management, don't summarise them: compare what they promised with what the numbers show. "
    "Use ONLY the inputs. Every point must cite at least one {\"doc\": id, \"page\": n} from the inputs. No hype, no filler. "
    "Express money in ₹ crore (1 crore = 10 million; transcripts often quote millions or billions, so convert). Return JSON: "
    '{"summary": str (3-4 sentences: what changed in the last year and why it matters), '
    '"promised_vs_delivered": [{"quarter": str, "promised": str, "delivered": str, "verdict": "beat"|"met"|"missed"|"unclear", "cites": [...]}], '
    '"guidance": [{"metric": str, "value": str, "horizon": str|null, "cites": [...]}], '
    '"themes": [{"title": str, "detail": str, "cites": [...]}], "risks": [{"title": str, "detail": str, "cites": [...]}], '
    '"bull": [{"text": str, "cites": [...]}], "bear": [{"text": str, "cites": [...]}], '
    '"questions": [{"question": str, "why": str}]}  (3-5 bull, 3-5 bear, 3-5 questions)'
)


def _with_cites(items: list[dict], doc: str) -> list[dict]:
    for it in items or []:
        if isinstance(it, dict) and "page" in it:
            it["cites"] = [{"doc": doc, "page": it.pop("page")}]
    return items or []


def _extract(sources: list[SourceDoc], texts: dict[str, str], filings: list[dict], usage: llm.Usage, notes: list[str]) -> dict:
    jobs = []
    for s in sources:
        if s.kind in MAP_PROMPTS and texts.get(s.id):
            header = f"Document {s.id}: {s.title}\n"
            jobs.append((s.id, MAP_PROMPTS[s.kind], header + texts[s.id]))
    if filings:
        jobs.append(("F", FILINGS_PROMPT, json.dumps(filings, ensure_ascii=False)))

    def call(j):
        doc, system, prompt = j
        try:
            return doc, llm.json_call("cheap", system, prompt, usage=usage)
        except llm.LLMError as e:
            return doc, e

    out: dict = {}
    pool = ThreadPoolExecutor(max_workers=4)  # free tiers allow ~10–15 requests/min; 8 calls fit comfortably
    futures = {pool.submit(call, j): j[0] for j in jobs}
    done, pending = wait(futures, timeout=config.EXTRACT_BUDGET)
    for fut in done:
        doc, res = fut.result()
        if isinstance(res, Exception):
            notes.append(f"Couldn't read {doc}: {str(res)[:120]}")
            continue
        for k, v in res.items():
            if isinstance(v, list):
                res[k] = _with_cites(v, doc)
        out[doc] = res
    for fut in pending:  # don't hold the investor hostage to one slow model call; it still lands in the cache for next time
        notes.append(f"Skipped {futures[fut]}: the model was too slow this time (refresh later to include it).")
    pool.shutdown(wait=False, cancel_futures=True)
    return out


def _cites(raw, valid: set[str]) -> list[Cite]:
    """Models format citations loosely. Accept {"doc","page"} objects, "T1 p.4" strings, and flat ["T1", "4", "A1", "20"] lists."""
    out: list[Cite] = []

    def page(v) -> int | None:
        m = re.search(r"\d+", str(v)) if v is not None else None
        return int(m.group(0)) if m else None

    for c in raw if isinstance(raw, list) else []:
        if isinstance(c, dict) and c.get("doc") in valid:
            out.append(Cite(doc=c["doc"], page=page(c.get("page"))))
        elif isinstance(c, (str, int)):
            tok = str(c).strip()
            m = re.match(r"^([A-Z]\d+)\b[\s,:;-]*(?:p(?:age)?\.?\s*)?(\d+)?$", tok)
            if m and m.group(1) in valid:
                out.append(Cite(doc=m.group(1), page=int(m.group(2)) if m.group(2) else None))
            elif out and out[-1].page is None and re.fullmatch(r"(?:p(?:age)?\.?\s*)?\d+", tok):
                out[-1] = Cite(doc=out[-1].doc, page=page(tok))  # a bare page number belongs to the doc before it
    return out


def _expert_for(question: str, net: list) -> NetworkHint | None:
    """Route a question to a go-to person: their expertise phrase, or any of its key words, appears in it."""
    ql = question.lower()
    best = None
    for person in net:
        for e in person.expertise:
            words = [w for w in re.split(r"[^a-z]+", e.lower()) if len(w) >= 5]
            if e.lower() in ql or any(w in ql for w in words):
                hint = graph._hint(person, f"Go-to for {e}")
                if best is None or hint.strength > best.strength:
                    best = hint
    return best


# ── the run ────────────────────────────────────────────────────────────────


def research(ticker: str, p: _Progress | None = None) -> DeepResearch:
    t0 = time.monotonic()
    usage = llm.Usage()
    notes: list[str] = []
    step = p.step if p else (lambda *a, **k: None)

    step("collect", "running")
    rep = ingest_company(ticker, days=365, with_documents=False, use_llm=False, say=lambda m: None)
    if rep.errors:
        notes += [f"{k}: {v[:100]}" for k, v in rep.errors.items()]
    step("collect", "done", " · ".join(f"{k}" for k in rep.steps) or "partial")

    step("documents", "running")
    picks = _pick_documents(ticker)

    def fetch(d: dict) -> tuple[dict, int, str | None]:
        try:
            with store.connect() as con:
                n = docs_mod.ingest(con, d["url"], ticker=ticker, kind=d["kind"], period=d["period"], title=d["title"])
            return d, n, None
        except Exception as e:
            return d, 0, str(e)[:120]

    sources: list[SourceDoc] = []
    texts: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for d, n, err in pool.map(fetch, picks):
            if err:
                notes.append(f"Couldn't fetch {d['title']}: {err}")
                continue
            pages = _pages(d["url"])
            used = _select_ar_pages(pages) if d["kind"] == "annual_report" else pages
            limit = {"transcript": 70_000, "presentation": 30_000, "annual_report": 90_000}[d["kind"]]
            texts[d["id"]] = _marked(used, limit)
            label = {"transcript": "earnings-call transcript", "presentation": "investor presentation", "annual_report": "annual report"}[d["kind"]]
            sources.append(SourceDoc(id=d["id"], kind=d["kind"], title=f"{d['period'] or ''} {label}".strip(), period=d["period"],
                                     url=d["url"], pages=n, used_pages=len(used)))
    pages_read = sum(s.pages for s in sources)
    step("documents", "done", f"{len(sources)} documents · {pages_read:,} pages")

    step("movements", "running")
    moves = movements(ticker)
    step("movements", "done", f"{len(moves)} movements in 12 months")

    # Filing excerpts worth a one-line summary (the NSE one-liner is usually boilerplate).
    filings, fsources = [], []
    with store.connect() as con:
        since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        for r in con.execute("SELECT id, filed_at, nse_desc, text, attachment_url, category, extra FROM announcements WHERE ticker=? AND filed_at>=? "
                             "AND category IN ('M&A','capex','fund_raise','litigation','credit_rating','press_release','management_change') ORDER BY filed_at DESC LIMIT 15",
                             (ticker, since)):
            if json.loads(r["extra"] or "{}").get("routine"):
                continue
            body = docs_mod.text(con, r["attachment_url"], max_pages=2) if r["attachment_url"] else ""
            fid = f"F{len(fsources) + 1}"
            filings.append({"id": fid, "ann": r["id"], "date": r["filed_at"][:10], "label": r["nse_desc"], "summary_line": r["text"][:300], "excerpt": " ".join(body.split())[:1500]})
            fsources.append(SourceDoc(id=fid, kind="filing", title=f"{r['filed_at'][:10]} · {r['nse_desc']}", url=r["attachment_url"] or "", pages=0))
    sources += fsources

    f = fundamentals.build(ticker)
    name = f.name if f else (companies.known().get(ticker).name if ticker in companies.known() else ticker)
    result = DeepResearch(ticker=ticker, name=name, generated_at=datetime.now(timezone.utc), sources=sources, movements=moves,
                          network=graph.who_knows_company(ticker, limit=5),
                          stats=ResearchStats(seconds=0, documents=len(sources), pages_read=pages_read, llm={}, llm_available=llm.available()))

    if not llm.available() or not llm.probe():
        why = llm._disabled or "no LLM key configured"
        notes.append(f"Reading layer skipped: {why}. Movements above are computed without a model.")
        step("extract", "skipped", "needs a working LLM key")
        step("synthesize", "skipped", "needs a working LLM key")
    else:
        step("extract", "running", f"{len([s for s in sources if s.kind != 'filing'])} documents + filings")
        facts = _extract(sources, texts, filings, usage, notes)
        summaries = {i["id"]: i for i in facts.get("F", {}).get("items", []) if isinstance(i, dict)}
        ann_to_f = {x["ann"]: x["id"] for x in filings}
        for s in fsources:
            if s.id in summaries and summaries[s.id].get("summary"):
                s.title = f"{s.title}: {summaries[s.id]['summary']}"
        for m in moves:  # give generic event titles the substance the model read in the filing
            fid = ann_to_f.get(m.source_id or "")
            if fid and summaries.get(fid, {}).get("summary"):
                m.detail = summaries[fid]["summary"]
                m.cites = [Cite(doc=fid)]
        step("extract", "done", f"{usage.calls} model calls, {usage.cached} from cache")

        step("synthesize", "running")
        numbers = {s.name: {pt.period: pt.value for pt in s.points} for s in (f.quarterly if f else [])}
        payload = {
            "company": name,
            "documents": {s.id: s.title for s in sources},
            "reported_quarterly_numbers_rs_cr": numbers,
            "fundamental_signals": [s.text for s in (f.signals if f else [])],
            "movements": [{"date": m.date, "what": m.title, "market_reaction_pct": m.reaction_pct} for m in moves[:25]],
            "extracted": {k: v for k, v in facts.items() if k != "F"},
            "filings": [{"id": x["id"], "date": x["date"], "summary": summaries.get(x["id"], {}).get("summary") or x["summary_line"]} for x in filings],
        }
        try:
            out = llm.json_call("strong", SYNTH_PROMPT, json.dumps(payload, ensure_ascii=False), usage=usage)
            valid = {s.id for s in sources}
            result.summary = out.get("summary")
            result.promised_vs_delivered = [PromiseCheck(quarter=x.get("quarter", ""), promised=x.get("promised", ""), delivered=x.get("delivered", ""),
                                                         verdict=x.get("verdict") if x.get("verdict") in ("beat", "met", "missed") else "unclear",
                                                         cites=_cites(x.get("cites"), valid)) for x in out.get("promised_vs_delivered", []) if isinstance(x, dict)]
            result.guidance = [GuidanceItem(metric=x.get("metric", ""), value=x.get("value", ""), horizon=x.get("horizon"), cites=_cites(x.get("cites"), valid))
                               for x in out.get("guidance", []) if isinstance(x, dict)]
            result.themes = [Theme(title=x.get("title", ""), detail=x.get("detail", ""), cites=_cites(x.get("cites"), valid)) for x in out.get("themes", []) if isinstance(x, dict)]
            result.risks = [Theme(title=x.get("title", ""), detail=x.get("detail", ""), cites=_cites(x.get("cites"), valid)) for x in out.get("risks", []) if isinstance(x, dict)]
            result.bull = [Point_(text=x.get("text", ""), cites=_cites(x.get("cites"), valid)) for x in out.get("bull", []) if isinstance(x, dict)]
            result.bear = [Point_(text=x.get("text", ""), cites=_cites(x.get("cites"), valid)) for x in out.get("bear", []) if isinstance(x, dict)]
            # The network weave: route each question to someone who could answer it.
            net = graph.people()
            company_contacts = result.network
            qs = []
            for x in out.get("questions", []):
                if not isinstance(x, dict) or not x.get("question"):
                    continue
                expert = _expert_for(x["question"], net)
                qs.append(Question(question=x["question"], why=x.get("why"), ask=expert or (company_contacts[0] if company_contacts else None)))
            result.questions = qs
            step("synthesize", "done")
        except llm.LLMError as e:
            notes.append(f"The analysis couldn't be written this time ({str(e)[:100]}). The movements above are complete; refresh to retry.")
            step("synthesize", "error", "models busy; movements still complete")

    result.notes = notes
    result.stats = ResearchStats(seconds=round(time.monotonic() - t0, 1), documents=len(sources), pages_read=pages_read,
                                 llm=usage.as_dict(), llm_available=llm.available())
    return result
