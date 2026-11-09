import os
import tempfile

import pytest

# Default store for module-level imports; every test then gets its own empty one (see `isolated`).
os.environ["FINN_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Fresh empty store per test (so the digest uses fixtures) and no network: NSE, screener, Yahoo, Google News fail fast."""
    from app import config
    from app.ingest import eod, http
    from app.services import graph

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "finn.db")
    graph.invalidate()

    def no_net(*a, **k):
        raise http.FetchError("network disabled in tests")

    monkeypatch.setattr(http, "get", no_net)
    monkeypatch.setattr(eod, "fetch_eod", no_net)
    yield
    graph.invalidate()
