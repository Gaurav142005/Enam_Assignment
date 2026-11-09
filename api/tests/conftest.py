import os
import tempfile

import pytest

# Tests run against an empty store → the digest uses synthetic fixtures (deterministic, offline).
os.environ["FINN_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No test may touch the network: NSE, screener, Yahoo and Google News all fail fast."""
    from app.ingest import eod, http

    def no_net(*a, **k):
        raise http.FetchError("network disabled in tests")

    monkeypatch.setattr(http, "get", no_net)
    monkeypatch.setattr(eod, "fetch_eod", no_net)
