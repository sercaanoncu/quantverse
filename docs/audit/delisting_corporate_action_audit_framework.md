# Delisting and Corporate-Action Audit Framework

## Rule

Institutional-grade equity backtesting requires delisting, split, dividend,
merger, ticker-change and corporate-action evidence. Adjusted prices from a
public provider are useful research inputs, but they do not by themselves prove
complete survivorship control.

## Required Fields

Future universe or price-audit outputs should include:

- `delisting_status`,
- `delisting_date`,
- `delisting_source_url`,
- `corporate_action_source`,
- `corporate_action_adjustment_status`,
- `split_adjustment_status`,
- `dividend_adjustment_status`,
- `ticker_change_status`.

## Current QuantVerse Status

The current global stock layer does not contain full delisting and
corporate-action audit evidence. Therefore it must not claim
institutional-grade historical backtesting.

## Promotion Rule

If delisting or corporate-action evidence is missing, global stock backtests
remain research-only and must not be promoted as institutional-grade evidence.
