# Sourced Global Universe Inputs

Place sourced current candidate CSV files in this directory before running the
global universe builder.

Expected files:

- `us_candidates.csv`
- `europe_candidates.csv`
- `uk_candidates.csv`
- `turkey_candidates.csv`
- `china_candidates.csv`
- `japan_candidates.csv`

Every row must include source metadata. Do not invent tickers, market caps,
ranks or source URLs. If market cap or rank is unavailable, leave it blank and
let the validator report coverage gaps.

Current candidate files are forward-looking research inputs only. Historical
claims require point-in-time constituent data.
