# Current Global Universe Builder

This builder creates a first-pass current global equity universe from sourced CSV
inputs. It is forward-looking research infrastructure, not point-in-time
historical constituent reconstruction.

Required source CSV files may be supplied under `data/universe/sources/` for the
United States, Europe, United Kingdom, Turkey, China and Japan sleeves. The
builder supports ticker, name, exchange, country, currency, source, as-of date
and notes, with optional market-cap metadata. If market capitalization is
missing, the row is retained for audit coverage and reported in
`current_global_universe_missing_market_caps.csv`; no market cap is invented.

Current constituent lists must not be used to claim historical outperformance.
Institutional-quality historical tests require point-in-time membership,
market-cap, corporate-action, FX and delisting data.
