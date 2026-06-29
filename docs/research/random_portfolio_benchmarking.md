# Random Portfolio Benchmarking

Random portfolio simulation is a robustness benchmark. It is not proof of
future superiority.

## Purpose

If a candidate cannot beat most random long-only capped portfolios on a
risk-adjusted metric, the candidate is weak. QuantVerse therefore compares the
candidate Sharpe ratio against a configurable random portfolio distribution.

## Scientific Interpretation

Passing a random benchmark means the result is less likely to be a trivial
weighting accident. It does not prove that the strategy will outperform in the
future. It also does not replace walk-forward validation.

## Constraints

Random portfolios must use the same return matrix, long-only rule, max weight
cap and available asset universe as the candidate. Tests use small random
counts for speed; research runs can use larger counts such as 10,000.

## Why Equal Weight Still Matters

Equal Weight remains a hard benchmark because it is simple, diversified and
low-assumption. A candidate should beat both Equal Weight and a high percentile
of random portfolios before promotion.
