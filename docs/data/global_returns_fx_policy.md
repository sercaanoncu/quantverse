# Global Returns and FX Policy

The global returns builder writes both simple and log returns:

- simple returns are used for portfolio aggregation and weighted portfolio
  return series,
- log returns are used for statistical diagnostics where additive time
  aggregation is useful.

The output files are:

- `data/processed/global_security_prices.csv`
- `data/processed/global_security_simple_returns_local.csv`
- `data/processed/global_security_simple_returns_usd.csv`
- `data/processed/global_security_log_returns_local.csv`
- `data/processed/global_security_log_returns_usd.csv`
- `data/processed/global_security_simple_returns.csv`
- `data/processed/global_security_log_returns.csv`
- `data/processed/global_security_returns.csv`
- `data/processed/global_returns_coverage_report.csv`
- `data/processed/global_fx_normalization_report.csv`
- `data/processed/global_fx_rate_coverage_report.csv`
- `data/processed/global_return_outlier_report.csv`

## Currency Discipline

The configured reporting base currency is USD. Local simple returns are
preserved, and non-USD investable returns are converted to USD simple returns
when a configured FX series is available.

The conversion rule is:

```text
usd_return = (1 + local_asset_return) * (1 + fx_return_to_usd) - 1
```

`fx_return_to_usd` must represent the local currency's return against USD. If
the configured quote is local currency per USD, the FX price is inverted before
returns are computed.

This is a hard promotion blocker for a global USD master portfolio. The system
may still produce a research candidate and diagnostics, but it must not promote
a global USD portfolio while any selected investable non-USD asset is missing
FX-normalized returns.

## FX Status Values

- `native_base`: asset is already in the base currency.
- `fx_normalized`: asset has aligned local and FX returns and is converted.
- `fx_missing`: required FX series is missing or has no aligned returns.
- `blocked`: asset return data is missing for an included investable asset.
- `signal_only`: row is not an investable portfolio asset.
- `not_investable`: row is excluded or benchmark-only.

## Coverage Discipline

Assets with insufficient price coverage are reported in
`global_returns_coverage_report.csv`. They are not silently converted into
zero-return assets. The outlier report flags extreme observations for review;
it does not delete them merely because they are large.
