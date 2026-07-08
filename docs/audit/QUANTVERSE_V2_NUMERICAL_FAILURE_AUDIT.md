# QuantVerse v2 Numerical Failure Audit

Branch: `fix/v2-numerical-integrity-equity-scope`

This audit documents the numerical integrity failures reproduced before repair.
The existing artifact validator passed because it checked file existence, schema,
claim language and basic consistency, but it did not validate whether generated
financial numbers were mathematically or economically meaningful.

| Failure | Evidence file | Observed value | Why invalid | Root cause hypothesis | Fix required | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Portfolio risk metrics are all zero | `data/processed/global_portfolio_risk_report.csv` | 9 model rows have `cagr`, `annualized_return`, `annualized_volatility`, `sharpe`, `max_drawdown`, `var_95`, `cvar_95` equal to `0.0` | A non-empty multi-holding portfolio with real return observations should not have zero volatility and zero risk metrics unless explicitly marked `insufficient_data` | Portfolio return series is empty, misaligned, all-NaN, or all-zero after selected ticker/weight alignment | Recompute model returns from aligned returns matrix and weights; add validator gate for all-zero executable model metrics | Fixed by available-weight portfolio return series and numerical integrity gate |
| Walk-forward metrics are all zero | `data/processed/global_walk_forward_model_comparison.csv` | 10 model rows have zero average CAGR, return, volatility, Sharpe, drawdown and CVaR | Walk-forward with non-empty folds should produce non-zero risk/performance or mark the fold insufficient | Fold return series is empty/misaligned, or fallback metric path silently returns zeros | Fix walk-forward return alignment and forbid silent all-zero metrics | Fixed by shared portfolio return series in walk-forward folds |
| Random percentile report is degenerate | `data/processed/global_random_portfolio_percentile_report.csv` | Nearly every executable model has all percentile fields equal to `1.0` | A random benchmark distribution should not assign perfect percentiles to all models across all metrics | Random benchmark distribution is empty/zero, percentile direction is wrong, or model metrics are zero while random distribution is malformed | Rebuild percentile logic from same return window/universe and add degeneracy gate | Fixed by non-empty random portfolio return series and degeneracy validator |
| Forecast validation scale is absurd | `data/processed/global_forecast_validation_by_horizon.csv` | 12M `mean_mae` about `305`, while random-walk MAE about `0.625`; 1M `mean_mae` about `27.8` | Return forecasts should be in return units; MAE hundreds of units is incompatible with daily/monthly return-scale targets | Forecast target or horizon compounding uses price/percentage units inconsistently or crypto outliers contaminate default scope | Fix target/forecast unit scale, classify failed scale sanity, keep forecasts diagnostic | Fixed by equity-scoped forecast inputs, forecast-only outlier clipping and scale-sanity status |
| Default selection is crypto dominated | `data/processed/global_portfolio_league_weights.csv`, `data/processed/global_stock_scores.csv` | Equal Weight selected tickers begin with `UNI-USD`, `M-USD`, `CC-USD`, `USDE-USD`, `SKY-USD`, etc. | The default v2 output is intended as current stock/equity analysis; crypto should be optional and stablecoin-like assets should not drive selected stock output | Config and scoring allow `crypto_top100` sleeve into default selected universe | Add equity-only default scope and exclude crypto unless explicitly enabled | Fixed by default `equity_only` scope and separate multi-asset opt-in config |
| Risk contribution and return contribution are nonsensical | `data/processed/global_top_holdings_explanation.csv` | `risk_contribution_pct` includes `0.906` for one holding and small negative values; `expected_return_contribution` includes `156.47` | Percent contribution should sum to approximately one for valid positive-volatility portfolios; expected return contribution must be in documented return units and sanity checked | Contribution calculation uses unstable covariance/return scale or zero-denominator fallback | Recompute and label component/percentage contributions; validate sums and units | Fixed for risk contribution output by percentage-sum validator and negative-contribution labels |
| Excel output exists but is not a reliable dashboard | `output/excel/quantverse_v2_research_output.xlsx` | Required sheets exist, but `RISK_METRICS`, `WALK_FORWARD`, `RANDOM_PERCENTILES`, `FORECAST_VALIDATION` contain invalid numbers | Workbook existence does not imply financial validity | Validator checks sheet presence, not numerical sanity | Add `PORTFOLIO_DASHBOARD` and numerical integrity status after fixing metrics | Fixed by `PORTFOLIO_DASHBOARD` and required Excel-sheet validator |
| PDF output exists but does not prove analysis validity | `output/pdf/quantverse_v2_research_report.pdf` | PDF is generated while underlying metrics are all-zero/degenerate | Report generation must not imply completeness when numerical integrity fails | Report builder consumes generated CSVs without hard integrity gate | Add integrity status to generated reports and fail validator on numerical defects | Fixed by report integrity section and artifact validator numerical checks |

## Immediate Root-Cause Focus

The first repair target is return/weight alignment for portfolio risk,
walk-forward and random benchmark logic. Forecast scale and equity scope must be
fixed next because crypto/stablecoin contamination and return-unit mismatch make
the default output economically uninterpretable.

## Post-Repair Evidence

After the repair, `python scripts/validate_quantverse_v2_artifacts.py` includes
the hard numerical integrity checks from
`src/project/research/global_numerical_integrity.py`. The corrected equity
default run reports `Equal Weight` as the final public-data research model with
25 equity holdings, weight sum `1.0`, non-zero volatility and drawdown metrics,
non-degenerate random percentiles, and forecast validation that remains
diagnostic rather than investment advice.
