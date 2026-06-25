# Model Selection Protocol

This protocol defines how QuantVerse evaluates return-seeking challenger
allocations against Equal Weight without look-ahead bias, date cherry-picking or
performance fabrication.

## Objective

The primary question is:

Can a statistically defensible, out-of-sample, no-look-ahead allocation model
beat Equal Weight on CAGR under the same walk-forward protocol?

The primary metric is out-of-sample CAGR. Secondary metrics are Sharpe, Sortino,
Calmar, maximum drawdown, volatility, turnover, transaction-cost drag,
rebalance-period hit rate and rolling relative performance.

## Benchmark

Equal Weight is always included as the benchmark. It is not removed when a
challenger wins one metric. Equal Weight remains the reference because it is
simple, transparent, diversified and does not require expected-return
estimation.

## Data Separation

At every rebalance date:

1. The strategy may use only returns strictly before the traded day.
2. The train window is 504 trading days.
3. The next day's portfolio return is computed after the rebalance decision.
4. No strategy may use full-sample mean returns, full-sample covariance,
   full-sample regimes or final-period outcomes for weight selection.

## Validation and Out-of-Sample Rules

For fixed-rule challengers, parameters are pre-specified in code and then
evaluated walk-forward. For the Shrunk Max Sharpe challenger, shrinkage strength
is selected inside each rebalance window:

1. Split the available training window into sub-training and validation parts.
2. Estimate candidate weights on the sub-training part.
3. Select shrinkage strength using only the validation part.
4. Refit on the full training window using the selected shrinkage.
5. Apply weights to the next out-of-sample day.

The final out-of-sample comparison does not influence hyperparameter selection.

## Candidate Models

The implemented challengers are:

- Momentum Tilt 6M/12M.
- Dual Momentum Absolute.
- Volatility-Scaled Momentum.
- Risk-Managed Equal Weight.
- Regime-Aware Allocation.
- Asset-Class Momentum Rotation.
- Shrunk Max Sharpe Nested.

Black-Litterman Lite is not included in the production path for this sprint. A
neutral-prior momentum-view version would be too close to the implemented
momentum challengers without adding a defensible external prior. LSTM is also
excluded: the available sample is small for sequence models, and a proper
chronological retraining design would add complexity without clear evidence it
beats simple momentum.

## Evidence Classification

Allowed evidence classes are:

- Strong challenger.
- Moderate challenger.
- Weak challenger.
- Diagnostic only.
- Failed / not robust.

A raw CAGR win is not enough for broad champion status. The project also checks
cost sensitivity, bootstrap confidence intervals, rolling relative performance,
subperiod consistency and drawdown penalty.

## Data-Snooping Warning

Any winner discovered in this sprint remains a research result. It should be
treated as exploratory until it survives future unseen data or a locked
pre-registered validation period. A model can be a legitimate annual-return
challenger winner and still not be robust enough to replace Equal Weight as the
broad project champion.

## Current Decision Rule

The project separates two concepts:

- Annual-return challenger winner: a model that beats Equal Weight on OOS CAGR
  and survives bootstrap CAGR and cost checks.
- Broad champion replacement: a model that also has stronger Sharpe robustness,
  acceptable drawdown penalty, rolling consistency and subperiod consistency.

In the current run, Asset-Class Momentum Rotation satisfies the first condition
but not the second.
