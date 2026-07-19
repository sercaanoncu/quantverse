# QuantVerse v2 Full Scientific Red-Team Audit

## 1. Executive Verdict

**Verdict: RESEARCH_READY_WITH_LIMITATIONS.**

QuantVerse v2 is fit to be reviewed as a public-data equity research and
portfolio-analytics project. It is not an institutional point-in-time
backtest, a production trading system, a promoted global USD master portfolio,
or investment advice.

The audit found and repaired all reproducible internal P0 and P1 defects listed
in Section 21. The clean rebuild selected **Equal Weight** as the public-data
research model, not because 1/N is protected, but because no active challenger
cleared the common walk-forward, uncertainty, robustness, cost, downside-risk,
random-benchmark, and metric-review gates. The selected model is still labelled
`not promoted`.

The current result is unusually strong and short:

- 356 realized observations in the final-sample risk table;
- 252 observations across 12 walk-forward test folds;
- OOS Equal Weight CAGR 107.55%;
- OOS Equal Weight Sharpe 2.5936.

These are warning conditions, not marketing claims. Current-universe bias,
missing point-in-time membership, no complete delisting history, only
diagnostic robustness, and incomplete multiple-testing control prevent a
stronger conclusion.

## 2. Audit Scope

The audit traced:

`source -> universe -> identity -> prices -> FX -> returns -> eligibility ->`
`features -> scores -> forecasts -> models -> risk -> walk-forward -> random`
`benchmark -> uncertainty -> robustness -> selection -> weights -> exposure ->`
`PDF/HTML/Excel -> validators`.

It covered the v2 public-data equity path, the legacy global-master candidate
path, and the older ETF/multi-asset pipeline. Decision scopes were not mixed.

## 3. Methodology Sources

All eight local books were inspected and recorded in
`docs/methodology/QUANTVERSE_V2_METHODOLOGY_SOURCE_LEDGER.md`:

1. Isaiah Hull, *Machine Learning for Economics and Finance in TensorFlow 2*.
2. Samit Ahlawat, *Statistical Quantitative Methods in Finance*.
3. Thomas A. Severini, *Introduction to Statistical Methods for Financial Models*.
4. *An Introduction to Statistical Learning*, second edition.
5. Dixon, Halperin and Bilokon, *Machine Learning in Finance*.
6. Stefan Jansen, *Machine Learning for Algorithmic Trading*.
7. Daniel P. Palomar, *Portfolio Optimization*.
8. *Quantitative Economics with Python*.

Primary sources include Markowitz (1952), Sharpe (1994), Ledoit and Wolf
(2004), DeMiguel, Garlappi and Uppal (2009), Lopez de Prado (2016),
Rockafellar and Uryasev (2000), White (2000), and Bailey and Lopez de Prado
(2014). Citations support methods; they do not validate implementation by
themselves.

## 4. Eight-Book Compliance

The complete matrix is
`docs/audit/QUANTVERSE_V2_EIGHT_BOOK_COMPLIANCE_MATRIX.md`.

Material compliance decisions:

- daily simple returns drive portfolio arithmetic;
- log returns are reserved for compatible diagnostics and simulation;
- sample estimates are labelled and uncertainty is not hidden;
- Equal Weight is mandatory as a benchmark but not hard-coded as winner;
- covariance-dependent optimizers use labelled shrinkage where implemented;
- Max Sharpe and Black-Litterman remain diagnostic under current evidence;
- forecasts remain diagnostic even when MAE beats the random-walk comparator;
- current-universe walk-forward evidence is not called institutional PIT evidence.

No book was treated as infallible. Where textbook simplification conflicted
with modern backtest-overfit controls, the more conservative primary-research
rule was used.

## 5. Data Integrity

Clean-run identity:

| Field | Value |
|---|---|
| Run ID | `qv2-2026-07-17-259efc27e54d3d25` |
| Data as of | `2026-07-17` |
| Universe snapshot | `universe-0473f8d204e446a0` |
| Data snapshot | `data-5a98fe44c52ea4402106` |
| Config hash | `config-15c8c9e152aa1e734b86` |
| Input fingerprint | `input-54d788bf05c12cbf05db` |

The current universe contains 890 rows. One hundred assets passed the current
return/history pipeline, 100 were scored, 99 met standard 12-month feature
history, 40 were selected, and the final Equal Weight model contains 40
holdings. Cross-artifact reconciliation passed.

The 665 excluded price-coverage rows and 21 large-return outlier records remain
visible diagnostics. They were not converted to zeros or silently winsorized
using future information.

## 6. Security Identity

Ticker text is not treated as a permanent security identifier. The identity
layer now separates provider-only confidence, known continuity, ticker reuse,
listing-date evidence, and manual-review states.

