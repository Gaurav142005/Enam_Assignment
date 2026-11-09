"""LLM plumbing without a network: stub the provider, check JSON parsing, caching and graceful fallback."""

from app import config, llm
from app.ingest import classify


def test_json_call_caches(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "LLM_API_KEY", "test")
    monkeypatch.setattr(llm, "_gemini", lambda m, s, p, **k: calls.append(p) or '{"items": [{"id": "1", "category": "M&A", "routine": false, "summary": "x"}]}')
    a = llm.json_call("cheap", "sys", "prompt-1")
    b = llm.json_call("cheap", "sys", "prompt-1")
    assert a == b and len(calls) == 1  # second call served from SQLite cache


def test_classifier_uses_llm_only_for_leftovers(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test")
    seen = []

    def fake(model, system, prompt, **k):
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


def test_overloaded_model_falls_back_and_cools_down(monkeypatch):
    from app import llm as L

    monkeypatch.setattr(config, "LLM_API_KEY", "test")
    monkeypatch.setattr(config, "STRONG_MODEL", "big")
    monkeypatch.setattr(config, "STRONG_FALLBACKS", ["small"])
    monkeypatch.setattr(L, "_cool_until", {})
    seen = []

    def fake(model, system, prompt, **k):
        seen.append(model)
        if model == "big":
            raise L.LLMError("gemini 503: overloaded")
        return '{"ok": true}', 10, 2

    monkeypatch.setattr(L, "_gemini", fake)
    u = L.Usage()
    assert L.json_call("strong", "s", "p1", usage=u) == {"ok": True}
    assert L.json_call("strong", "s", "p2", usage=u) == {"ok": True}
    assert seen == ["big", "small", "small"]  # second call skipped the cooling model
    assert u.models == {"small": 2}
