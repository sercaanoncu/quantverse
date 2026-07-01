# QuantVerse Methodology Literature Mapping

This document maps the eight local methodology PDFs into QuantVerse validation
rules. It does not reproduce long copyrighted passages. Each book is used as a
methodological reference category and translated into practical project rules.

## Local Books Inspected

| Book file | Detected title/topic | Pages inspected | QuantVerse contribution |
|---|---|---:|---|
| `portfolio-optimization-book.pdf` | Portfolio Optimization, Daniel P. Palomar | 608 | Portfolio theory, constrained optimization, covariance fragility, CVaR, risk parity, robust interpretation. |
| `introduction-to-statistical-methods-for-financial-models_compress.pdf` | Introduction to Statistical Methods for Financial Models, Thomas A. Severini | 387 | Returns, financial statistics, covariance, statistical assumptions and model interpretation. |
| `_OceanofPDF.com_Statistical_Quantitative_Methods_in_Finance_-_Samit_Ahlawat.pdf` | Statistical Quantitative Methods in Finance, Samit Ahlawat | 301 | MLE, regression, distributional assumptions, quantitative portfolio management discipline. |
| `Machine_Learning_for_Algorithmic_Trading_Predictive.pdf` | Machine Learning for Algorithmic Trading, Stefan Jansen | 821 | Backtesting, leakage prevention, feature discipline, transaction costs and systematic trading validation. |
| `machine-learning-in-finance-matthew-f-dixon-igor-halperin-paul-bilokon_compress.pdf` | Machine Learning in Finance, Dixon, Halperin and Bilokon | 565 | Financial ML limitations, time-series caution, GARCH/PCA/deep-learning governance. |
| `_OceanofPDF.com_Machine_Learning_for_Economics_and_Finance_-_Isaiah_Hull.pdf` | Machine Learning for Economics and Finance in TensorFlow 2, Isaiah Hull | 321 | ML workflows, simulation, regularization and economics/finance model interpretation. |
| `ISLRv2_website.pdf` | An Introduction to Statistical Learning, James, Witten, Hastie and Tibshirani | 612 | Train/test discipline, regression/classification metrics, regularization, trees, boosting, PCA and clustering. |
| `quantitative_economics_with_python.pdf` | Quantitative Economics with Python, Sargent and Stachurski | 943 | Simulation, dynamic/economic reasoning, numerical discipline and reproducibility. |

## Portfolio Theory Rules

| Methodological principle | QuantVerse implementation rule | Current evidence | Status | Remaining blocker |
|---|---|---|---|---|
| A portfolio is a constrained weight vector, not a label. | Every full portfolio must show weights, sum-to-one status, long-only status and cap status. | `data/processed/global_master_candidate_weights.csv`, `data/processed/global_master_constraint_audit.csv` | Partially satisfied | Some generated candidate outputs remain research-only while universe inputs are insufficient. |
| Mean-variance and Max Sharpe are sensitive to expected-return estimation error. | Max Sharpe must be diagnostic unless validated out of sample and not blocked by data. | `data/processed/model_applicability_matrix.csv`, `data/processed/global_master_model_comparison.csv` | Satisfied as governance | Global walk-forward evidence is still missing. |
| Risk allocation models can reduce concentration but do not guarantee higher return. | HRP, Risk Parity and Min CVaR must be labelled by actual run status and risk objective. | `data/processed/model_applicability_matrix.csv` | Partially satisfied | Global report must keep blocked/not-run status explicit. |
| CVaR is tail-aware and should be interpreted with data limits. | CVaR must be shown with drawdown and stress results, not as a standalone success metric. | `data/processed/global_master_risk_report.csv`, `data/processed/global_stress_test_results.csv` | Partially satisfied | Tail estimates are weak while source/FX blockers remain. |
| Black-Litterman requires defensible priors and views. | Do not present Black-Litterman as valid allocation evidence without sourced market-cap priors or documented views. | `data/processed/global_black_litterman_prerequisite_report.csv` | Satisfied as blocker | Equity market-cap/rank priors remain missing. |

## Risk Rules

