# Sourced Top-100 Universe Population

The real current global equity universe must be populated from sourced CSV files
under `data/universe/sources/`.

Required candidate files are listed in
`configs/source_universe_validation.yaml`. Each row must carry ticker, name,
exchange, country, currency, source, source URL, as-of date and data provider.
Market cap and market-cap rank may be blank, but blanks are reported by the
validator and cannot support a top-100-by-market-cap claim.

Do not claim a list is top-100 by market cap unless the source provides market
cap or rank evidence. Current lists are forward-looking research candidates only
and must not be used as historical point-in-time constituents.

Validate inputs before building the current universe:

```powershell
python scripts/validate_source_universe_inputs.py --config configs/source_universe_validation.yaml
```

## Current Source-Coverage Status

The current configured source files are required but may be absent on a fresh
checkout:

- `us_candidates.csv`
- `europe_candidates.csv`
- `uk_candidates.csv`
- `turkey_candidates.csv`
- `china_candidates.csv`
- `japan_candidates.csv`

When these sourced files are missing, the global quant orchestrator must return
`insufficient_inputs` and must not promote a global master portfolio. Example
files ending in `.example.csv` are schema templates only; they are not sourced
market-cap/rank evidence and must not be treated as exact top-100 inputs.
