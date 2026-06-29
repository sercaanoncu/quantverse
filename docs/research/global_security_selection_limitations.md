# Global Security Selection Limitations

The global security-selection architecture is intentionally conservative.

## Key Limitations

- Current top-100 lists create survivorship bias when used historically.
- Point-in-time market-cap rankings are required for institutional-quality
  backtests.
- Global equities require FX handling, local calendars, corporate actions,
  delistings and liquidity controls.
- Commodity proxies such as ETFs or funds differ from spot commodities and
  futures because of fees, tracking structure and roll yield.
- Crypto universes must flag or exclude stablecoins and must account for
  exchange, custody, liquidity and weekend trading risk.
- Higher return alone is not enough; drawdown, CVaR, turnover, transaction costs
  and robustness matter.

## Why `not promoted` Is A Valid Result

A scientific system should reject weak candidates. If a portfolio fails the
promotion gate, the output should say `not promoted` rather than implying that a
model score is a buy signal.

## Next Sprint

The next sprint should add:

- sourced top-100 stock files,
- returns fetching for populated tickers,
- FX normalization,
- walk-forward stock-selection backtests,
- transaction-cost and turnover integration,
- master portfolio allocator across equity, crypto, real assets and defensive
  sleeves.
