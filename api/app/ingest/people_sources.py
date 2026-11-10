"""Public sources for people at listed companies, plus resolving free-text employer names to NSE tickers.

  management  → Yahoo Finance company officers (name, title, birth year)
  board       → NSE corporate-governance XBRL (quarterly filing: every director, category, status)
  changes     → management-change filings already ingested (people_mentions): who joined / left since

No LinkedIn scraping anywhere: LinkedIn's terms forbid it. The investor's own connections come from
their LinkedIn data export (ingested elsewhere), which is their data to use.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from app import config
from app.ingest import http

_HONORIFIC = re.compile(r"^(mr|ms|mrs|dr|shri|smt|prof|capt|cdr|col|lt|gen)\.?\s+", re.I)


_DEGREES = {"btech", "mtech", "be", "bcom", "mcom", "mba", "pgdm", "pgdbm", "ca", "fca", "aca", "acs", "fcs", "cs", "cfa", "llb", "llm",
            "phd", "bsc", "msc", "cma", "icwa", "aicwa", "ba", "ma", "bba", "cpa", "frm", "acma", "fcma", "pgp"}


def _is_degree(tok: str) -> bool:
    return re.sub(r"[^a-z]", "", tok.lower()) in _DEGREES


def clean_name(name: str) -> str:
    """Drop honorifics and trailing qualifications: 'Mr. Anup Bagchi B.Tech, PGDM' → 'Anup Bagchi'."""
    n = " ".join(name.replace(" ", " ").split())
    while _HONORIFIC.match(n):
        n = _HONORIFIC.sub("", n)
    toks = n.split(",")[0].split()
    while len(toks) > 2 and _is_degree(toks[-1]):
        toks.pop()
    return " ".join(toks).strip(" .,")


def _parts(name: str) -> tuple[list[str], str]:
    toks = [t for t in re.split(r"[\s.]+", clean_name(name).lower()) if t]
    return (toks[:-1], toks[-1]) if toks else ([], "")


def same_person(a: str, b: str) -> bool:
    """Same surname and compatible first names: 'V S Rangan' ≈ 'Vedanthachari Srinivasa Rangan', 'Rakesh' ≈ 'Rakeshkumar'."""
    fa, la = _parts(a)
    fb, lb = _parts(b)
    if not la or la != lb:
        return False
    if not fa or not fb:
        return True
    x, y = fa[0], fb[0]
    if len(x) == 1 or len(y) == 1:
        return x[0] == y[0]
    return x.startswith(y) or y.startswith(x)


def name_key(name: str) -> str:
    """'Mr. Inder Thakurdas Jaisinghani' and 'Inder T. Jaisinghani' → 'inder jaisinghani'."""
    toks = [t for t in re.split(r"[\s.]+", clean_name(name).lower()) if t]
    full = [t for t in toks if len(t) > 1]
    if not full:
        return " ".join(toks)
    return f"{full[0]} {full[-1]}" if len(full) > 1 else full[0]


def fetch_officers(ticker: str) -> list[dict]:
    import yfinance as yf  # loaded on demand (see eod.py)

    info = yf.Ticker(f"{ticker}.NS").info or {}
    out = []
    for o in info.get("companyOfficers") or []:
        if o.get("name") and o.get("title"):
            out.append({"name": clean_name(o["name"]), "role": " ".join(o["title"].split()), "year_born": o.get("yearBorn"),
                        "source": "Yahoo Finance officers"})
    return out


_FACT = re.compile(r'<in-bse-cg:(\w+) contextRef="([^"]+)"[^>]*>([^<]*)</in-bse-cg:\1>')


def fetch_board(ticker: str) -> tuple[list[dict], str | None]:
    """Directors from the latest NSE corporate-governance report. Returns (directors, as-of date)."""
    r = http.get("https://www.nseindia.com/api/corporate-governance-master", params={"index": "equities", "symbol": ticker},
                 referer="https://www.nseindia.com/", accept="application/json")
    reports = [x for x in (r.json().get("data") or []) if x.get("xbrl")]
    if not reports:
        return [], None
    latest = reports[0]
    xml = http.get(latest["xbrl"], referer="https://www.nseindia.com/").text
    ctx: dict[str, dict[str, str]] = {}
    for tag, c, v in _FACT.findall(xml):
        ctx.setdefault(c, {})[tag] = " ".join(v.split())
    out = []
    for f in ctx.values():
        name = f.get("NameOftheDirector")
        if not name or (f.get("CurrentStatusDirector") or "Active").lower() != "active":
            continue
        cat = f.get("PositionOfDirectorInBoardOne") or "Director"
        chair = (f.get("PositionOfDirectorInBoardTwo") or "").lower()
        role = cat.replace("Non-Executive - ", "Non-executive ").replace("Independent Director", "independent director")
        if "chair" in chair:
            role = f"Chairperson · {role}"
        out.append({"name": clean_name(name), "role": role, "independent": "independent" in cat.lower(),
                    "since": f.get("DateOfAppointmentOfDirector"), "source": "NSE corporate-governance filing"})
    as_of = datetime.strptime(latest["date"], "%d-%b-%Y").date().isoformat() if latest.get("date") else None
    return out, as_of


# ── employer → ticker ─────────────────────────────────────────────────────

_SUFFIX = re.compile(r"\b(ltd|limited|pvt|private|inc|llp|plc|co|company|corporation|corp|the|india|group)\b\.?", re.I)


def org_key(name: str) -> str:
    s = _SUFFIX.sub(" ", name.lower().replace("&", " and "))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


@lru_cache
def nse_companies() -> dict[str, str]:
    """normalised company name → NSE symbol, from NSE's equity master list (cached on disk for a week)."""
    path = config.CACHE_DIR / "EQUITY_L.csv"
    fresh = path.exists() and datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < timedelta(days=7)
    if not fresh:
        try:
            body = http.get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", referer="https://www.nseindia.com/").text
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        except http.FetchError:
            if not path.exists():
                return {}
    out: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(path.read_text())):
        sym, name = row.get("SYMBOL"), row.get("NAME OF COMPANY")
        if sym and name:
            out.setdefault(org_key(name), sym)
    return out


