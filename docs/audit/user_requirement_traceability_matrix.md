# User Requirement Traceability Matrix

This matrix reconstructs the user's requirements and maps each one to evidence, limitation and sprint action.

## Status Summary

- `met`: 26
- `partially_met`: 7

## Requirements

| # | Requirement | Status | Evidence | Limitation | Sprint Fix |
|---:|---|---|---|---|---|
| 1 | Real stocks must enter the analysis. | `met` | data/processed/real_global_universe_population_summary.csv | No exact historical point-in-time membership. | True |
| 2 | NASDAQ and NYSE must be represented separately. | `partially_met` | data/universe/sources/nasdaq_top100_candidates.csv; data/universe/sources/nyse_top100_candidates.csv | NYSE file is S&P 100 proxy, not pure NYSE top-100. | False |
| 3 | Europe, Germany, UK, BIST, Japan and China/HK must be represented. | `met` | data/processed/real_global_universe_population_summary.csv | Several are index proxies. | True |
| 4 | Gold, silver, oil, platinum and copper must be represented. | `met` | data/universe/sources/commodity_candidates.csv | ETF/fund proxies differ from spot/futures. | True |
| 5 | Crypto top 100 must be represented. | `met` | data/universe/sources/crypto_top100_candidates.csv | Yahoo ticker mapping can fail. | True |
| 6 | Bonds, bills and cash proxies must be represented. | `met` | data/universe/sources/bond_bill_candidates.csv | ETF proxy risk differs from direct bills/bonds. | True |
| 7 | Distinguish exact market-cap top-100 from index proxies. | `met` | source_method columns | Visual report was previously too table-heavy. | True |
| 8 | Do not claim exact top-100 when cap/rank evidence is missing. | `met` | data/processed/real_global_universe_market_cap_coverage.csv | Exact top-100 still blocked. | True |
| 9 | Region/sleeve clustering must be shown. | `partially_met` | global_master_asset_class_weights.csv; global_master_region_weights.csv | Exchange-level clustering is not separate. | True |
| 10 | Correlation clustering must be shown. | `met` | global_cluster_membership.csv | Cluster stability not bootstrapped. | True |
| 11 | Number of clusters must be justified. | `partially_met` | global_cluster_diagnostics.csv | Selection rule is still heuristic. | True |
| 12 | Holdings per cluster must be reported. | `met` | global_cluster_membership.csv | Full cluster table is dense. | True |
| 13 | Covariance estimation must be audited. | `met` | global_covariance_estimator_comparison.csv | Some condition numbers are red flags. | True |
| 14 | Simple and log return policy must be clear. | `met` | docs/data/global_returns_fx_policy.md | Needs plain Turkish in report. | True |
| 15 | Normality and stationarity diagnostics must be run and interpreted. | `met` | global_normality_tests.csv; global_stationarity_tests.csv | Raw counts need interpretation. | True |
| 16 | Non-normal returns trigger robust/tail-aware interpretation. | `met` | global_scientific_sanity_issues.csv | No full EVT/GARCH yet. | True |
| 17 | Models must be run only where scientifically appropriate. | `met` | model_applicability_matrix.csv | Could be hidden in old report. | True |
| 18 | Every full portfolio must have weights summing to 1. | `met` | portfolio_weight_sum_audit.csv | Generated outputs need re-audit after each run. | True |
| 19 | Negative weights must be blocked unless shorting is explicit. | `met` | portfolio_logic_audit_issues.csv | No shorting module. | True |
| 20 | Different portfolios may have different holding counts. | `met` | global_master_constraint_audit.csv | Selected universe shared within run. | True |
| 21 | Risk minimization and return seeking must be separated. | `partially_met` | global_master_model_comparison.csv | Need clearer narrative. | True |
| 22 | Forward projections must exist. | `met` | global_portfolio_projection_*.csv | Simulation assumptions are not forecasts. | True |
| 23 | Monte Carlo simulation must exist. | `met` | global_monte_carlo_projection.csv | No guarantee. | True |
| 24 | Stress testing must exist. | `met` | global_stress_test_results.csv | Stylized shocks. | True |
| 25 | Train/test or walk-forward validation must be labelled clearly. | `partially_met` | model_applicability_matrix.csv | Global master is not point-in-time walk-forward. | True |
| 26 | Confusion matrix/AUC only for classification. | `met` | global_forecast_confusion_matrix.csv; global_forecast_roc_auc.csv | Threshold is simple. | True |
| 27 | R2/RMSE/MAE only for regression. | `met` | global_forecast_regression_metrics.csv | Weak R2 must not be overclaimed. | True |
| 28 | AIC/BIC only for models that support it. | `met` | global_forecast_time_series_metrics.csv | NaN may confuse users. | True |
| 29 | Random portfolios must be compared with candidates. | `met` | global_master_random_portfolio_benchmark.csv | Random benchmark is not future proof. | True |
| 30 | PDF/presentation must be understandable with charts, not raw tables. | `partially_met` | output/pdf/quantverse_visual_scientific_audit_report.pdf | Requires QA. | True |
| 31 | Excel workbook must have START_HERE and plain Turkish. | `partially_met` | output/excel/quantverse_explainable_global_stock_output.xlsx | Depends on artifact-tool export. | True |
| 32 | Scientific errors, economic nonsense and suspicious metrics must be flagged. | `met` | global_scientific_sanity_issues.csv | Not all issues are fixed immediately. | True |
| 33 | Nothing should be promoted if FX/source/data quality blocks it. | `met` | global_master_decision_summary.json | FX and market-cap blockers remain. | True |