SPCX has only 23 valid returns in the clean run and is
`diagnostic_short_history`; it cannot enter standard scoring, forecasting,
covariance, or final portfolio inputs. Crypto identity and stable-value assets
are separated from the equity master input path.

Remaining limitation: public provider metadata cannot establish complete
legal-security continuity, historical delistings, predecessor mapping, or
institutional corporate-action reconciliation for all securities.

## 7. Returns And FX

The governing identity is:

`R_usd = (1 + R_local) * (1 + R_fx) - 1`

when FX is quoted as USD value per unit of local currency. Missing FX is not
zero return. Unsupported conversion blocks institutional/global-master
promotion.

Portfolio returns require every non-zero-weight security to have a matching
return column and a complete selected-weight row. Missing observations are not
implicit cash and do not trigger silent weight redistribution.

The v2 final evidence is built from `global_security_simple_returns_usd.csv`.
The legacy/global-master gate remains not promoted where source, rank, FX, or
constraint evidence is insufficient.

## 8. Statistical Methods

The authoritative formulas, units, signs, and invalidation conditions are in
`docs/methodology/QUANTVERSE_V2_METRIC_AND_UNIT_CONTRACT.md`.

Key decisions:

- arithmetic annual return is `mean(r) * 252`;
- CAGR is compounded wealth growth;
- volatility is sample standard deviation times `sqrt(252)`;
- Sharpe uses daily excess returns with an explicit annual risk-free policy;
- Sortino uses lower partial second moment over all observations;
- drawdown is non-positive;
- daily historical VaR/CVaR are negative return-tail measures;
- unsupported square-root-of-time annual VaR/CVaR labels were removed;
- stationarity and normality tests are diagnostic, not proof of predictability.

Normality is rejected for the current returns. Sample, MLE-normal, and EWMA
covariance condition numbers are warnings; they do not block the v2 model
because the optimization path uses labelled Ledoit-Wolf shrinkage.

## 9. Stock Scoring

The composite score was reconstructed component by component. Standard ranking
is limited to securities satisfying the common history contract. Ineligible
rows remain visible but cannot occupy ranks that reduce the selected eligible
count.

Horizon labels now require their stated observations. A 12-month statistic
cannot be computed from a materially shorter sample and retain a 12-month
label. Missing component handling, robust scaling, direction, clipping, and
selection order are deterministic and tested.

The score is a cross-sectional research ranking, not an expected-return
guarantee.

## 10. Forecasting

The ridge forecast path is chronological, purges overlapping target horizons,
uses training-only preprocessing, evaluates the exact 1M/3M/6M/12M targets,
and compares model error with a same-horizon random-walk baseline.

Current mean MAE:

| Horizon | Model MAE | Random-walk MAE |
|---|---:|---:|
| 1M | 0.1462 | 0.1618 |
| 3M | 0.3534 | 0.4238 |
| 6M | 0.5648 | 0.6242 |
| 12M | 1.4000 | 1.5518 |

The diagnostic beats the comparator on these point estimates, but this does
not establish an allocation signal. Confidence labels are explicitly
heuristic; no calibrated predictive interval is claimed. Forecast-driven
portfolios remain diagnostic only.

## 11. Portfolio Mathematics

Every full candidate is long-only, finite, and checked for:

- unique ticker identity;
- no non-zero weight outside the return matrix;
- weight sum equal to one;
- feasible maximum weight;
- explicit solver status;
- no failed optimizer relabelled as another model.

The clean final portfolio has 40 holdings, each weighted 0.025. Weight sum is
1.0; negative weights, dust weights, and 10% cap-bound weights are all zero.

Model status:

| Model | Status | Decision use |
|---|---|---|
| Equal Weight | benchmark only | final public-data research model |
| Inverse Volatility | actually run | active candidate |
| GMV | actually run | active candidate |
| HRP | actually run | active defensive candidate |
| Risk Parity | actually run | active defensive candidate |
| Min CVaR | actually run | active tail-risk candidate |
| Max Sharpe | diagnostic only | expected-return fragility |
| Black-Litterman | diagnostic only | priors/views not institutional |
| Policy Constrained | diagnostic only | extreme metrics/current evidence |
| Forecast Enhanced | diagnostic only | forecast not promotable |
| ML/Ensemble Forecast | diagnostic only | no allocation evidence |
| Random Portfolios | benchmark distribution | never selectable |

## 12. Risk

Final full-sample Equal Weight metrics:

