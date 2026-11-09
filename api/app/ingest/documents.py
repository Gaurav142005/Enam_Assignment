"""Primary-source PDFs → page-indexed text, cached on disk by content hash (fetched + parsed once, ever)."""

from __future__ import annotations

import hashlib
import io
import sqlite3
import zipfile
from urllib.parse import urlparse

import pymupdf

from app import config
from app.ingest import http, store

_REFERER = {"nsearchives.nseindia.com": "https://www.nseindia.com/", "www.bseindia.com": "https://www.bseindia.com/"}


def _download(url: str) -> tuple[str, bytes, str | None]:
    """→ (sha, pdf bytes, xbrl xml). NSE ships some filings as a zip of PDF + SEBI XBRL; unpack those."""
    r = http.get(url, referer=_REFERER.get(urlparse(url).netloc), accept="application/pdf,application/zip,*/*")
    body, xbrl = r.content, None
    if not body:
        raise http.FetchError(f"{url}: empty response")
    if body[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            pdfs = sorted((i for i in z.infolist() if i.filename.lower().endswith(".pdf")), key=lambda i: -i.file_size)
            xmls = [i for i in z.infolist() if i.filename.lower().endswith(".xml")]
            xbrl = z.read(xmls[0]).decode("utf-8", "replace") if xmls else None
            body = z.read(pdfs[0]) if pdfs else b""
    if b"%PDF" not in body[:1024]:
        if xbrl:
            body = b""
        else:
            raise http.FetchError(f"{url}: not a PDF ({r.headers.get('content-type')})")
    sha = hashlib.sha256(body or (xbrl or "").encode()).hexdigest()
    if body:
        config.FILES_DIR.mkdir(parents=True, exist_ok=True)
        (config.FILES_DIR / f"{sha}.pdf").write_bytes(body)
    return sha, body, xbrl


def ingest(con: sqlite3.Connection, url: str, *, ticker: str, kind: str, period: str | None, title: str,
           max_pages: int | None = None) -> int:
    """Fetch + extract unless already stored. Returns page count."""
    row = con.execute("SELECT pages FROM documents WHERE url=? AND pages IS NOT NULL", (url,)).fetchone()
    if row:
        return row["pages"]
    sha, data, xbrl = _download(url)
    pages: list[dict] = []
    if data:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            n = pdf.page_count if max_pages is None else min(max_pages, pdf.page_count)
            pages = [{"url": url, "page": i + 1, "text": pdf[i].get_text()} for i in range(n)]
    con.execute("DELETE FROM doc_pages WHERE url=?", (url,))
    store.upsert(con, "doc_pages", pages)
    store.upsert(con, "documents", [{"url": url, "ticker": ticker, "kind": kind, "period": period, "title": title,
                                     "sha": sha, "pages": len(pages), "fetched_at": store.now_iso(), "xbrl": xbrl}])
    return len(pages)


def text(con: sqlite3.Connection, url: str, max_pages: int | None = None) -> str:
    q = "SELECT text FROM doc_pages WHERE url=? ORDER BY page" + (f" LIMIT {int(max_pages)}" if max_pages else "")
    return "\n".join(r["text"] for r in con.execute(q, (url,)))


def xbrl(con: sqlite3.Connection, url: str) -> str | None:
    row = con.execute("SELECT xbrl FROM documents WHERE url=?", (url,)).fetchone()
    return row["xbrl"] if row else None
