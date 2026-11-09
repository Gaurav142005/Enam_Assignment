"""EOD price & volume (Push triggers). Source: Yahoo Finance via yfinance, `<TICKER>.NS`.

To build in the Push phase:
  - fetch_eod(tickers, days=60)  → daily close/volume, cached per (ticker, date) in SQLite
  - detect_moves(tickers, rules) → |Δclose%| ≥ rules.price_move_pct or
                                   volume ≥ rules.volume_multiple × mean(volume, lookback)
"""
