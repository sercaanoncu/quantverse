# AGENTS.md - QuantVerse

## Project Identity

QuantVerse is a multi-asset quantitative portfolio research and risk-validation
system. It supports universe construction, market-data preparation, return/risk
analytics, portfolio optimization, backtesting, stress testing and transparent
research outputs.

## Non-Negotiable Rules

- Do not introduce look-ahead bias.
- Do not introduce survivorship bias without explicitly documenting it.
- Do not commit generated outputs unless explicitly requested.
- Do not silently change data assumptions.
- Do not hardcode fake tickers, fake market caps, fake ranks or fake prices.
- Do not mix daily and monthly frequency without explicit resampling logic.
- Do not treat missing data as zero returns unless explicitly justified.
- Do not change benchmark or risk-free assumptions silently.
- Do not claim guaranteed returns or provide investment advice.

## Financial Assumptions

- Annualization uses 252 trading days unless a task specifies otherwise.
- Long-only portfolios are the default.
- Portfolio weights must sum to 1 when long-only allocation is used.
- Risk-free rates must be aligned to the return frequency.
- Backtests must use only information available at the decision time.
- Transaction costs, slippage and rebalance frequency must be stated if used.

## Data Rules

Before analysis, validate ticker universe, date range, missingness, currency/base
denomination, adjusted-price assumptions, duplicate rows, calendar alignment and
asset-class mapping.

## Coding Rules

- Prefer clear, testable functions over notebook-only logic.
- Separate data loading, transformation, modeling and reporting.
- Keep configuration in config files, not hidden inside logic.
- Use deterministic random seeds when simulation is involved.
- Add tests for behavior-changing changes.
- Avoid broad refactors unless explicitly requested.

## Task Response Standard

Every substantial task response should include the goal, files changed,
assumptions, implementation summary, validation result, risks and next step.

## Risk Warnings

Flag suspicious returns, impossible volatility, data leakage, date misalignment,
extreme concentration, unstable covariance, optimizer infeasibility and benchmark
mismatch immediately.
