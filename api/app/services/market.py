"""Prices for charts and portfolio performance. Reads the EOD store; fetches on demand for any NSE ticker."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from app.ingest import eod, store
from app.models import Bar, Holding, PerfPeriod, PortfolioPerformance, PriceHistory
from app.services import companies

log = logging.getLogger(__name__)
BENCHMARK = "NIFTY50"
STALE_AFTER = timedelta(hours=6)

RANGE_DAYS: dict[str, int] = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366, "3Y": 3 * 366, "5Y": 5 * 366}
PERIOD_DAYS: dict[PerfPeriod, int | None] = {"1D": None, "1W": 7, "1M": 31, "3M": 92, "6M": 183, "1Y": 366}


def ensure_prices(ticker: str, *, force: bool = False) -> None:
    """Fetch 5y of EOD if we have none or it's stale. Works for any NSE symbol, not just the portfolio."""
    with store.connect() as con:
        meta = con.execute("SELECT fetched_at FROM eod_meta WHERE ticker=?", (ticker,)).fetchone()
        have = con.execute("SELECT COUNT(*) FROM eod WHERE ticker=?", (ticker,)).fetchone()[0]
    fresh = meta and datetime.now(timezone.utc) - datetime.fromisoformat(meta["fetched_at"]) < STALE_AFTER
    if not force and have and fresh:
        return
    try:
        rows = eod.fetch_eod(ticker, period="5y")
    except Exception as e:  # yfinance raises a zoo of errors; a chart must not 500 because Yahoo hiccupped
        log.warning("price fetch %s failed: %s", ticker, e)
        return
    if rows:
        with store.connect() as con:
            store.upsert(con, "eod", rows)
            store.upsert(con, "eod_meta", [{"ticker": ticker, "fetched_at": store.now_iso(), "period": "5y"}])


def history(ticker: str, rng: str) -> PriceHistory:
    t = ticker.upper().removesuffix(".NS")
    ensure_prices(t)
    days = RANGE_DAYS.get(rng, 183)
    with store.connect() as con:
        last = con.execute("SELECT MAX(date) FROM eod WHERE ticker=?", (t,)).fetchone()[0]
        if not last:
            return PriceHistory(ticker=t, range=rng, bars=[])
        since = (date.fromisoformat(last) - timedelta(days=days)).isoformat()
        rows = con.execute(
            "SELECT date, open, high, low, close, volume FROM eod WHERE ticker=? AND date>=? ORDER BY date", (t, since)
        ).fetchall()
    bars = [Bar(time=r["date"], open=r["open"], high=r["high"], low=r["low"], close=r["close"], volume=r["volume"]) for r in rows]
    return PriceHistory(ticker=t, range=rng, bars=bars)


def _series(con, ticker: str, since: str) -> list[tuple[str, float]]:
    return [(r["date"], r["close"]) for r in con.execute(
        "SELECT date, close FROM eod WHERE ticker=? AND date>=? ORDER BY date", (ticker, since))]


def _period_return(con, ticker: str, period: PerfPeriod) -> tuple[float | None, list[float], str | None, float | None]:
    """(return %, sparkline closes, as-of date, last close). Start = last close on/before (as-of − period)."""
    last = con.execute("SELECT date, close FROM eod WHERE ticker=? ORDER BY date DESC LIMIT 1", (ticker,)).fetchone()
    if not last:
        return None, [], None, None
    asof = date.fromisoformat(last["date"])
    days = PERIOD_DAYS[period]
    if days is None:  # 1D: previous session
        prev = con.execute("SELECT date, close FROM eod WHERE ticker=? AND date<? ORDER BY date DESC LIMIT 1", (ticker, last["date"])).fetchone()
        start_close = prev["close"] if prev else None
        spark = [c for _, c in _series(con, ticker, (asof - timedelta(days=14)).isoformat())]
    else:
        target = (asof - timedelta(days=days)).isoformat()
        base = con.execute("SELECT close FROM eod WHERE ticker=? AND date<=? ORDER BY date DESC LIMIT 1", (ticker, target)).fetchone()
        start_close = base["close"] if base else None
        spark = [c for _, c in _series(con, ticker, target)]
    if len(spark) > 60:  # keep the payload small; shape is what matters in a sparkline
        step = len(spark) / 60
        spark = [spark[int(i * step)] for i in range(60)] + [spark[-1]]
    ret = round((last["close"] / start_close - 1) * 100, 2) if start_close else None
    return ret, [round(x, 2) for x in spark], last["date"], last["close"]


