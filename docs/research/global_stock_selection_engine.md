# Global Stock Selection Engine

This document describes the first architecture sprint for global security
selection in QuantVerse. The goal is to prepare a scientific research layer, not
to fabricate current top-100 stock lists or make buy recommendations.

## Why Single-Stock Selection Differs From ETF Allocation

ETF allocation chooses broad exposures. Single-stock selection chooses
individual securities with company-specific risk, sector concentration,
corporate actions, liquidity, currency and survivorship-bias concerns. A stock
selection engine therefore needs stronger universe controls than an ETF
allocation engine.

## Universe Requirements

Top-100 stock files must be sourced and dated. Current constituents cannot be
used as if they were historical constituents. Institutional-quality backtests
need point-in-time market-cap ranks, delisted names, corporate actions, FX
normalization and exchange calendars.

## Candidate Construction

The sprint adds deterministic functions that can:

- validate a global security universe,
- score assets from a supplied returns matrix,
- cluster assets by correlation,
- select a diversified candidate set,
- build long-only capped portfolio candidates,
- compare with Equal Weight and random portfolios,
- return `promoted` or `not promoted` through an evidence gate.

## Promotion Philosophy

Higher return alone is insufficient. A candidate must be evaluated using return,
risk, drawdown, CVaR, first-pass transaction-cost and turnover gates, random
portfolio benchmarking and look-ahead discipline. The system must be allowed to
say `not promoted`.

## Current Sprint Boundary

This sprint does not fetch live stock data, scrape market caps, build a global
master portfolio or change the existing ETF benchmark pipeline.
