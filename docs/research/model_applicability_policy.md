# Model Applicability Policy

QuantVerse does not run a model merely because the model name sounds advanced.
Each model must have an appropriate input, output, metric and validation
context.

## Portfolio Models

Equal Weight, Inverse Volatility, Min Variance, Max Sharpe, Min CVaR,
cluster-balanced and policy-constrained candidates can be evaluated from a
returns matrix. Black-Litterman is blocked when sourced market caps are missing.
HRP and Risk Parity remain available in the broader project, but this global
stock master run lists unavailable variants explicitly when they are not wired
into the constrained global candidate engine.

## Forecasting and ML

Regression metrics such as RMSE, MAE and R2 are used only for regression-style
forecast diagnostics. Confusion matrix, ROC AUC and related classification
metrics are used only for downside classification diagnostics. AIC/BIC are
reported only where a statistical time-series model supports them.

LSTM/RNN, reinforcement learning and similar high-capacity methods are not
production allocation engines in this project. They require larger point-in-time
datasets, strict train/test separation, nested validation, transaction-cost
analysis and model governance before they can be considered.

## Output

The deterministic registry is produced by:

```python
from project.research.model_applicability import model_applicability_matrix
```

The global diagnostics script writes:

- `data/processed/model_applicability_matrix.csv`

The registry should be read as a guardrail against overclaiming, not as a list
of models that must always be run.
