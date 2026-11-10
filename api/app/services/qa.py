"""Ask a company a question. Retrieval over its own transcripts, decks and annual report; a cheap model answers with page cites.

Primary sources only, and the model is told to say when the documents don't answer. Retrieval is lexical (TF-IDF over
pages): at ~700 pages per company it is instant, needs no embedding calls, and finance questions are keyword-heavy.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from app import llm
from app.ingest import documents as docs_mod
from app.ingest import store
from app.models import Answer, Cite, Passage, Point_, SourceDoc
from app.services import deep_research, fundamentals, graph

_STOP = set(["a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "at", "by", "with", "from", "is", "are", "was", "were", "be", "been", "what", "which", "who", "how", "why", "when", "does", "do", "did", "has", "have", "had", "their", "its", "it", "this", "that", "these", "those", "about", "into", "over", "than", "then", "as", "management", "company", "companys", "say", "says", "said", "tell", "me", "us", "any", "there", "will", "would", "can", "could", "should", "much", "many", "last", "next", "year", "quarter"])
_SYN = {"capex": ["capex", "capital expenditure", "capacity"], "margin": ["margin", "margins", "ebitda"], "guidance": ["guidance", "guide", "guided", "outlook", "expect", "target"],
        "debt": ["debt", "borrowing", "leverage"], "demand": ["demand", "volume", "volumes"], "risk": ["risk", "risks", "concern", "headwind"],
        "export": ["export", "exports", "international"], "price": ["price", "pricing", "prices"]}

_ALIAS = {"guiding": "guidance", "guide": "guidance", "guided": "guidance", "outlook": "guidance", "target": "guidance", "expansion": "capex",
          "borrowing": "debt", "leverage": "debt", "pricing": "price", "volume": "demand", "overseas": "export", "international": "export",
          "worried": "risk", "worry": "risk", "concern": "risk", "headwind": "risk", "ebitda": "margin", "profitability": "margin"}

SYSTEM = (
    "You answer an equity investor's question about an Indian listed company using ONLY the excerpts provided "
    "(its earnings-call transcripts, investor presentations, annual report) and the reported numbers. Never use outside knowledge. "
    "If the excerpts do not answer the question, set found=false and say what is missing in one sentence. "
    "Be direct and specific: numbers, periods, who said it. Express money in ₹ crore. "
    'Return JSON: {"found": bool, "answer": str (2-4 sentences), "points": [{"text": str, "cites": [{"doc": str, "page": int}]}]} (0-4 points, each cited).'
)


def _terms(q: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z][a-z&-]+|\d{2,4}", q.lower()) if w not in _STOP and len(w) > 2]
    out: list[str] = []
    for w in words:
        stem = w[:-1] if w.endswith("s") and len(w) > 4 else w
        stem = _ALIAS.get(stem, stem)
        out += _SYN.get(stem, [w, stem] if stem != w else [w])
    return list(dict.fromkeys(out))


def _ensure_docs(ticker: str) -> list[dict]:
    """Transcripts + decks are small: fetch on first question. The annual report is used only if already read (deep research does that)."""
    fundamentals.ensure(ticker)
    picks = deep_research._pick_documents(ticker)

    def fetch(d: dict) -> dict | None:
        try:
            with store.connect() as con:
                have = con.execute("SELECT pages FROM documents WHERE url=? AND pages IS NOT NULL", (d["url"],)).fetchone()
                if not have and d["kind"] == "annual_report":
                    return None
                docs_mod.ingest(con, d["url"], ticker=ticker, kind=d["kind"], period=d["period"], title=d["title"])
            return d
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        return [d for d in pool.map(fetch, picks) if d]


def _retrieve(docs: list[dict], terms: list[str], k: int = 8) -> list[Passage]:
    pages: list[tuple[str, int, str]] = []
    with store.connect() as con:
        for d in docs:
            for r in con.execute("SELECT page, text FROM doc_pages WHERE url=? ORDER BY page", (d["url"],)):
                text = " ".join(r["text"].split())
                if len(text) > 200:
                    pages.append((d["id"], r["page"], text))
    if not pages or not terms:
        return []
    lows = [t.lower() for _, _, t in pages]
    df = Counter(term for term in terms for low in lows if term in low)
    n = len(pages)
    scored = []
    for (doc, page, text), low in zip(pages, lows):
        s = sum((1 + math.log(low.count(t))) * math.log(1 + n / df[t]) for t in terms if t in low)
        if s > 0:
            recency = {"T1": 1.25, "P1": 1.15, "T2": 1.1}.get(doc, 1.0)  # the latest call usually has the current answer
            scored.append((s * recency / (1 + len(low) / 6000), doc, page, text))
    scored.sort(reverse=True)
    return [Passage(doc=doc, page=page, text=text[:2600]) for _, doc, page, text in scored[:k]]


def ask(ticker: str, question: str) -> Answer:
    t = ticker.upper().removesuffix(".NS")
    docs = _ensure_docs(t)
    label = {"transcript": "earnings-call transcript", "presentation": "investor presentation", "annual_report": "annual report"}
    sources = {d["id"]: SourceDoc(id=d["id"], kind=d["kind"], title=f"{d['period'] or ''} {label[d['kind']]}".strip(), period=d["period"], url=d["url"]) for d in docs}
    passages = _retrieve(docs, _terms(question))
    hint = deep_research._expert_for(question, graph.people()) or next(iter(graph.who_knows_company(t, limit=1)), None)
    base = Answer(ticker=t, question=question, answer=None, passages=passages[:3], sources=[sources[i] for i in dict.fromkeys(p.doc for p in passages)], ask=hint)
    if not passages:
        return base.model_copy(update={"found": False, "answer": "No transcripts or presentations are available for this company yet, so there is nothing to ground an answer in."})
    if not llm.available():
        return base

    f = fundamentals.build(t)
    numbers = {s.name: {p.period: p.value for p in s.points[-5:]} for s in (f.quarterly if f else [])}
    excerpts = "\n\n".join(f"[{p.doc} p.{p.page}] ({sources[p.doc].title})\n{p.text}" for p in passages)
    prompt = f"Company: {f.name if f else t}\nQuestion: {question}\n\nReported quarterly numbers (₹ cr): {json.dumps(numbers)}\n\nExcerpts:\n{excerpts}"
    usage = llm.Usage()
    try:
        out = llm.json_call("cheap", SYSTEM, prompt, usage=usage)
    except llm.LLMError:
        return base
    valid = set(sources)
    points = [Point_(text=x.get("text", ""), cites=[Cite(doc=c["doc"], page=c.get("page")) for c in x.get("cites", []) if isinstance(c, dict) and c.get("doc") in valid])
              for x in out.get("points", []) if isinstance(x, dict) and x.get("text")]
    cited = list(dict.fromkeys(c.doc for p in points for c in p.cites)) or [passages[0].doc]
    return base.model_copy(update={"answer": out.get("answer"), "found": bool(out.get("found", True)), "points": points,
                                   "sources": [sources[i] for i in cited], "llm": usage.as_dict()})
