"""Company Q&A: retrieval and the no-model fallback (offline, seeded pages)."""

from app import config
from app.ingest import store
from app.services import qa


def test_terms_expand_finance_vocabulary():
    t = qa._terms("What is management guiding for margins and capex?")
    assert "guidance" in t and "ebitda" in t and "capital expenditure" in t and "management" not in t


def test_retrieval_ranks_the_relevant_page_and_falls_back_without_a_model(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    filler = "The operator opened the call and read the safe harbour statement to all participants. " * 6
    with store.connect() as con:
        store.upsert(con, "documents", [{"url": "t1", "ticker": "QACO", "kind": "transcript", "period": "Oct 2026", "title": "x", "sha": "s", "pages": 2,
                                         "fetched_at": store.now_iso(), "xbrl": None}])
        store.upsert(con, "doc_pages", [
            {"url": "t1", "page": 1, "text": filler},
            {"url": "t1", "page": 2, "text": filler + "On margins, we guide to EBITDA margin of 11% to 13% over the medium term; capex guidance is Rs 1,200 crore."},
        ])
    docs = [{"id": "T1", "url": "t1", "kind": "transcript", "period": "Oct 2026", "title": "x"}]
    hits = qa._retrieve(docs, qa._terms("margin guidance"))
    assert [(p.doc, p.page) for p in hits] == [("T1", 2)]
    monkeypatch.setattr(qa, "_ensure_docs", lambda t: docs)
    a = qa.ask("QACO", "What is the margin guidance?")
    assert a.answer is None and a.passages[0].page == 2  # no model → closest passages, never an invented answer
