# Risk And Covariance Upgrade Plan

## 1. Current Covariance Methods

QuantVerse currently computes several covariance estimates through the
`CovarianceEstimator` class:

- Sample covariance.
- Ledoit-Wolf shrinkage.
- OAS shrinkage.
- Constant-correlation shrinkage.
- Random-matrix denoising.
- Gerber statistic.
- EWMA covariance.

The current promoted covariance input for optimizers is Ledoit-Wolf. The
pipeline also writes `data/processed/covariance_model_comparison.csv` so the
available estimators are visible without changing the default.

## 2. Why Sample Covariance Is Fragile

Sample covariance is noisy when the number of assets is large relative to the
number of observations, when correlations change through time, or when the
sample contains extreme events. Small covariance errors can produce large weight
changes in optimization, especially in minimum-variance and Max Sharpe
allocations.

## 3. Why Ledoit-Wolf / Shrinkage Is Useful

Shrinkage pulls the noisy sample estimate toward a structured target. This can
reduce estimation error and improve conditioning. Ledoit-Wolf is therefore a
reasonable current default for a research project because it is transparent,
deterministic and widely understood.

## 4. Whether Nonlinear Shrinkage Is Feasible Now

Nonlinear shrinkage is feasible as a future upgrade, but it is not necessary for
the current sprint. It would require estimator selection, additional tests and
evidence that it improves downstream portfolio decisions rather than just
looking better mathematically.

Decision: future work.

## 5. Whether EWMA Covariance Is Feasible Now

EWMA is already feasible and already implemented as an estimator. It gives more
weight to recent observations and can react faster to volatility shifts. It is
now included in the covariance comparison output.

Decision: keep as comparison output; do not promote as default until portfolio
and risk tests support it.

## 6. Whether Factor Covariance Is Feasible Now

Factor covariance is institutionally useful because it decomposes risk into
interpretable drivers. QuantVerse already contains factor risk analysis, but a
full factor covariance allocator would require factor data quality checks,
factor selection governance and out-of-sample validation.

Decision: future institutional extension.

## 7. Whether DCC-GARCH Is Too Heavy

DCC-GARCH is too heavy for the current project because it increases statistical
and computational complexity while creating more tuning and validation burden.
It is better suited to a focused volatility-modeling project or an institutional
risk engine with strict model-risk controls.

Decision: not now.

## 8. How Covariance Quality Affects Portfolio Engines

Covariance quality directly affects:

- MinVar: very sensitive to covariance conditioning.
- MaxSharpe: sensitive to both covariance and expected-return estimates.
- HRP: less dependent on inversion, but still uses correlation structure.
- RiskParity: depends on stable risk contribution estimates.
- CVaR: less covariance-centered, but still affected by return distribution and
  scenario quality.

Improving covariance estimates can help risk allocation more reliably than
trying to predict expected returns directly.

## 9. What Should Be Implemented Now Versus Later

Implemented now:

- Keep Ledoit-Wolf as default covariance input.
- Produce covariance comparison table.
- Surface EWMA as a validated estimator candidate, not a default.

Later:

- Nonlinear shrinkage.
- Factor covariance.
- ES backtesting.
- Dynamic covariance promotion study.
- Full model-risk documentation for any promoted covariance change.
