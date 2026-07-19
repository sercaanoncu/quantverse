# QuantVerse v2 Metric And Unit Contract

## Scope

This document is the authoritative unit and formula contract for QuantVerse v2.
An output is invalid if its implementation, label, unit, sign, sampling scope or
missing-data handling conflicts with this contract.

## Global Conventions

| Item | Contract |
|---|---|
| Return frequency | Daily observations unless an artifact explicitly states another frequency |
| Annualization factor | 252 trading days |
| Portfolio weights | Decimal fractions; long-only; sum to 1 within numerical tolerance |
| Return unit | Decimal return (`0.01` means 1%) |
| Volatility unit | Annualized decimal standard deviation |
| Drawdown unit/sign | Decimal wealth loss from prior peak; always `<= 0` |
| VaR/CVaR unit/sign | Return-tail quantile/mean; losses are negative |
| Risk-free rate | Annual decimal; current v2 research policy is explicitly `0.0` |
| Transaction cost | Basis points applied to gross traded-notional L1 turnover |
| Base currency | USD only when the FX-normalization report validates conversion |
| Missing observations | Never interpreted as zero return |

## Returns

### Simple Asset Return

`r[t] = P[t] / P[t-1] - 1`

- **Use:** portfolio aggregation, realized wealth, drawdown and backtest output.
- **Validity:** prices must belong to the same security identity and use an
  adjusted-price convention appropriate for corporate actions.
- **Invalidation:** denominator is non-positive, security identity changes
  without verified continuity, or `r[t] < -1`. An exact -100% return is a valid
  terminal simple return but cannot enter a log-return model.
- **Missing data:** retained as missing until an explicit common-sample policy is
  applied; never filled with zero.

### Log Asset Return

`g[t] = log(P[t] / P[t-1]) = log(1 + r[t])`

- **Use:** distributional diagnostics and log-return Monte Carlo fitting.
- **Validity:** requires `r[t] > -1`.
- **Invalidation:** cannot be used as if it were a simple return in weighted
  portfolio arithmetic.

### Static Portfolio Return

`r_p[t] = sum_i w_i * r_i[t]`

- Every non-zero weight must have a return column.
- The calculation uses rows where the selected portfolio inputs satisfy the
  declared common-data policy.
- Missing weighted assets cause failure; the implementation must not silently
  drop and renormalize them.

### Wealth Index

`W[0] = 1`

`W[t] = W[t-1] * (1 + r_p[t])`

- The visual equity curve must begin at exactly 1.0.
- A return below -100% invalidates multiplicative wealth arithmetic. An exact
  -100% return sends wealth to zero and prevents subsequent log-return modeling.

## Annualized Performance

### Arithmetic Annualized Return

`annualized_return = mean(daily_simple_returns) * 252`

This is an arithmetic annualized sample mean. It is useful with annualized
volatility in Sharpe-style calculations, but it is not realized compounded
growth.

### Compound Annual Growth Rate

Given `T` valid daily simple returns and ending wealth `W[T]`:

`CAGR = W[T] ** (252 / T) - 1`

This is the geometric annualized growth rate. QuantVerse reports it separately
from arithmetic `annualized_return`; the labels must not be interchanged.

`annualized_volatility = sample_std(daily_returns, ddof=1) * sqrt(252)`

Invalidation conditions:

- fewer than two valid observations for volatility;
- mixed frequencies;
- missing returns treated as zero;
- annualization factor not disclosed;
- impossible or non-finite compounding.

## Risk-Adjusted Metrics

### Sharpe Ratio

The annual risk-free rate is converted to a daily compounded hurdle:

`rf_daily = (1 + rf_annual) ** (1 / 252) - 1`

`Sharpe = mean(r_p - rf_daily) / std(r_p, ddof=1) * sqrt(252)`

The ratio is invalid when excess-return volatility is zero or non-finite.
Current outputs must carry the 0% research assumption rather than imply a
historically reconstructed cash series.

### Sortino Ratio

`excess[t] = r_p[t] - rf_daily`

`downside_deviation = sqrt(mean(min(excess[t], 0) ** 2))`

`Sortino = mean(excess) / downside_deviation * sqrt(252)`

QuantVerse uses the lower partial second moment over all observations. A
conditional standard deviation computed only on negative observations must not
be labelled as this Sortino convention.

### Calmar Ratio

`Calmar = annualized_return / abs(max_drawdown)`

It is invalid if maximum drawdown is zero or non-finite.

## Drawdown And Tail Risk

### Drawdown

`running_peak[t] = max(W[0], ..., W[t])`

`drawdown[t] = W[t] / running_peak[t] - 1`

`max_drawdown = min_t drawdown[t]`

Every drawdown value must be `<= 0` within tolerance.

### Historical VaR At 95%

`VaR_95 = quantile(r_p, 0.05)`

### Historical CVaR / Expected Shortfall At 95%

`CVaR_95 = mean(r_p[t] | r_p[t] <= VaR_95)`

Both are return-space statistics, so adverse losses normally appear as negative
numbers. They are historical estimates, not distribution-free guarantees.

Daily parametric VaR/CVaR must not be labelled as annual VaR/CVaR by multiplying
the tail statistic by `sqrt(252)`. That scaling is not a valid general
annual-loss distribution. A longer-horizon tail estimate requires an explicit
multi-period return distribution or empirical rolling compounded returns.

