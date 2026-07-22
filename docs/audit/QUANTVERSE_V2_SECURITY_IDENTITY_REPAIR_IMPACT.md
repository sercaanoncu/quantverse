# QuantVerse v2 Security Identity Repair Impact

## Executive Decision

The repair materially changed the admissible research evidence. The previous
public-data result selected HRP from 26 scored and selected securities. The
repaired run scores 100 equity securities, selects 40 standard-history-eligible
candidates, excludes SPCX from standard scoring, and selects Equal Weight as the
final public-data research model.

This is not evidence that Equal Weight will outperform in the future. It is
evidence that the previous HRP decision was not stable to correction of a
security-master row-resolution bug that had suppressed 74 valid equity return
series. Institutional/global master promotion remains `not_promoted`.

## Root Cause

The universe intentionally contains overlapping rows for some tickers: excluded
proxy-documentation rows and included investable market-cap-enriched rows. The
pre-repair pipeline used the first ticker row in several downstream stages. For
NVDA, AAPL and many peers, the excluded proxy row appeared first, so valid
long-history securities were treated as non-investable during USD normalization
and could disappear again during scoring or metadata joins.

The repair introduces one deterministic canonical security-master rule and uses
it consistently in returns, scoring, portfolio metadata, exposure metadata and
report metadata. The source universe is not deleted or rewritten.

## Before And After Counts

| Evidence item | Before repair | After repair | Interpretation |
| --- | ---: | ---: | --- |
| Equity rows scored | 26 | 100 | 74 valid equity series are no longer suppressed by an excluded proxy row. |
| Standard selected candidates | 26 | 40 | The configured selection cap is now reached from the valid standard-history universe. |
| Forecast tickers | 26 | 40 | Every selected forecast-eligible ticker has forecast output. |
| Forecast rows | 104 | 160 | Four diagnostic horizons per selected ticker. |
| Final model holdings | 26 | 40 | Equal Weight uses every current selected candidate. |
| Latest walk-forward selected count | Previously not reconciled in this snapshot | 20 | Matches the separately configured fold-level cap. |
| Cross-artifact reconciliation | Not available | Passed, 11/11 relationships | Counts and run identity now agree. |
| Core run IDs | Not available | One | `qv2-2026-07-21-4453b1fd66455d43` |

The current after-repair selected securities have 358 to 1,391 valid returns; the
median is 1,391. SNDK is the shortest standard-selected history at 358 valid returns,
which still exceeds the 252-observation requirement.

## Selected-Set Change At The Initial Repair Snapshot

Fourteen prior selected tickers remain selected. The following prior selections
leave the standard selected set:

`ANET, APH, BABA, BHP, ETN, GLW, NVO, SAP, SHEL, SPCX, TM, TSM`

The following enter after the previously suppressed valid equity rows are
restored:

`AAPL, ABBV, AMAT, AMD, AMGN, CAT, CSCO, GOOG, GOOGL, INTC, JNJ, KO, LIN, LLY,
MRK, MS, MU, NEE, PEP, PG, PM, RTX, SNDK, STX, VZ, WDC`

This historical snapshot records the immediate repair impact. The selected set
can change with a later data-as-of date because ranking inputs are recomputed.
The change is a cross-sectional ranking consequence of corrected inputs, not
manual ticker selection.

## SPCX Impact

| Check | Result |
| --- | --- |
| Verified current listing start | 2026-06-12 |
| Observed provider price start | 2026-06-12 |
| First valid return | 2026-06-15 |
| Valid return observations | 25 |
| Observations before listing | 0 |
| Pre-listing contamination | None detected |
| Ticker reuse | Known prior unrelated ETF |
| Standard score | Ineligible |
| Forecast | Ineligible |
| Walk-forward | Ineligible |
| Final model weight | 0 |

SPCX had a pre-repair HRP weight of approximately 1.45%. It is removed from the
standard selection because its 25 valid returns cannot support 12-month features,
not because the current downloaded series contains observed prior-ETF prices.

The first downstream inspection found that the legacy global master allocator
still admitted SPCX after the v2 equity league had excluded it. That cross-layer
leak affected selected-assets metadata, seven candidate-model weight rows, all
10,000 random portfolio rows and the 36-asset correlation matrix. The allocator
now applies the same current-run feature-history gate before clustering,
covariance estimation, optimization or simulation. The current rebuilt master
evidence contains 34 unique active tickers and no SPCX or other short-history ticker in those
input surfaces. Its promotion decision remains `not promoted`.

