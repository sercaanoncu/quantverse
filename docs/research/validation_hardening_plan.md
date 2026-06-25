# Validation Hardening Plan

## 1. Current Validation Protocol

QuantVerse uses a walk-forward protocol for champion-challenger research. At
each rebalance date, strategy weights are computed from historical data available
before that date. The resulting portfolio is then evaluated out-of-sample until
the next rebalance.

The current validation layer includes:

- Equal Weight benchmark comparison.
- Transaction costs and turnover.
- 0, 5, 10, 25 and 50 bps challenger cost sensitivity.
- Subperiod analysis.
- Rolling relative performance.
- Bootstrap confidence intervals versus Equal Weight.
- VaR exception tests.
- Stress scenarios.
- Promotion gates and lightweight overfit diagnostics.

## 2. Walk-Forward Strengths

Walk-forward evaluation reduces look-ahead risk because each decision uses only
past data. It also makes portfolio turnover and transaction costs observable in
the same timeline as the allocation decisions.

## 3. Remaining Risks

The project remains exposed to:

- Multiple testing: many strategies increase the chance of a lucky winner.
- Hyperparameter overfit: lookbacks and caps can be tuned too aggressively.
- Date sensitivity: results can depend on start and end dates.
- Asset-universe sensitivity: changing the universe can change the champion.
- Cost sensitivity: high-turnover models may fail after realistic costs.
- Turnover sensitivity: implementation friction can erase small edges.
- Regime instability: one regime can dominate full-sample results.

## 4. Purged / Embargoed CV Feasibility

Purged and embargoed validation is most important when labels overlap across
time, especially in supervised ML. The current alpha challengers are rule-based
walk-forward strategies, so purged CV is not required for the current outputs.
It should be added before any meta-labeling, classification or ML allocation
overlay is promoted.

## 5. CPCV Feasibility

Combinatorial Purged Cross-Validation is feasible as future work, but it would
increase complexity. It should be used when the project has a defined supervised
learning label and enough observations for many train/test splits.

## 6. Probabilistic Sharpe Ratio

Probabilistic Sharpe Ratio would help estimate whether an observed Sharpe is
meaningfully above a benchmark Sharpe after accounting for sampling uncertainty.
It is a future validation upgrade.

## 7. Deflated Sharpe Ratio

Deflated Sharpe Ratio adjusts for non-normality and multiple trials. It is
important when many strategies and parameter combinations are tested. The
current project uses a lightweight overfit flag, but full Deflated Sharpe is a
future upgrade.

## 8. PBO Approximation

The current `model_overfit_diagnostics.csv` is a lightweight PBO-style warning,
not a full Probability of Backtest Overfitting implementation. It flags
bootstrap intervals crossing zero, unstable subperiod behavior and rejected
evidence classes.

## 9. White Reality Check / SPA Future Work

White Reality Check or SPA can test whether the best strategy is truly superior
after accounting for multiple tested alternatives. This is future work because
it requires a careful definition of the strategy trial set.

## 10. Required Decision Rule For Promoting A Model

A model can be promoted only if the correct league-specific gate passes:

- Broad Default Champion: must beat Equal Weight on return, risk-adjusted,
  cost, drawdown, bootstrap, rolling and subperiod checks.
- Annual Return Challenger: must have the highest OOS CAGR and survive cost and
  bootstrap CAGR checks.
- Risk-Adjusted Champion: must beat on Sharpe/Sortino/Calmar and survive
  bootstrap and cost checks.
- Defensive Candidate: must improve drawdown or crisis behavior without hiding
  an unacceptable return or turnover cost.

If the evidence is weak, the model remains a research candidate or diagnostic
only. If it fails due to cost, instability or overfit risk, it is rejected for
allocation use.