| Metric | Value | Interpretation |
|---|---:|---|
| Observations | 356 | short sample |
| Arithmetic annual return | 69.48% | realized annualized estimate |
| CAGR | 94.56% | realized compounded estimate |
| Volatility | 23.90% | annualized |
| Sharpe | 2.9072 | 0% labelled research RF assumption |
| Sortino | 4.6334 | LPM2 convention |
| Calmar | 4.6235 | annual return / drawdown magnitude |
| Max drawdown | -20.45% | realized peak-to-trough |
| Daily VaR 95 | -1.9633% | historical 5% quantile |
| Daily CVaR 95 | -3.1724% | historical tail mean |
| Total return | 156.06% | over the observed sample |

The annual return and CAGR are flagged
`high_*_short_sample_review_required`. They are not forecast targets and do not
support an outperformance claim.

## 13. Walk-Forward

The corrected walk-forward engine:

- uses chronological train/test windows;
- recomputes scores, forecasts, covariance, and weights from training data;
- concatenates each OOS daily return once;
- charges gross traded-notional turnover costs;
- uses common OOS dates for paired comparisons;
- records 12 folds and 252 OOS observations.

The engine passes synthetic no-look-ahead tests. The universe itself is based
on current constituents, so survivorship/current-membership bias remains. The
result is `completed_public_data_current_universe`, not institutional PIT.

## 14. Model Selection

Selection first filters model status, solver constraints, downside-risk limits,
costs, random benchmark, forecast status, robustness, uncertainty, and metric
review warnings. Only then does it rank eligible models by OOS Sharpe.

All active paired circular-block-bootstrap Sharpe-difference confidence
intervals cross zero. Examples:

- Inverse Volatility: `[-0.2951, 0.3922]`;
- Risk Parity: `[-0.4126, 0.4897]`;
- HRP: `[-0.7113, 0.3966]`.

Inverse Volatility has the highest active OOS Sharpe, 2.6706, versus Equal
Weight 2.5936, but its improvement is not statistically established and it has
an extreme-metric review warning. Equal Weight therefore remains the
defensible benchmark/final research model.

If the selection table is empty or a valid Equal Weight benchmark is missing,
the result is now `not_available`; no model is fabricated.

## 15. Robustness

The bounded sensitivity grid evaluated 48 of 216 feasible configurations. Equal
Weight was the dominant model in 100% of sampled scenarios. This is
`diagnostic_configuration_stability_only`.

It does not rerun nested chronological model selection for every scenario and
does not evaluate all covariance estimators, score weights, selection
thresholds, or test-window dimensions. It therefore cannot satisfy the active
promotion gate.

Multiple-testing control is also incomplete for ten compared walk-forward
models. No White Reality Check, SPA, DSR, or full PBO estimate is claimed.

## 16. Economic Realism

The exposure layer distinguishes listing country, issuer country, listing
currency, and economic exposure. It does not assert that these concepts are
equivalent.

Sector, industry, issuer-country, and listing-country metadata coverage is
reported as 100% for final holdings, but confidence is provider-derived and
medium. Economic-country coverage is 0%, explicitly blocking an economic
exposure claim.

The backtest does not model market impact, dynamic spread, taxes, borrow,
partial fills, lot sizes, execution latency, custody, or portfolio capacity.

## 17. ML And Data Science

The older downside-risk classifier remains diagnostic. Its ROC AUC is about
0.558 and PR AUC about 0.114 versus a base event rate near 0.094; it is not a
trading signal.

The v2 return forecasts are regression diagnostics and use MAE/RMSE/R2, not
classification metrics. No LSTM, Transformer, reinforcement-learning, or LLM
allocation engine is presented as production-ready.

Preprocessing, target construction, random-walk comparison, feature timing, and
chronological splits are regression-tested. Negative or weak OOS skill must
remain visible.

## 18. Software Engineering

Material controls added or strengthened:

- shared portfolio-weight contract;
- optimizer failure status and previous-weight carry-forward audit;
- deterministic run fingerprints;
- schema and cross-artifact reconciliation;
- strict v2/legacy artifact separation;
- explicit unavailable-model behavior;
- expanded adversarial tests;
- independent numerical reference implementation.

The current suite has 306 passing tests. Black, Ruff, compileall, artifact
validation, and `git diff --check` are final release gates. Pyright is not
configured and is not falsely reported as passed.

## 19. Reproducibility

Run identity separates deterministic input fingerprints from execution
metadata. Core artifacts carry run ID, as-of date, universe/data snapshot IDs,
config hash, and input fingerprint. The validator rejects mixed-run core
artifacts.

Random portfolio, bootstrap, and simulation paths use explicit seeds. Output
files are generated and excluded from the source commit.

The independent reference validator recalculated 21 representative return,
portfolio, risk, and weight identities without calling the production metric
functions. All 21 checks passed.

