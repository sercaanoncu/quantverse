# FX Normalization Implementation Plan

## Current Blocker

The global research layer contains USD and non-USD assets in the same candidate
universe. Before this sprint, the return matrix was explicitly labelled as mixed
local-currency evidence. That made a promoted global USD master portfolio
scientifically invalid, even when the portfolio candidate itself could be
constructed.

## Simple-Return Conversion Rule

Portfolio aggregation must use simple returns. For a non-USD local asset, the
USD return is:

```text
usd_return = (1 + local_asset_return) * (1 + fx_return_to_usd) - 1
```

`fx_return_to_usd` must represent the return of the local currency against USD
in the correct direction. If the configured FX quote is USD per local currency,
the quote return can be used directly. If the configured FX quote is local
currency per USD, the quote price must be inverted before return calculation.

Log returns may still be produced for diagnostics, but they are not used for
weighted portfolio aggregation.

## Required FX Metadata

Each currency mapping must define:

- currency code,
- FX ticker or source identifier,
- quote direction,
- expected interpretation,
- whether inversion is required,
- fallback behavior when unavailable.

The first supported mapping set covers USD, EUR, GBP, TRY, JPY, HKD, CNY, CNH,
CAD, CHF and AUD.

## Required Source and Provider Fields

The FX audit output records the FX ticker/source identifier, quote direction,
inversion flag, base currency, asset currency, return observations, aligned
observations, missing FX dates and final FX normalization status. The system
does not fabricate FX rates, tickers or source URLs.

## Implemented In This Sprint

- Local simple/log returns are preserved in separate local files.
- USD-normalized simple/log returns are written separately.
- Backward-compatible `global_security_returns.csv` now represents the
  USD-normalized simple return matrix.
- FX audit reports classify assets as `native_base`, `fx_normalized`,
  `fx_missing`, `blocked`, `signal_only` or `not_investable`.
- FX rate coverage is written separately.
- The global master promotion gate can clear the FX blocker only when selected
  non-USD assets are marked `fx_normalized`.

## Remaining Blockers

Clearing FX does not automatically promote a global USD master portfolio.
Remaining blockers may include missing market-cap/rank evidence, missing
point-in-time constituents, delisting handling, corporate-action reconciliation,
outlier review, walk-forward validation and other promotion-gate failures.

## Correctness Tests

The deterministic test plan covers:

- USD asset unchanged,
- EUR conversion with known local and FX returns,
- inverted quote conversion for currencies such as JPY or TRY,
- missing FX series producing `fx_missing`,
- calendar mismatch and missing FX dates being reported,
- signal-only assets not becoming investable FX blockers,
- global master promotion remaining blocked when selected non-USD assets lack
  `fx_normalized` status.
