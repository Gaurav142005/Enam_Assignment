"""LLM plumbing without a network: stub the provider, check JSON parsing, caching and graceful fallback."""

from app import config, llm
from app.ingest import classify


def test_json_call_caches(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "_gemini", lambda m, s, p: calls.append(p) or '{"items": [{"id": "1", "category": "M&A", "routine": false, "summary": "x"}]}')
    a = llm.json_call("cheap", "sys", "prompt-1")
    b = llm.json_call("cheap", "sys", "prompt-1")
    assert a == b and len(calls) == 1  # second call served from SQLite cache


def test_classifier_uses_llm_only_for_leftovers(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test")
    seen = []

    def fake(model, system, prompt):
        seen.append(prompt)
        return '{"items": [{"id": "b", "category": "capex", "routine": false, "summary": "New plant in Gujarat"}]}'

    monkeypatch.setattr(llm, "_gemini", fake)
    rows = [
        {"id": "a", "nse_desc": "Credit Rating", "text": "CO has informed the Exchange about Credit Rating", "attachment_url": None},
        {"id": "b", "nse_desc": "General Updates", "text": "CO has informed the Exchange about General Updates", "attachment_url": None},
    ]
    classify.classify_rows(rows)
    assert rows[0]["category"] == "credit_rating" and rows[0]["category_source"] == "nse"
    assert rows[1]["category"] == "capex" and rows[1]["category_source"] == "llm" and rows[1]["summary"]
    assert len(seen) == 1 and '"id": "a"' not in seen[0]  # the rule-classified row never reached the model


def test_no_key_falls_back_to_defaults(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    rows = [{"id": "c", "nse_desc": "General Updates", "text": "CO has informed the Exchange about General Updates", "attachment_url": None}]
    classify.classify_rows(rows)
    assert rows[0]["category"] == "unclassified" and rows[0]["category_source"] == "default"
