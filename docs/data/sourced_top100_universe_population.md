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