def performance(period: PerfPeriod) -> PortfolioPerformance:
    port = companies.portfolio()
    for c in [*port, companies.Company(ticker=BENCHMARK, name="Nifty 50", sector="Index")]:
        ensure_prices(c.ticker)
    pos = companies.positions()
    holdings: list[Holding] = []
    with store.connect() as con:
        for c in port:
            ret, spark, asof, close = _period_return(con, c.ticker, period)
            day, _, _, _ = _period_return(con, c.ticker, "1D")
            p = pos.get(c.ticker, {})
            qty, cost = int(p.get("qty") or 0), p.get("avg_cost")
            value = qty * close if qty and close else None
            # ₹ change over the period, holding today's quantity throughout
            start_px = close / (1 + ret / 100) if close and ret is not None else None
            day_px = close / (1 + day / 100) if close and day is not None else None
            holdings.append(Holding(
                ticker=c.ticker, name=c.name, sector=c.sector, last_close=close, as_of=asof, day_change_pct=day,
                return_pct=ret, spark=spark, qty=qty, avg_cost=cost, value=value,
                pnl=(value - qty * cost) if value is not None and cost else None,
                pnl_pct=round((close / cost - 1) * 100, 2) if close and cost else None,
                period_pnl=qty * (close - start_px) if qty and start_px else None,
                day_pnl=qty * (close - day_px) if qty and day_px else None,
            ))
        bench_ret, bench_spark, bench_asof, bench_close = _period_return(con, BENCHMARK, period)

    total = sum(h.value or 0 for h in holdings) or None
    for h in holdings:
        h.weight_pct = round(h.value / total * 100, 2) if total and h.value else None
    valued = [h for h in holdings if h.value and h.period_pnl is not None]
    if valued:
        weighting, start_val = "value", sum(h.value - h.period_pnl for h in valued)  # type: ignore[operator]
        port_ret = round(sum(h.period_pnl for h in valued) / start_val * 100, 2) if start_val else None  # type: ignore[misc]
    else:
        rets = [h.return_pct for h in holdings if h.return_pct is not None]
        weighting, port_ret = "equal", (round(sum(rets) / len(rets), 2) if rets else None)
    cost_total = sum(h.qty * h.avg_cost for h in holdings if h.qty and h.avg_cost) or None
    rets = [h.return_pct for h in holdings if h.return_pct is not None]
    holdings.sort(key=lambda h: (h.return_pct is None, -(h.return_pct or 0)))
    return PortfolioPerformance(
        period=period,
        as_of=max((h.as_of for h in holdings if h.as_of), default=None),
        portfolio_return_pct=port_ret,
        weighting=weighting,  # type: ignore[arg-type]
        total_value=total,
        total_cost=cost_total,
        total_pnl=(total - cost_total) if total and cost_total else None,
        day_pnl=sum(h.day_pnl or 0 for h in holdings) if total else None,
        period_pnl=sum(h.period_pnl or 0 for h in valued) if valued else None,
        benchmark_name="Nifty 50",
        benchmark_return_pct=bench_ret,
        benchmark_spark=bench_spark,
        up=sum(r > 0 for r in rets),
        down=sum(r < 0 for r in rets),
        holdings=holdings,
    )


def position(ticker: str) -> Holding | None:
    """The investor's holding in one company (1M period figures), or None if not held."""
    if ticker not in companies.positions():
        return None
    return next((h for h in performance("1M").holdings if h.ticker == ticker), None)
