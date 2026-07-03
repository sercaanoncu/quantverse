# Real Global Universe Population

`scripts/populate_real_global_universe.py` creates sourced candidate universe
CSV files for the current global research layer. The script is not allowed to
invent tickers, market caps, ranks, source URLs or prices.

## Source Files

The population step writes current source-input CSVs under
`data/universe/sources/` for:

- NASDAQ proxy candidates,
- NYSE or broad US large-cap proxy candidates,
- Europe proxy candidates,
- Germany proxy candidates,
- UK candidates,
- Borsa Istanbul candidates,
- Japan proxy candidates,
- China/Hong Kong proxy candidates,
- crypto top-100 candidates,
- commodity/real-asset proxies,
- defensive bond, bill and cash proxies.

Compatibility files are also written for older config paths where needed.

## Source Method Policy

Each row includes `source_method`:

- `exact_market_cap_rank`: sourced market-cap rank is available.
- `index_proxy`: current index constituents are used as a documented proxy.
- `manual_review_required`: the row is a documented proxy that requires human
  review before publication or investment use.
- `api_market_cap_enriched`: market cap/rank comes from an API source.
- `yfinance_enriched`: reserved for sourced enrichment from yfinance metadata.

Missing `market_cap_usd` and `market_cap_rank` are allowed only when they are
reported transparently. A proxy file must not be described as an exact top-100
market-cap universe.

## Generated Coverage Reports

The population step writes:

- `data/processed/real_global_universe_population_summary.csv`
- `data/processed/real_global_universe_population_issues.csv`
- `data/processed/real_global_universe_market_cap_coverage.csv`
- `data/processed/real_global_universe_source_coverage.csv`

## Interpretation

Current constituent proxies are useful for a present-day research candidate, but
they do not support historical point-in-time backtest claims. Institutional
research needs dated membership files, market caps, delisting data and corporate
action reconciliation.
