"""NSE corporate announcements → normalised rows → classified (rules first, LLM only for leftovers)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.ingest import http

IST = timezone(timedelta(hours=5, minutes=30))
API = "https://www.nseindia.com/api/corporate-announcements"


def fetch_announcements(ticker: str, since: date, until: date | None = None) -> list[dict]:
    until = until or date.today()
    r = http.get(
        API,
        params={"index": "equities", "symbol": ticker, "from_date": since.strftime("%d-%m-%Y"), "to_date": until.strftime("%d-%m-%Y")},
        referer="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        accept="application/json",
    )
    rows = r.json() if r.content else []
    out = []
    for x in rows:
        filed = datetime.strptime(x["sort_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        out.append(
            {
                "id": str(x["seq_id"]),
                "ticker": x["symbol"],
                "filed_at": filed.isoformat(),
                "nse_desc": (x.get("desc") or "").strip(),
                "text": " ".join((x.get("attchmntText") or "").split()),
                "attachment_url": x.get("attchmntFile") or None,
                "company_name": x.get("sm_name"),
                "isin": x.get("sm_isin"),
            }
        )
    return out
