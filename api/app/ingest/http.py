"""One polite HTTP client for every public source: browser UA, retries with backoff, per-host pacing."""

from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
_MIN_GAP = {"www.nseindia.com": 0.5, "www.screener.in": 1.5, "www.bseindia.com": 0.5}
_last: dict[str, float] = {}

_client = httpx.Client(
    headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
    timeout=httpx.Timeout(60, connect=15),
    follow_redirects=True,
)


class FetchError(RuntimeError):
    pass


def get(url: str, *, params: dict | None = None, referer: str | None = None, accept: str = "*/*", tries: int = 3) -> httpx.Response:
    host = urlparse(url).netloc
    headers = {"Accept": accept}
    if referer:
        headers["Referer"] = referer
    for attempt in range(tries):
        gap = _MIN_GAP.get(host, 0) - (time.monotonic() - _last.get(host, 0))
        if gap > 0:
            time.sleep(gap)
        _last[host] = time.monotonic()
        try:
            r = _client.get(url, params=params, headers=headers)
        except httpx.TransportError as e:
            err: str = str(e)
        else:
            if r.status_code == 200:
                return r
            err = f"HTTP {r.status_code}"
            if r.status_code == 404:
                break
        time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"{url}: {err}")
