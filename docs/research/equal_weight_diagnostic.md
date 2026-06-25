# Equal Weight Diagnostic

This note explains why Equal Weight is difficult to beat and how the new
return-seeking challenger layer changes the interpretation. The analysis is
research-grade only and is not investment advice.

## Protocol

- Benchmark: Equal Weight.
- Asset universe: the same investable universe used by the main QuantVerse
  pipeline after data-quality filtering.
- Out-of-sample method: walk-forward evaluation.
- Train window: 504 trading days.
- Rebalance frequency: 63 trading days.
- Transaction costs: 10 bps proportional plus 5 bps spread in the base run.
- Primary metric: out-of-sample CAGR.
- Secondary metrics: Sharpe, Sortino, Calmar, max drawdown, volatility,
  turnover, transaction-cost drag, hit rate by rebalance period, rolling 1Y and
  3Y relative performance.

The machine-readable diagnostic table is written to
`data/processed/equal_weight_diagnostic.csv`.

## Current Evidence

In the final challenger run, Equal Weight produced:

- CAGR: 18.23%.
- Sharpe: 0.79.
- Volatility: 18.77%.
- Max drawdown: -31.42%.
- Total turnover: 2.96.
- Annualized transaction-cost drag: 0.06%.

The strongest annual-return challenger was Asset-Class Momentum Rotation:

- CAGR: 35.27%.
- Sharpe: 0.95.
- Volatility: 33.83%.
- Max drawdown: -37.95%.
- Total turnover: 15.58.
- Annualized transaction-cost drag: 0.34%.
- Rebalance-period hit rate versus Equal Weight: 57.14%.
- Bootstrap CAGR-difference 5%-95% interval versus Equal Weight: -0.25% to
  40.70%.
- Bootstrap Sharpe-difference interval: -0.18 to 0.44.

Therefore, Asset-Class Momentum Rotation is the highest-CAGR research candidate
in the current evidence layer, but not a full replacement for Equal Weight as
the broad project champion.

## Diagnostic Answers

### 1. Is Equal Weight winning because of broad diversification?

Partly yes. Equal Weight spreads capital across every surviving investable asset
without estimating expected returns. This matters because expected returns are
statistically noisy. A diversified allocation can avoid severe estimator error,
single-theme concentration and excessive turnover.

### 2. Is Equal Weight winning because expected return estimates are too noisy?

For several optimized models, yes. Shrunk Max Sharpe Nested generated only 3.29%
CAGR and 0.07 Sharpe, despite using nested shrinkage selection. That result is a
direct warning that expected-return estimation remains unstable in this sample.

### 3. Are optimized models over-concentrating in defensive assets?

Some risk-focused models do. Risk-Managed Equal Weight reduced volatility to
14.56% and drawdown to -27.12%, but CAGR fell to 13.29%. This is not a failure if
the objective is risk control, but it is not an annual-return victory.

### 4. Are transaction costs hurting active models?

Costs matter but do not explain all results. Asset-Class Momentum Rotation kept
its CAGR advantage at 0, 5, 10, 25 and 50 bps cost levels. At 25 bps, it still
produced 34.97% CAGR versus 18.19% for Equal Weight. At 50 bps, it produced
34.22% CAGR versus 18.06% for Equal Weight. Dual Momentum also kept a CAGR
advantage under costs, but with worse drawdown and weaker Sharpe evidence.

### 5. Are rebalance windows too short or too long?

This sprint did not optimize the rebalance frequency. It intentionally held the
main project setting fixed at 63 trading days so all models used the same
calendar. Changing the rebalance interval would be a separate hyperparameter
study and must be selected inside training/validation windows, not after seeing
the final out-of-sample result.

### 6. Is crypto, commodity or equity exposure driving Equal Weight CAGR?

Growth-sensitive assets contribute materially to the result. Equal Weight
benefits from broad participation in equity, commodity and crypto exposure
without concentrating too heavily in one class. Asset-Class Momentum Rotation
earned its higher CAGR by rotating more aggressively toward asset classes with
strong trailing momentum, including crypto-heavy periods after the 2020 crash.

### 7. Does Equal Weight win in all regimes or only certain regimes?

Equal Weight does not win in every rolling window, but it is more stable across
named stress periods. Asset-Class Momentum Rotation beat Equal Weight in only 1
of 4 named subperiods:

- Pre-COVID: challenger CAGR 15.80% versus Equal Weight 29.00%.
- COVID crash: challenger CAGR -58.23% versus Equal Weight -55.90%.
- 2022 inflation/rate shock: challenger CAGR -19.89% versus Equal Weight
  -15.84%.
- Recent period: challenger CAGR 23.50% versus Equal Weight 15.74%.

This is why the challenger is not promoted to broad champion status.

### 8. Is Equal Weight winning on CAGR but losing on drawdown/risk?

No longer on CAGR. Asset-Class Momentum Rotation has higher OOS CAGR and higher
Sharpe in the base run. However, it also has a worse maximum drawdown:
-37.95% versus -31.42%. The return gain comes with a real drawdown penalty.

### 9. Does HRP reduce risk at the cost of return?

The existing HRP layer remains a risk-focused candidate rather than a pure
return champion. HRP-style diversification can be defensible when the objective
is concentration control or drawdown behavior. It is not automatically expected
to maximize CAGR.

### 10. Is Max Sharpe unstable because expected return estimation is weak?

Yes. Even after using nested shrinkage, Shrunk Max Sharpe Nested had weak
out-of-sample evidence. This supports the existing project stance: Max Sharpe is
diagnostic unless it proves itself under the same walk-forward protocol.

## Conclusion

Equal Weight is no longer the highest-CAGR model in this challenger layer.
Asset-Class Momentum Rotation has the highest point-estimate annual return
without using future data and survives the base, 25 bps and 50 bps cost checks.
However, Equal Weight remains the benchmark and broad default champion because
the challenger has higher drawdown, higher turnover, weaker subperiod
consistency and bootstrap intervals that cross zero.
