# Asset-Class Momentum Rotation Forensic Audit

Date: 2026-06-25

## Scope

This audit reviews the Asset-Class Momentum Rotation challenger in QuantVerse. The
goal is not to promote the strategy, but to verify whether its reported
out-of-sample performance is generated without look-ahead bias, metric mismatch,
or unfair benchmark treatment.

## Questions Reviewed

1. Does the strategy use only information available before each traded day?
2. Are rebalance weights applied after the decision point rather than to the same
   information used to estimate the signal?
3. Are Equal Weight and challenger strategies evaluated on the same universe,
   date index, and transaction-cost convention?
4. Is the asset-class map static rather than selected from future winners?
5. Can the reported CAGR and risk metrics be recomputed from saved strategy
   returns?
6. Does the evidence justify replacing Equal Weight as the broad default
   champion?

## Code Path Reviewed

- `src/project/research/challenger.py`
- `src/project/pipeline.py`
- `src/project/reporting/pdf_report.py`
- `data/processed/challenger_returns.csv`
- `data/processed/challenger_weights.csv`
- `data/processed/challenger_cost_robustness.csv`
- `data/processed/model_promotion_gate.csv`
- `data/processed/model_league_summary.csv`

## Walk-Forward Timing Finding

The challenger engine uses a chronological walk-forward loop. For a traded date
at position `i`, the optimizer receives `returns.iloc[max(0, i - train_window):i]`.
That slice ends before the traded row. The realized return used for the strategy
result is then the current row `returns.iloc[i]`.

This timing rule means the model decision is based on historical data available
before the return being scored. No future daily return, future drawdown, future
Sharpe ratio, future covariance, or full-sample ranking is used inside the
allocation decision.

## Asset-Class Momentum Signal Finding

Asset-Class Momentum Rotation computes asset-class scores from trailing class
returns inside the training window. Within selected classes, it uses trailing
volatility from the same historical window for inverse-volatility sizing. The
asset-class map is supplied by the static asset universe metadata. It is not
constructed by looking at future winners.

The implemented rule is therefore an ex ante rule: rank classes using trailing
information, allocate to higher-ranked classes, diversify within classes, and
apply a maximum-weight cap.

## Benchmark Fairness Finding

Equal Weight and all challengers are run through the same research engine:

- same cleaned return matrix,
- same sorted date index,
- same investable tickers,
- same train window,
- same rebalance frequency,
- same transaction-cost convention,
- same metric calculation class,
- same bootstrap and subperiod comparison layer.

Missing observations are handled before the strategy league by applying the same
cleaned return matrix to every strategy. This does not give Asset-Class Momentum
a separate data advantage over Equal Weight.

## Metric Recompute Finding

The pipeline writes
`data/processed/asset_class_momentum_metric_recompute_check.csv`. This file
recomputes Asset-Class Momentum Rotation metrics directly from
`challenger_returns.csv` using the same `PerformanceMetrics` implementation used
by the summary tables.

The expected forensic result is that every row has `Matches=True`. If any row
does not match, the strategy must not be promoted until the mismatch is
explained and fixed.

## Weight Audit Finding

The pipeline writes `data/processed/asset_class_momentum_weight_audit.csv`. This
file records daily Asset-Class Momentum Rotation weight diagnostics:

- weight sum,
- minimum and maximum weight,
- long-only check,
- sum-to-one check,
- rebalance-date cap check,
- top ticker and top asset class by weight.

The maximum-weight cap is evaluated on rebalance dates. Between rebalances,
weights can drift mechanically because assets earn different returns. That drift
is expected in a realistic portfolio accounting process and is not treated as a
new signal.

## Promotion Gate Finding

No look-ahead or metric mismatch was found in the reviewed code path. However,
absence of leakage is not sufficient to make Asset-Class Momentum Rotation the
broad default champion.

The model remains a high-return annual-return challenger or research candidate
because broad promotion would require stronger evidence than currently
implemented:

- 25 bps and 50 bps cost robustness,
- bootstrap evidence that does not merely reflect noise,
- acceptable drawdown penalty,
- subperiod and rolling consistency,
- asset-universe sensitivity such as no-crypto and no-commodity checks,
- future unseen validation beyond the current historical sample.

Because no-crypto and no-commodity sensitivity checks are not yet implemented,
and because bootstrap/subperiod/drawdown gates remain conservative, Equal Weight
remains the Broad Default Champion.

## Conclusion

The forensic audit did not identify look-ahead bias, off-by-one timing advantage,
metric recomputation mismatch, or unfair benchmark treatment for Asset-Class
Momentum Rotation. The correct interpretation is still conservative:

- Equal Weight remains the broad default benchmark/champion.
- Asset-Class Momentum Rotation may be highlighted as the annual-return
  challenger if it clears the implemented cost and bootstrap gates.
- Asset-Class Momentum Rotation should not be described as a guaranteed best
  portfolio, production trading model, or investment recommendation.
