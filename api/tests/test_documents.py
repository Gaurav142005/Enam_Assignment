import pytest

from app.ingest import documents, http, store


def test_oversized_attachment_is_remembered_and_not_downloaded_again(monkeypatch):
    calls = []

    def too_big(url, **k):
        calls.append(url)
        raise http.TooLarge(f"{url}: 13 MB is over the 12 MB limit")

    monkeypatch.setattr(http, "get_bytes", too_big)
    url = "https://nsearchives.nseindia.in/corporate/BIG.pdf"
    with store.connect() as con:
        with pytest.raises(http.TooLarge):
            documents.ingest(con, url, ticker="X", kind="filing", period=None, title="t")
        with pytest.raises(documents.Skipped):
            documents.ingest(con, url, ticker="X", kind="filing", period=None, title="t")
    assert calls == [url]  # the second refresh skipped it without a download


def test_skip_under_small_cap_does_not_block_a_larger_cap(monkeypatch):
    calls = []

    def too_big(url, **k):
        calls.append(k["max_bytes"])
        raise http.TooLarge("too big")

    monkeypatch.setattr(http, "get_bytes", too_big)
    url = "https://example.com/report.pdf"
    with store.connect() as con:
        with pytest.raises(http.TooLarge):
            documents.ingest(con, url, ticker="X", kind="filing", period=None, title="t")
        with pytest.raises(http.TooLarge):
            documents.ingest(con, url, ticker="X", kind="annual_report", period=None, title="t")
    assert calls == [12_000_000, 60_000_000]
