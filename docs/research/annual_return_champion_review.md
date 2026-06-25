# Annual Return Champion Review

This review summarizes the final result of the return-seeking
champion-challenger layer. The analysis is research-grade only and is not
investment advice.

## 1. Which model has the highest OOS CAGR?

Asset-Class Momentum Rotation has the highest point-estimate out-of-sample CAGR:

- Asset-Class Momentum Rotation CAGR: 35.27%.
- Equal Weight CAGR: 18.24%.
- CAGR difference: 17.03 percentage points.

The rule ranks asset classes using trailing returns known at each rebalance
date, allocates more capital to stronger classes, diversifies inside each class,
uses long-only weights and respects the 25% maximum weight cap.

## 2. Does it beat Equal Weight after costs?

Yes on point-estimate CAGR. Under the implemented cost-sensitivity grid, the
strategy keeps a CAGR advantage at both 25 bps and 50 bps:

- 25 bps Equal Weight CAGR: 18.19%.
- 25 bps Asset-Class Momentum Rotation CAGR: 34.97%.
- 50 bps Equal Weight CAGR: 18.06%.
- 50 bps Asset-Class Momentum Rotation CAGR: 34.22%.

The advantage is not explained away by these transaction-cost assumptions in
this historical sample. This does not prove future superiority because execution
slippage, taxes, market impact and future liquidity regimes are not modeled.

## 3. Does it beat Equal Weight consistently or only in one regime?

It does not beat Equal Weight consistently across all named subperiods. It wins
the recent period but loses the pre-COVID, COVID crash and 2022 inflation/rate
shock subperiods. This is the main reason it is not promoted to broad champion
status.

Rolling evidence is mixed but stronger than the named subperiod count:

- Rolling 1Y CAGR difference is positive in 69.41% of windows.
- Rolling 3Y CAGR difference is positive in 97.47% of windows.

## 4. What is the drawdown penalty?

The drawdown penalty is material:

- Equal Weight max drawdown: -31.42%.
- Asset-Class Momentum Rotation max drawdown: -37.95%.
- Difference: -6.53 percentage points.

The challenger earns higher point-estimate return by accepting more volatility,
more turnover and deeper peak-to-trough loss.

## 5. Is the higher return statistically meaningful or likely noise?

The bootstrap comparison is not strong enough for promotion:

- CAGR difference bootstrap 5%-95% interval: -0.25% to 40.70%.
- Sharpe difference bootstrap 5%-95% interval: -0.18 to 0.49.

Both intervals cross zero. Therefore, the higher point-estimate CAGR is useful
research evidence, but it is not statistically settled enough to call the model
a broad champion.

## 6. Is the model simple enough to defend in interview?

Yes. The rule is explainable:

1. Look backward, never forward.
2. Rank asset classes by trailing performance.
3. Allocate more to stronger asset classes.
4. Diversify within each selected class.
5. Respect long-only and max-weight constraints.
6. Compare against Equal Weight under the same cost and rebalance protocol.

The rule is simpler and more defensible than an LSTM or an unconstrained Max
Sharpe optimizer.

## 7. Is the model robust enough to become the new champion?

No. It is best described as the highest-CAGR research candidate in the current
evidence layer, not as the broad project champion.

The reason is precise:

- It beats Equal Weight on point-estimate OOS CAGR.
- It survives the 25 bps and 50 bps cost checks.
- But its bootstrap CAGR and Sharpe intervals cross zero.
- It wins only 1 of 4 named subperiods.
- It has a deeper drawdown than Equal Weight.
- No-crypto and no-commodity asset-universe sensitivity checks are not yet
  implemented.

## 8. If not, why does Equal Weight remain champion?

Equal Weight remains the benchmark and broad default champion because it is more
stable, lower-turnover, easier to explain and less dependent on a specific
momentum regime. It does not maximize CAGR in this run, but it remains the
strongest broad reference allocation until a challenger clears all promotion
gates.

## 9. What exact rule makes the challenger defensible?

The defensible rule is:

At each rebalance date, use only the previous 504 trading days. Compute trailing
asset-class momentum from past returns, rank asset classes, allocate the largest
class budget to the highest-ranked class, allocate a smaller budget to the
second-ranked class, diversify the residual across remaining classes, diversify
inside each class using inverse volatility, cap each asset at 25%, apply the
result to the next out-of-sample day and subtract transaction costs.

This is not overfit in the narrow walk-forward sense because the model does not
use future returns, future regimes, full-sample covariance, final-period
performance or cherry-picked dates to set weights. It remains exploratory
because the discovered result should be tested on future unseen data.

## Final Decision

Asset-Class Momentum Rotation is the highest-CAGR research candidate in the
current evidence layer. Equal Weight remains the benchmark and broad project
champion until future unseen data and additional sensitivity tests confirm that
the challenger can keep its CAGR advantage without unacceptable drawdown,
regime fragility or statistical uncertainty.
