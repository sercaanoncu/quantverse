# Portfolio Projection Engine

The projection engine produces first-pass 1, 3, 6 and 12 month research
projections. It includes historical mean, EWMA, linear regression, ridge,
decision tree, random forest and gradient boosting baselines.

XGBoost, LightGBM and TensorFlow/LSTM are optional adapters. They are not added
as mandatory dependencies and are marked `not_available` when absent.

ROC output is produced only for downside classification tasks, such as the
probability of a negative forward return. ROC is not used for regression return
forecasts.

Projection outputs are scenario distributions, not guarantees.