# Former names and common shorthand that the exchange list won't contain.
ALIASES = {"zomato": "ETERNAL", "l and t": "LT", "lnt": "LT", "l t": "LT", "tcs": "TCS", "hul": "HINDUNILVR", "sbi": "SBIN",
           "m and m": "M&M", "mahindra and mahindra": "M&M", "icici": "ICICIBANK", "kotak": "KOTAKBANK", "kpit": "KPITTECH",
           "hal": "HAL", "chola": "CHOLAFIN", "cholamandalam": "CHOLAFIN", "sun pharma": "SUNPHARMA", "pi": "PIIND"}


@lru_cache
def nse_listing() -> list[tuple[str, str]]:
    """(symbol, company name) for every NSE equity — powers 'research any listed company' search."""
    nse_companies()  # ensures the CSV is cached on disk
    path = config.CACHE_DIR / "EQUITY_L.csv"
    if not path.exists():
        return []
    return [(r["SYMBOL"], r["NAME OF COMPANY"]) for r in csv.DictReader(io.StringIO(path.read_text())) if r.get("SYMBOL")]


def resolve_ticker(company: str, extra: dict[str, str] | None = None) -> str | None:
    """Free-text employer ('Polycab India Ltd', 'L&T') → NSE symbol, or None. Exact normalised match, else a unique prefix match."""
    if not company:
        return None
    k = org_key(company)
    if not k:
        return None
    index = {**nse_companies(), **ALIASES, **(extra or {})}
    if k in index:
        return index[k]
    if k.upper() in index.values():
        return k.upper()
    hits = {sym for name, sym in index.items() if name.startswith(k + " ") or k.startswith(name + " ")}
    return hits.pop() if len(hits) == 1 else None