## 20. Reporting

The rebuilt package contains:

- 27 chart images;
- chart-led scientific audit PDF and presentation;
- v2 research PDF and HTML;
- v2 research Excel workbook;
- explainable Excel workbook with full weights and blockers.

Visual data contracts enforce an equity curve starting at 1.0, non-positive
drawdown, risk on the x-axis and return on the y-axis, non-degenerate random
benchmarks, same-horizon forecast/error comparison, and exposure sums of one.

If a final-model decision is absent, visual/exposure builders no longer assume
Equal Weight.

## 21. Findings By P0/P1/P2/P3

The table counts internal correctness findings from the baseline commit
`492d8d5`. External institutional-data blockers are listed separately.

| Severity | Found | Fixed | Unresolved |
|---|---:|---:|---:|
| P0 - core result invalidation | 12 | 12 | 0 |
| P1 - material interpretation | 15 | 15 | 0 |
| P2 - robustness/quality | 18 | 12 | 6 |
| P3 - engineering/presentation | 8 | 6 | 2 |

P0 repairs covered missing-return arithmetic, FX/stablecoin master inputs,
security/price identity, feature eligibility/ranking, forecast timing,
walk-forward OOS construction, same-protocol random benchmarks, optimizer
fallbacks, Min CVaR formulation, simulation return support, and risk formulas.

P1 repairs covered Equal Weight self-comparison, model-selection thresholds and
uncertainty, metric-warning gates, absent-benchmark behavior, visual/model
fallbacks, v2/legacy weight mixing, robustness labels, covariance labels,
Black-Litterman prerequisites, risk-free labels, run identity, mixed artifacts,
stress semantics, VaR horizon semantics, and projection horizon/missingness.

The six unresolved P2 items are:

1. point-in-time membership and survivorship;
2. official dated market-cap ranks/exact top-100 evidence;
3. complete delisting/corporate-action history;
4. nested OOS sensitivity across all policy dimensions;
5. multiple-testing control across the model search;
6. only 252 OOS observations and extreme point estimates.

The two unresolved P3 items are no configured static type checker and no fully
transactional/atomic end-to-end artifact publication layer.

Generated audit severity also reports 43 open evidence issues: 12 critical, 11
high, and 20 medium. These are scoped blockers or warnings, not 43 unresolved
internal code bugs. Twenty-one block a specific promotion decision: 19
institutional/legacy-global-master blockers and 2 active-challenger blockers.
None blocks the honestly scoped v2 public-data research model.

## 22. Fixes Implemented

Representative repairs:

- missing non-zero portfolio weights now fail;
- no zero-filling of missing weighted returns;
- security identity/history and feature eligibility are enforced;
- crypto mappings and stable-value assets are gated;
- covariance, LP CVaR, HRP, risk parity, GMV, and optimizer statuses are explicit;
- expected-return models remain diagnostic where evidence is weak;
- walk-forward returns are genuine concatenated net OOS daily series;
- uncertainty uses paired circular block bootstrap;
- model selection requires a positive Sharpe-difference lower confidence bound;
- all metric warnings block active model selection pending review;
- Monte Carlo uses log-space wealth with valid return support;
- historical VaR/CVaR signs and horizons are explicit;
- legacy tearsheet Sharpe, Sortino, alpha, and benchmark overlap were corrected;
- visual/report builders cannot fabricate final models;
- validator scope separates v2 research, legacy candidate, and institutional promotion.

## 23. Remaining Limitations

Institutional/global-master promotion remains blocked by:

- no official exact top-100 evidence for supported sleeves;
- 1,635 market-cap/rank blocker records;
- no institutional point-in-time membership/delisting database;
- incomplete corporate-action/security-master evidence;
- Black-Litterman prior evidence unavailable;
- economic-country exposure unavailable;
- public-provider identity confidence;
- simplified transaction costs and no execution/capacity model.

The legacy global-master candidate also fails its region constraint and remains
`not promoted`. It does not override the v2 model.

## 24. Merge-Readiness Verdict

**RESEARCH_READY_WITH_LIMITATIONS**

Rationale:

- zero unresolved internal P0;
- zero unresolved internal P1;
- no known arithmetic or temporal leakage defect in the corrected v2 path;
- complete selected-weight return policy enforced;
- full pipelines pass;
- independent reference math passes;
- active-model uncertainty and metric warnings prevent false promotion;
- external PIT, rank, delisting, and market-practice limitations remain explicit.

This verdict permits a public-data research merge after final formatting,
linting, artifact QA, and source-only commit checks. It does not permit claims
of institutional validity, production readiness, exact top-100 support,
guaranteed alpha, or investment suitability.
