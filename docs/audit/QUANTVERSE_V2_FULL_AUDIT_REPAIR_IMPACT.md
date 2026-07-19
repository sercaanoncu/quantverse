# QuantVerse v2 Full Audit Repair Impact

## Scope

This document compares the evidence immediately before the full-system
correctness reconstruction with the clean run produced after the repairs.
Differences are not interpreted as performance improvement. They reflect
changes in data snapshot, security-history eligibility, formula contracts,
out-of-sample construction, model status, and selection gates.

## Run Comparison

| Item | Before audit snapshot | After clean rebuild |
|---|---|---|
| Starting source commit | `492d8d5` | working repair set based on `492d8d5` |
| Data as of | 2026-07-17 | 2026-07-17 |
| Universe rows | 890 | 890 |
| Assets with returns | 100 | 100 |
| Standard-history eligible | 99 | 99 |
| Short-history diagnostic | 1 | 1 (`SPCX`) |
| Stocks scored | 100 | 100 |
| Stocks selected | 40 | 40 |
| Final holdings | 40 | 40 |
| Final model | Equal Weight | Equal Weight |
| Weight sum | 1.0 | 1.0 |
| Negative weights | 0 | 0 |
| Walk-forward folds | 12 | 12 |
| OOS observations | 252 | 252 |
| Run ID | `qv2-2026-07-17-12b5fd15701f677a` | `qv2-2026-07-17-259efc27e54d3d25` |

The run ID changed because the corrected input/data fingerprint and generated
evidence changed. Generated time remains execution metadata rather than a
methodology input.

## Final Model Metrics

| Metric | Before audit evidence | After repair | Interpretation |
|---|---:|---:|---|
| Full-sample observations | 356 | 356 | same short common sample |
| Arithmetic annual return | 69.4820% | 69.4820% | unchanged point estimate |
| CAGR | 94.5570% | 94.5570% | unchanged, now explicit warning |
| Volatility | 23.8997% | 23.8997% | unchanged |
| Sharpe | 2.9072 | 2.9072 | unchanged, 0% labelled RF policy |
| Sortino | 4.6334 | 4.6334 | LPM2 contract retained |
| Calmar | 4.6235 | 4.6235 | formula/label explicit |
| Max drawdown | -20.4512% | -20.4512% | unchanged |
| Daily VaR 95 | -1.9633% | -1.9633% | negative return-tail convention |
| Daily CVaR 95 | -3.1724% | -3.1724% | negative tail mean |
| Total return | 156.0567% | 156.0567% | observed sample only |

The major impact is interpretive: the high annual return and CAGR now carry
short-sample review warnings, and any active model with an unresolved metric
warning cannot pass the final selection gate.

## Walk-Forward Comparison

| Model | OOS annual return | OOS volatility | OOS Sharpe | OOS max drawdown | OOS CVaR | Random Sharpe percentile |
|---|---:|---:|---:|---:|---:|---:|
| Equal Weight | 77.5901% | 29.9165% | 2.5936 | -13.2528% | -4.3430% | 0.634 |
| Inverse Volatility | 58.1630% | 21.7789% | 2.6706 | -10.2364% | -3.0827% | 0.797 |
| Risk Parity | 52.5099% | 19.7303% | 2.6614 | -9.1426% | -2.7957% | 0.775 |
| HRP | 47.7804% | 19.4850% | 2.4522 | -8.8692% | -2.8479% | 0.307 |
| GMV | 34.2119% | 15.0115% | 2.2790 | -8.0259% | -1.9693% | 0.058 |
| Min CVaR | 34.1524% | 15.2852% | 2.2343 | -7.9470% | -2.0119% | 0.026 |

Inverse Volatility has the highest active OOS Sharpe, but its paired
Sharpe-difference confidence interval is `[-0.2951, 0.3922]`. The interval
crosses zero. Risk Parity and HRP also fail uncertainty and/or benchmark gates.
No active model replaces Equal Weight.

## Decision-Layer Impact

| Control | Before | After |
|---|---|---|
| Empty model evidence | could return Equal Weight label | returns `not_available` |
| Missing eligible EW benchmark | could select first/highest row | returns `not_available` |
| Extreme metric warning | blocked only if text contained `severe` | every non-`none` warning blocks active selection |
| Visual final-model fallback | silently assumed Equal Weight | explicit decision required |
| Exposure final-model fallback | silently assumed Equal Weight | explicit matching decision/weights required |
| v2 risk weight source | could fall back to legacy master weights | v2 league weights only |
| Robustness | potentially read as promotion evidence | diagnostic configuration sensitivity only |
| Multiple testing | implicit | explicit active-challenger blocker |

## Portfolio And Constraint Impact

The final Equal Weight vector contains 40 holdings at 2.5% each:

- sum: 1.000000;
- negative positions: 0;
- dust positions: 0;
- 10% cap-bound positions: 0;
- non-zero weighted tickers missing from returns: 0.

The legacy global-master candidate remains a separate scope. It fails
`max_region_ok` and is not promoted. No report may reinterpret that legacy
fallback as the v2 public-data model.

## Forecast Impact

The forecast engine now enforces:

- true horizon length;
- chronological, purged training;
- training-only transforms;
- latest eligible feature row;
- same-horizon random-walk comparison;
- no full-sample winsorization;
- diagnostic-only allocation status.

Current model MAE is below random-walk MAE at 1M, 3M, 6M and 12M, but the result
does not pass a portfolio promotion gate and no calibrated forecast interval is
claimed.

## Risk And Simulation Impact

Repairs include:

- common Sharpe/Sortino conventions;
- correct benchmark overlap;
- CAPM intercept annualization for Jensen alpha;
- no unsupported square-root-of-time annual VaR/CVaR;
- log-space parametric simulation with positive wealth;
- rejection of returns at or below -100% for log modeling;
- shared full-weight contract across risk, stress, simulation, attribution,
  rebalancing, dashboard, and backtest modules;
- explicit optimizer failures instead of false successful labels.

The legacy ETF/multi-asset pipeline still completes on real data after these
repairs.

## Audit Output Impact

The scoped audit currently reports:

| Scope | Open evidence issues | Promotion blockers |
|---|---:|---:|
| v2 public-data research model | 11 warnings | 0 |
| active public-data challenger promotion | 2 | 2 |
| legacy global-master candidate | 13 | 2 |
| institutional global-master promotion | 17 | 17 |
| Total | 43 | 21 |

Critical/high institutional issues include unsupported exact top-100 claims,
1,635 market-cap/rank blockers, missing PIT/delisting evidence, unavailable
Black-Litterman priors, and unverified crypto mappings. These do not disappear
because the v2 public-data model runs.

## Artifact Impact

The clean rebuild produced:

- 27 chart images;
- visual scientific audit PDF and presentation;
- explainable Excel workbook;
- v2 research PDF;
- v2 research HTML;
- v2 research Excel workbook;
- 21/21 independent reference-math checks;
- cross-artifact count and run-ID reconciliation.

Generated files remain excluded from the source commit.

## Conclusion

The audit did not improve performance by tuning toward a winner. It tightened
what the project is allowed to conclude. Equal Weight remains the final
public-data research model because the active challengers do not establish a
positive Sharpe improvement after paired uncertainty and robustness controls.

The project is **RESEARCH_READY_WITH_LIMITATIONS**, not institutionally
promoted and not production-ready.