| Methodological principle | QuantVerse implementation rule | Current evidence | Status | Remaining blocker |
|---|---|---|---|---|
| Volatility, VaR, CVaR and drawdown describe different risks. | Reports must present return and risk jointly before promotion. | `data/processed/global_master_model_comparison.csv`, `data/processed/global_master_risk_report.csv` | Partially satisfied | Promotion remains blocked, so performance must not be marketed. |
| Non-normal financial returns weaken normal-only risk claims. | Normality rejection triggers robust/tail-aware language. | `data/processed/global_normality_tests.csv`, `data/processed/global_scientific_sanity_issues.csv` | Satisfied | Use historical CVaR, stress and bootstrap language. |
| Covariance matrices can be ill-conditioned. | Ill-conditioned covariance must flag optimizer instability. | `data/processed/global_covariance_estimator_comparison.csv`, audit issues | Satisfied | Prefer shrinkage/robust covariance before promotion. |
| Stress tests are scenario diagnostics, not forecasts. | Scenario analysis must be labelled assumption-based. | `data/processed/global_stress_test_results.csv` | Satisfied as policy | Scenario set needs final governance review. |

## Econometrics and Time-Series Rules

| Methodological principle | QuantVerse implementation rule | Current evidence | Status | Remaining blocker |
|---|---|---|---|---|
| Simple returns aggregate linearly in portfolio weights. | Use simple returns for weighted portfolio returns. | `docs/data/global_returns_fx_policy.md` | Satisfied as policy | Global returns matrix may be missing if source universe is missing. |
| Log returns are useful for diagnostics and additive time aggregation. | Use log returns for diagnostics, not direct weight aggregation. | `docs/data/global_returns_fx_policy.md` | Satisfied as policy | Must remain explicit in reports. |
| ARIMA/SARIMA require stationarity and fitted likelihood discipline. | AIC/BIC must not appear unless fitted likelihood models are actually used. | `data/processed/model_applicability_matrix.csv` | Satisfied as governance | No global allocation claim from ARIMA. |
| GARCH is a volatility model, not automatic allocation proof. | Treat GARCH as future/diagnostic unless implemented with validation. | `docs/research/model_applicability_policy.md` if present, model applicability output | Partially satisfied | Do not show GARCH as run unless evidence exists. |

## ML Validation Rules

| Methodological principle | QuantVerse implementation rule | Current evidence | Status | Remaining blocker |
|---|---|---|---|---|
| Train/test splits must be chronological for time-series finance. | No look-ahead and no test-period tuning. | `TESTING.md`, global research docs | Partially satisfied | Full global stock walk-forward is not yet complete. |
| Classification metrics apply to classification tasks only. | Confusion matrix/AUC must not be used for regression claims. | `data/processed/global_forecast_classification_metrics.csv` | Partially satisfied | Audit should keep metric-task mapping visible. |
| Regression metrics apply to regression tasks only. | R2/RMSE/MAE must not be used as portfolio-promotion proof. | `data/processed/global_forecast_regression_metrics.csv` | Partially satisfied | Forecast diagnostics remain diagnostic only. |
| Deep learning is high-risk without strict validation. | LSTM, RNN, Transformer and RL must not be production allocation engines in current state. | `data/processed/model_applicability_matrix.csv`, thesis governance | Satisfied as policy | Future only after point-in-time data and walk-forward validation. |

## Data, Source and FX Rules

| Methodological principle | QuantVerse implementation rule | Current evidence | Status | Remaining blocker |
|---|---|---|---|---|
| Source provenance is part of model validity. | Every sourced row needs provider, source URL and as-of date. | `docs/data/sourced_top100_universe_population.md`, source validation outputs | Partially satisfied | Missing sourced equity CSVs. |
| Current constituents are not point-in-time historical evidence. | Do not claim historical top-100 support from current lists. | `docs/data/sourced_top100_universe_population.md` | Satisfied as policy | Need dated historical memberships. |
| Mixed currencies invalidate a global USD portfolio claim. | Convert non-USD local returns into USD or block promotion. | `docs/data/global_returns_fx_policy.md`, FX reports | Partially satisfied | Current global master promotion remains blocked/insufficient input. |
| Market-cap-ranked top-100 requires market-cap or rank evidence. | Exact top-100 claims are forbidden without market-cap/rank evidence. | `data/processed/global_market_cap_rank_evidence_report.csv` | Satisfied as gate | Exact top-100 support is not available for required equity sleeves. |
