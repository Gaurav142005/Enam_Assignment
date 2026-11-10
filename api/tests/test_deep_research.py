"""Deep research pieces that don't need the network or a model."""

from app.models import Movement
from app.services.deep_research import _collapse, _marked, _select_ar_pages


def test_repetitive_case_filings_collapse_to_one():
    ms = [Movement(date=f"2026-10-{d:02d}", kind="event", category="litigation", title=f"NCLT update {d}", reaction_pct=r)
          for d, r in [(30, 0.5), (14, -1.5), (7, -1.9)]]
    ms.append(Movement(date="2026-10-15", kind="event", category="results", title="Q2 results"))
    out = _collapse(sorted(ms, key=lambda m: m.date, reverse=True))
    assert [m.title for m in out] == ["Q2 results", "NCLT update 7"]  # biggest reaction kept, re-sorted by date
    assert "+2 related filings" in out[1].detail


def test_annual_report_page_selection_prefers_narrative():
    narrative = "Management discussion and analysis: our strategy, segment outlook, capex plans and key risks. " * 20
    table = " ".join(str(1000 + i) for i in range(400))
    pages = [(1, table), (2, narrative), (3, "short"), (4, narrative.replace("strategy", "related party transactions"))]
    picked = [no for no, _ in _select_ar_pages(pages, n=2)]
    assert picked == [2, 4]
    assert _marked([(7, "hello   world")], 100) == "\n[p.7] hello world"


def test_citation_formats_are_normalised():
    from app.services.deep_research import _cites

    valid = {"T1", "A1", "F10"}
    got = lambda raw: [(c.doc, c.page) for c in _cites(raw, valid)]
    assert got([{"doc": "T1", "page": 4}, {"doc": "X9", "page": 1}]) == [("T1", 4)]
    assert got(["F10", "A1", "20"]) == [("F10", None), ("A1", 20)]
    assert got(["T1 p.7", "A1, page 211"]) == [("T1", 7), ("A1", 211)]
    assert got(None) == [] and got("T1") == []
