# Global Returns and FX Policy

The global returns builder writes both simple and log returns:

- simple returns are used for portfolio aggregation and weighted portfolio
  return series,
- log returns are used for statistical diagnostics where additive time
  aggregation is useful.

The output files are:

- `data/processed/global_security_prices.csv`
- `data/processed/global_security_simple_returns.csv`
- `data/processed/global_security_log_returns.csv`
- `data/processed/global_security_returns.csv`
- `data/processed/global_returns_coverage_report.csv`
- `data/processed/global_fx_normalization_report.csv`
- `data/processed/global_return_outlier_report.csv`

## Currency Discipline

The configured reporting base currency is USD. The current sprint does not
implement full FX normalization for all non-USD listings. Therefore, a run that
contains local-currency assets is labelled
`local_currency_mixed_not_promotable`.

This is a hard promotion blocker for a global USD master portfolio. The system
may still produce a research candidate and diagnostics, but it must not claim a
promoted global USD portfolio until local returns are converted with correct FX
series, calendars and compounding logic.

## Coverage Discipline

Assets with insufficient price coverage are reported in
`global_returns_coverage_report.csv`. They are not silently converted into
zero-return assets. The outlier report flags extreme observations for review;
it does not delete them merely because they are large.
