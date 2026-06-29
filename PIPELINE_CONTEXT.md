# PIPELINE_CONTEXT.md

## Pipeline Stages

1. Source universe input
2. Source validation
3. Market data download or local price loading
4. Price cleaning
5. Return calculation
6. Asset-class mapping
7. Risk metric calculation
8. Portfolio optimization
9. Backtest or projection
10. Report or research output generation

## Validation Checkpoints

- source files exist when required
- schema matches expected columns
- tickers are sourced and not placeholders
- date range is valid
- missing-data thresholds are respected
- returns are finite
- covariance matrix is usable
- optimizer constraints are feasible
- benchmark uses the same dates and universe where applicable
- generated outputs are reproducible

## Generated Outputs

Generated files must not be committed unless explicitly requested.
