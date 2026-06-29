# Global Security Universe Schema

QuantVerse supports a future global security-selection universe, but this sprint
does not fabricate top-100 stock lists, market-cap rankings or point-in-time
historical constituents. Sourced universe files must be supplied before real
stock-selection analysis.

## Required Columns

Every universe CSV must include:

`ticker`, `name`, `sleeve`, `region`, `country`, `exchange`, `currency`,
`asset_type`, `sector`, `industry`, `market_cap_usd`, `market_cap_rank`,
`as_of_date`, `source`, `data_provider`, `investable`, `benchmark_only`,
`signal_only`, `include`, `proxy_type`, `notes`.

## Allowed Sleeve Values

- `global_equity_us`
- `global_equity_europe`
- `global_equity_uk`
- `global_equity_turkey`
- `global_equity_china`
- `global_equity_japan`
- `crypto`
- `commodity_real_assets`
- `defensive_bonds_cash`
- `etf_benchmark`
- `market_signal`

## Scientific Requirements

Current top-100 lists are not valid historical universes by themselves. A
historical backtest needs point-in-time constituents, market caps, corporate
actions, delistings, currencies, exchange calendars and data-vendor
reconciliation.

## Proxy Warning

Commodity rows in `data/universe/commodity_real_assets_universe.csv` use ETF or
fund proxies where available. ETF, ETC and futures-based proxies can differ
materially from spot commodity exposure because of fees, roll yield, liquidity
and tracking structure.