## Turnover And Costs

For consecutive target weight vectors:

`gross_traded_notional_turnover = sum_i abs(w_i[t] - w_i[t-1])`

`cost_decimal = gross_traded_notional_turnover * transaction_cost_bps / 10000`

This convention charges both sale and purchase notional. A complete rotation
between two fully invested assets therefore has gross traded-notional turnover
of 2.0, while an initial purchase from cash has turnover of 1.0. The cost is
deducted on the rebalance date. It is a simplified linear proxy and excludes
spread dynamics, market impact, taxes, borrow, lot sizes, partial fills and
execution delay. Outputs must not relabel it as the alternative
`0.5 * L1` one-way turnover convention.

## Covariance And Correlation

- Covariance-dependent allocation uses complete cases for selected assets.
- Optimizer paths use Ledoit-Wolf shrinkage where declared.
- A covariance matrix must be finite, symmetric within tolerance and positive
  semidefinite within numerical tolerance.
- Correlation distance is `sqrt((1 - rho) / 2)` where the HRP implementation
  requires it.
- Constant series are not assigned fabricated zero correlation. They receive
  deterministic singleton clusters in the general correlation clustering
  diagnostic.
- A sample-covariance output is allowed only when its estimator is labelled and
  its purpose is diagnostic.

## Portfolio Constraints

For every full long-only candidate:

- `sum_i w_i = 1` within `1e-8` unless an artifact declares a looser solver
  tolerance;
- `w_i >= 0`;
- `w_i <= max_weight + tolerance`;
- `max_weight * number_of_assets >= 1`, otherwise the constraint set is
  infeasible;
- a failed optimizer raises or records a failed/infeasible model status;
- no failed optimizer may silently return Equal Weight under another model name.

## Forecast Metrics

### Regression Errors

`MAE = mean(abs(y - y_hat))`

`RMSE = sqrt(mean((y - y_hat) ** 2))`

`R2 = 1 - SSE / SST`

- These metrics apply only to regression targets.
- A negative OOS R2 is valid evidence that the model is worse than the OOS mean
  benchmark; it must not be hidden.
- The random-walk baseline uses only information available at forecast origin.
- Forecast horizons, feature lags and purging must prevent target overlap from
  entering training features.

Classification AUC, confusion matrices and calibration curves must not be shown
for a regression forecast. Regression metrics must not be used to claim
classification skill.

## Walk-Forward Evidence

- Train windows precede test windows chronologically.
- Test returns are concatenated once into a daily OOS series; fold summary
  metrics are not compounded as if they were daily returns.
- All models use the same test dates, universe policy, max-weight rule and cost
  convention.
- Hyperparameter selection cannot use final OOS outcomes.
- Current constituents create survivorship bias; the result is
  `completed_public_data_current_universe`, not institutional point-in-time
  evidence.

## Uncertainty

QuantVerse uses a paired circular block bootstrap on synchronized model and Equal
Weight OOS daily returns.

- Pairing preserves same-date comparison.
- Block resampling partially preserves short-range serial dependence.
- An active model may pass the Sharpe uncertainty gate only if the lower bound of
  the configured Sharpe-difference confidence interval is greater than zero.
- A confidence interval crossing zero means the improvement is not established.
- The bootstrap is not a White Reality Check, SPA, DSR or full PBO test.

## Random Portfolio Benchmark

Current constrained random weights are generated by:

1. i.i.d. positive uniform raw scores;
2. deterministic projection to the capped simplex.

This method is reproducible and constraint-valid, but it is not uniform over the
feasible capped simplex. Outputs must label
`iid_uniform_raw_scores_projected_to_capped_simplex`. Percentiles are
diagnostic comparisons against this sampling design, not probabilities of
future outperformance.

## Monte Carlo Projection

1. Validate historical daily simple returns are strictly greater than -100%,
   because `log1p(-1)` is undefined even though -100% is a possible terminal
   simple return.
2. Transform selected returns with `log1p`.
3. Fit daily mean and Ledoit-Wolf covariance to complete-case log returns.
4. Draw multivariate normal log returns.
5. Convert each draw with `expm1`.
6. Apply fixed portfolio weights and compound simple portfolio returns.

This is a conditional parametric scenario model. Normal log-return innovations,
constant parameters, fixed weights and no trading frictions are material
limitations. Projection quantiles are not calibrated confidence intervals and
are not investment advice.

## Promotion States

| State | Meaning |
|---|---|
| `promoted` | All declared evidence gates for the specified universe and evidence layer passed |
| `not_promoted` | One or more required gates failed |
| `diagnostic_only` | Output is useful for interpretation but cannot select the final model |
| `blocked` | Required input or validation evidence is absent |
| `rejected` | Mathematical, data, leakage, identity or optimizer validity failed |

The universe and evidence layer must always accompany the state. A proxy-only or
current-universe result is never synonymous with a promoted global USD
institutional master portfolio.

Operational extreme-metric thresholds are review gates, not significance
tests. If `extreme_metric_warning` is anything other than `none`, an active
model cannot pass final selection until the warning has been investigated and
resolved. Empty evidence or a missing eligible Equal Weight benchmark produces
`not_available`; it must never fabricate a default winner.
