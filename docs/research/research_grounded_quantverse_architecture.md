# Research-Grounded QuantVerse Architecture

QuantVerse is a research-grade multi-asset portfolio analytics system. It is
not a production trading platform and it is not investment advice. Its purpose
is to compare allocation methods under one reproducible protocol and to explain
why a model should or should not be trusted.

## 1. What QuantVerse Is Trying To Solve

QuantVerse studies a practical portfolio decision problem: given a multi-asset
universe, historical prices, transaction costs and risk constraints, what
allocation rule produces the strongest out-of-sample portfolio decision quality?

The system separates the problem into five parts.

1. Multi-asset portfolio selection: decide which investable assets remain after
   data-quality and history checks. Assets are not removed because their
   realized return was low.
2. Allocation sizing: assign weights to assets using Equal Weight, optimization,
   risk allocation or alpha-challenger rules.
3. Risk estimation: estimate covariance, volatility, drawdown, VaR, CVaR and
   stress behavior.
4. Return/risk trade-off: compare CAGR, Sharpe, Sortino, Calmar, maximum
   drawdown, turnover and transaction-cost drag.
5. Out-of-sample decision quality: evaluate models only through walk-forward
   decisions that use information available before the rebalance date.

The objective is not a lower prediction error in isolation. The objective is a
better net portfolio decision after costs, turnover, uncertainty and drawdown
constraints.

## 2. Why Equal Weight Remains A Necessary Benchmark

Equal Weight, or 1/N, is retained because expected-return estimation error is
severe. A small error in estimated expected returns can be amplified by mean-
variance optimization into large and unstable weights. Equal Weight avoids this
failure mode by not estimating expected returns at all.

Equal Weight also provides a strong diversification baseline. It does not know
which asset will win, but it avoids making a fragile concentrated bet based on a
noisy return forecast. Therefore, beating Equal Weight must be proven
out-of-sample. It cannot be assumed because a method is mathematically more
sophisticated.

In QuantVerse, Equal Weight is both a benchmark and the broad default champion
unless a challenger clears the promotion gates: CAGR, Sharpe, Calmar, cost,
bootstrap, subperiod, drawdown and overfit-risk checks.

## 3. Alpha Engine

The alpha engine is limited to defensible active-return families that can be
evaluated without look-ahead bias.

- Time-series momentum: each asset is evaluated against its own trailing trend.
- Cross-asset relative momentum: assets are ranked against each other using
  trailing returns known at the rebalance date.
- Asset-class momentum rotation: asset classes are ranked, then capital is
  diversified within the selected classes.
- Trend-following / moving average rules: allocation is increased only when the
  historical price proxy is above a trailing moving average.
- Volatility-scaled momentum: momentum is divided by recent realized volatility
  to avoid allocating purely to the noisiest winners.
- Risk-managed Equal Weight: Equal Weight is reduced in assets or classes with
  high recent volatility or drawdown.
- Signal-aware HRP Lite: a risk-allocation candidate that tilts inverse-
  volatility weights by trailing risk and momentum diagnostics.

All implemented alpha challengers are long-only, capped, walk-forward and net
of transaction costs. They use the same asset universe, dates, rebalancing
calendar and benchmark comparison.

## 4. Risk Engine

The current risk engine uses sample statistics, Ledoit-Wolf shrinkage covariance,
VaR/CVaR, drawdown analysis, stress scenarios and VaR exception tests. Ledoit-
Wolf is the promoted covariance input because linear shrinkage is more stable
than raw sample covariance in noisy multi-asset settings.

The roadmap is explicit:

- Nonlinear shrinkage: future upgrade; useful but requires careful validation.
- Factor covariance: future upgrade; useful for institutional risk attribution.
- EWMA / dynamic covariance: already produced as a comparison table, but not
  promoted as default until it passes backtest and risk checks.
- DCC-GARCH: too heavy for the current project scope unless the universe and
  validation design justify the additional complexity.
- Expected Shortfall backtesting: future upgrade beyond current VaR exception
  testing.

Risk and covariance forecasts are treated as more reliable than direct expected-
return forecasts, but they still require validation.

## 5. ML Engine

The current ML layer is a downside-risk diagnostic. It is not a direct trading
signal. This is intentional.

Raw daily return prediction is fragile because the signal-to-noise ratio is low,
relationships are unstable, regimes change, and transaction costs can erase
small predictive edges. The next defensible ML steps are overlay problems rather
than blind return prediction:

- Meta-labeling / trade filtering.
- Rebalance veto when risk is unusually high.
- Uncertainty-aware predictions.
- Regularized models before deep learning.
- Downside-risk overlays that change risk exposure, not autonomous asset picks.

LSTM, Transformer and reinforcement-learning allocation are not production
candidates in this project. They would require strict chronological retraining,
purged validation, cost-aware execution assumptions, model-risk governance and
evidence that they beat simple momentum and Equal Weight out-of-sample.

LLMs may support research, text/sentiment/event feature extraction, stress
scenario generation and governance documentation. They are not autonomous
portfolio managers.

## 6. Validation Engine

The validation engine is as important as the model. QuantVerse uses walk-forward
evaluation, transaction costs, turnover, subperiod analysis, rolling relative
performance, bootstrap confidence intervals and explicit promotion gates.

The target validation roadmap includes:

- Nested validation for hyperparameter selection.
- Purged and embargoed validation where overlapping labels are introduced.
- Bootstrap confidence intervals for return and Sharpe differences.
- Probabilistic Sharpe Ratio and Deflated Sharpe Ratio as future upgrades.
- Probability of Backtest Overfitting as a future full implementation.
- White Reality Check or SPA as future work for multiple testing.
- Cost, turnover, subperiod and regime robustness before promotion.

No model is promoted because it has the best single metric. Promotion requires a
decision rule that matches the model's intended league.

## 7. Governance Engine

QuantVerse includes governance language because portfolio models are easy to
overstate. The governance layer covers:

- Model cards and limitations.
- Not investment advice.
- Reproducibility commands and deterministic tests.
- Data-source limits, especially yfinance suitability for research but not
  production.
- Portfolio weight transparency.
- Transfer manifests for safe migration into a clean GitHub repository.
- Production-readiness gaps: institutional data, execution, tax, access control,
  limit management, monitoring, audit trail and model approval are not
  implemented.

The system is designed to be defensible in a research, GitHub, CV or interview
setting. It is not presented as a live trading platform.