A subsequent Excel red-team pass found zero-weight SPCX rows in the v2 risk
contribution table. Although zero weight meant no component risk or portfolio
return effect, the risk engine still formed a wider covariance surface and the
rows were visually misleading. Risk contribution and covariance calculations
now operate model by model on active holdings only (`abs(weight) > 1e-12`).
The current risk contribution artifact has 328 active-holding rows, no zero
weights and no SPCX row; the reported portfolio metrics are unchanged.

## Other Identity Results

- Documented known ticker-reuse conflicts: 1, SPCX.
- Unresolved documented ticker-reuse conflicts: 0.
- Current SPCX history contamination: none detected.
- Provider-only, no-known-conflict rows: 764.
- Identity-blocked or manual-review rows in the current generated audit: 0.

`no_known_conflict_provider_only` is not institutional identity proof. It means
the pipeline has no documented conflict override for that ticker. Full reference
data, dated corporate actions and independent vendor reconciliation remain future
requirements.

## Model Decision Impact

| Item | Before repair | After repair |
| --- | --- | --- |
| Final public-data research model | HRP | Equal Weight |
| Institutional/global master promotion | Not promoted | Not promoted |
| Robustness status | Prior snapshot | `diagnostic_configuration_stability_only`; promotion-ineligible |
| Sensitivity result | Prior snapshot | Fragile; GMV is dominant in 26/48 sampled scenarios |
| Equal Weight random Sharpe percentile | Not the final model | 0.629 |

After repair, HRP remains a valid defensive candidate. In the realized full
sample, HRP has lower volatility, drawdown and CVaR and a higher Sharpe than Equal
Weight. In the chronological walk-forward comparison, however:

| Model | OOS annualized return | OOS volatility | OOS Sharpe | OOS max drawdown | OOS CVaR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Equal Weight | 77.54% | 29.92% | 2.5919 | -13.25% | -4.34% |
| HRP | 47.78% | 19.49% | 2.4523 | -8.87% | -2.85% |

HRP's OOS Sharpe difference versus Equal Weight is -0.1396. Its paired block
bootstrap Sharpe-difference interval is [-0.7097, 0.3982], while its annual-return
difference interval is wholly negative at [-0.5202, -0.1049]. Equal Weight
therefore remains the defensible benchmark/final public-data model. HRP is not
rejected as useless; it retains stronger defensive characteristics but does not
clear the active-model promotion gate.

## Risk Metric Comparison

| Metric | Before: HRP on 26-security evidence | After: Equal Weight on 40-security evidence |
| --- | ---: | ---: |
| CAGR | 24.29% | 98.60% |
| Annualized arithmetic return | 22.97% | 71.62% |
| Annualized volatility | 15.59% | 24.22% |
| Sharpe | 1.4735 | 2.9566 |
| Sortino | 2.1825 | 4.6969 |
| Maximum drawdown | -17.43% | -20.41% |
| Daily historical VaR 95% | -1.46% | -1.98% |
| Daily historical CVaR 95% | -2.10% | -3.25% |

These figures are not an apples-to-apples performance uplift experiment because
both the security universe and final model changed. They are disclosed to show
the exact reporting impact, not to claim that the repair generated superior
future return.

The after-repair return and risk values are based on a short, unusually strong
realized public-data sample and carry explicit high-return/extreme-metric review
warnings. They are not forecasts or evidence of repeatable future performance.

## Walk-Forward Calendar Repair

The first rebuilt run correctly failed reconciliation because the walk-forward
engine counted crypto weekend rows in an `equity_only` training window. A
252-row global-union window then contained only about 132 valid US-equity returns,
so no security could meet a 252-valid-observation standard.

The fix does not lower the history threshold. For `equity_only`, the engine now:

1. resolves the canonical investable equity scope;
2. removes dates where every scoped equity is missing;
3. applies the 252-valid-return feature rule inside each chronological fold.

The final run completes 12 folds and passes leakage and count reconciliation.

## Final Integrity Status

- Security identity audit: passed with provider-coverage limitations.
- SPCX pre-listing contamination check: passed.
- Feature-history sufficiency: passed.
- Short-history silent promotion check: passed.
- Short-history portfolio-input leakage check: passed.
- Ticker-reuse warning portfolio-input check: passed.
- Selected/forecast/holding count reconciliation: passed.
- Core generated-artifact run-ID consistency: passed.
- Numerical integrity: passed.
- Visual analytics validation: passed.
- QuantVerse v2 artifact validator: passed.
- PDF identity-table render QA: passed after bounded column wrapping.
- Excel and publication-package validation: passed; generated workbooks remain
  local, untracked evidence.

The result remains public-data, current-universe research. It is not an
institutional point-in-time backtest, a promoted global USD master portfolio or
investment advice.
