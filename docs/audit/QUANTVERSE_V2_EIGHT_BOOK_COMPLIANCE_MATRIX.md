# QuantVerse v2 Eight-Book Compliance Matrix

## Interpretation

`Implemented` means the code and deterministic tests support the stated rule.
`Partial` means the current method is scientifically useful but does not satisfy
the complete institutional requirement. `Not implemented` is not hidden by
reporting language.

Book columns use `Direct`, `Supporting` or `Not primary`. IDs and complete
bibliographic traceability are defined in
`docs/methodology/QUANTVERSE_V2_METHODOLOGY_SOURCE_LEDGER.md`.

## Required Concept Compliance Matrix

| Concept | Implementation location | Book 1 support | Book 2 support | Book 3 support | Book 4 support | Book 5 support | Book 6 support | Book 7 support | Book 8 support | Academic support | Current implementation | Correct? | Theoretical issue | Practical issue | Required fix | Validation method | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Simple returns | returns pipeline; numerical integrity | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | P1 | weighted portfolio arithmetic | Yes | linear only for one-period returns | adjusted prices/identity required | retain no-zero-fill contract | reference recomputation | Implemented |
| Log returns | statistical diagnostics; Monte Carlo | Supporting | Direct | Direct | Supporting | Direct | Direct | Supporting | Supporting | standard identity | diagnostics and `log1p` simulation | Yes | cannot aggregate with simple-weight formula | undefined at -100% | reject log-model input <= -100% | unit tests and reference math | Implemented |
| Annualization | constants and risk evaluator | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | P2 | 252-day arithmetic return/volatility | Yes | sampling error remains | frequency must be daily | expose factor and units | annualization tests | Implemented |
| CAGR | risk evaluator | Supporting | Direct | Direct | Supporting | Supporting | Direct | Direct | Supporting | P1 | compounded wealth annualization | Yes | path/sample dependent | impossible return can break compounding | preserve separate CAGR label | independent recomputation | Implemented |
| Volatility | risk and covariance modules | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | P1, P3 | sample daily SD times sqrt(252) | Yes | unstable in short samples | asynchronous/missing data | show estimator/sample | tests and validator | Implemented |
| Downside volatility | risk module | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | lower-partial-moment literature | LPM2 around daily hurdle | Yes | target choice affects value | 0% RF simplification | label MAR/RF | formula test | Implemented |
| Sharpe | risk/model selection | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | P2, P8 | daily excess mean / SD annualized | Yes | non-normality and selection bias | 0% RF, short OOS | paired uncertainty; no alpha claim | reference math/bootstrap tests | Partial |
| Sortino | risk module | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | downside-risk literature | annualized excess / LPM downside | Yes | MAR convention matters | unstable when downside near zero | expose convention | deterministic formula tests | Implemented |
| Calmar | risk module | Supporting | Supporting | Supporting | Not primary | Supporting | Direct | Direct | Supporting | practitioner risk literature | CAGR / abs(max drawdown) | Yes | sample/path dependent | zero drawdown edge | return 0/NA policy disclosed | reference math | Implemented |
| VaR | risk module | Supporting | Direct | Direct | Not primary | Direct | Direct | Direct | Supporting | risk literature | historical 5% return quantile | Yes | not coherent in general | sparse tail | keep negative-return sign | quantile test | Implemented |
| CVaR / ES | risk and CVaR optimizer | Supporting | Direct | Direct | Not primary | Direct | Direct | Direct | Supporting | P6 | historical tail mean and LP optimizer | Yes | sample-sensitive | few tail observations | retain stress/uncertainty caveat | LP and tail tests | Implemented |
| Max drawdown | risk/visual modules | Supporting | Direct | Direct | Not primary | Direct | Direct | Direct | Supporting | practitioner literature | wealth/running peak - 1 | Yes | path-dependent | short history | chart must remain <=0 | visual/reference tests | Implemented |
| Covariance | league/statistics | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | P3 | complete-case Ledoit-Wolf in optimizers | Yes | estimation error | high dimension/short history | retain shrinkage labels | symmetry/PSD/condition tests | Implemented |
| Correlation | clustering/HRP | Supporting | Direct | Direct | Supporting | Direct | Direct | Direct | Supporting | P5 | complete-case correlation; constants singleton | Yes | unstable clusters | constant/missing series | keep no fabricated correlations | synthetic tests | Implemented |
| Diversification | league/exposure | Supporting | Supporting | Supporting | Supporting | Direct | Direct | Direct | Supporting | P1, P4, P5 | holdings, HHI/effective N, exposures | Partial | count is not economic diversification | US/currency concentration | retain exposure warnings | weight/exposure reconciliation | Partial |
| Expected returns | league/forecast diagnostics | Direct | Direct | Direct | Direct | Direct | Direct | Direct | Direct | P1, P4 | historical/forecast estimates only in diagnostic models | Partial | severe estimation error | short/current-winner sample | no promotable expected-return optimizer | OOS/random/bootstrap gates | Diagnostic |
| Random walk | forecast validation | Direct | Supporting | Direct | Direct | Direct | Direct | Not primary | Direct | time-series baseline literature | same-horizon baseline | Yes | baseline specification matters | overlapping targets | preserve purging/comparable loss | forecast tests | Implemented |
| Forecasting | forecast engine | Direct | Direct | Direct | Direct | Direct | Direct | Supporting | Direct | forecasting literature | purged chronological Ridge | Partial | non-stationarity | only 1M-12M public history | diagnostic only | leakage/scale/random-walk tests | Partial |
| Regression | forecast engine | Direct | Direct | Direct | Direct | Direct | Direct | Not primary | Direct | standard regression | regularized Ridge | Yes for diagnostic | linearity | target overlap/history | keep OOS diagnostics | synthetic temporal tests | Implemented |
| Regularization | forecast/covariance | Direct | Supporting | Supporting | Direct | Direct | Direct | Direct | Supporting | P3 | Ridge and Ledoit-Wolf | Yes | tuning uncertainty | no nested tuning | fixed/declared parameters | determinism tests | Partial |
| Portfolio optimization | league | Supporting | Supporting | Supporting | Supporting | Direct | Direct | Direct | Supporting | P1 | explicit objectives and constraints | Yes | optimizer fragility | solver/cap feasibility | fail visibly | optimizer tests | Implemented |
| GMV | league | Not primary | Supporting | Supporting | Not primary | Supporting | Direct | Direct | Supporting | P1, P3 | minimize `w' Sigma w` | Yes | covariance error | cap binds | surface convergence | objective/constraint tests | Implemented |
| Max Sharpe | league | Supporting | Supporting | Supporting | Not primary | Supporting | Direct | Direct | Supporting | P1, P2, P4 | nonlinear diagnostic | Yes as diagnostic | expected-return error | extreme/concentrated output | never promote currently | status/gate tests | Diagnostic |
| CVaR optimization | league/optimization | Not primary | Supporting | Supporting | Not primary | Supporting | Direct | Direct | Supporting | P6 | historical-scenario LP | Yes | tail sampling error | limited scenarios | keep candidate status | LP/reference tests | Implemented |
| HRP | hierarchy/league | Not primary | Not primary | Supporting | Supporting | Direct | Direct | Direct | Supporting | P5 | correlation distance/linkage/bisection | Yes | no universal optimality | cluster instability/cap post-process | same OOS gates | hierarchy/constraint tests | Implemented |
| Risk Parity | league | Not primary | Supporting | Supporting | Not primary | Supporting | Direct | Direct | Supporting | risk-budget literature | equal-risk contribution solver | Yes | covariance dependent | convergence/tolerance | expose status | contribution tests | Implemented |
| Black-Litterman | BL module/league | Not primary | Supporting | Supporting | Not primary | Supporting | Direct | Direct | Supporting | original BL literature | current-cap prior diagnostic | Partial | prior/view uncertainty | no PIT caps/defensible views | keep diagnostic only | prerequisite/status tests | Blocked for promotion |
| Equal Weight benchmark | league/model selection | Not primary | Supporting | Supporting | Supporting | Supporting | Direct | Direct | Supporting | P4 | same-protocol 1/N benchmark | Yes | not theoretically optimal in every state | current-universe bias | no self-win comparison | benchmark policy tests | Implemented |
| Transaction costs | walk-forward | Supporting | Supporting | Supporting | Not primary | Direct | Direct | Direct | Supporting | market-friction literature | gross L1 traded notional times bps | Yes as simplification | linear model only | no spread/impact/tax | label convention | turnover/cost tests | Partial |
| Turnover | walk-forward/robustness | Supporting | Supporting | Supporting | Not primary | Direct | Direct | Direct | Supporting | portfolio literature | sum absolute weight changes | Yes if labelled | conventions differ | initial buy and both legs | retain gross-notional name | synthetic transition tests | Implemented |
| Walk-forward testing | walk-forward | Direct | Supporting | Supporting | Direct | Direct | Direct | Supporting | Direct | P7, P8 | chronological non-overlap, net returns | Yes for current-universe research | survivorship remains | 252 OOS days | require PIT for institutional claim | leakage/date tests | Partial |
| Random portfolios | model selection/walk-forward | Supporting | Supporting | Supporting | Supporting | Supporting | Direct | Direct | Direct | simulation literature | capped-simplex projected raw scores | Partial | sampler not uniform | seed/sample sensitivity | disclose sampling design | reproducibility/nondegeneracy tests | Diagnostic |
| Model selection | model-selection module | Direct | Direct | Supporting | Direct | Direct | Direct | Direct | Direct | P7, P8 | hard gates then OOS Sharpe rank | Partial | winner's curse/multiple testing | 13 compared models | no active promotion absent stronger controls | gate/CI tests | Partial |
| Robustness | robustness module | Supporting | Supporting | Supporting | Direct | Direct | Direct | Direct | Direct | P7 | current-sample bounded grid | Correctly labelled diagnostic | not nested OOS | 48 of 216 scenarios | implement nested OOS later | grid coverage tests | Diagnostic |
| Statistical uncertainty | walk-forward bootstrap | Direct | Direct | Direct | Direct | Direct | Direct | Supporting | Direct | P7, P8 | paired circular block bootstrap | Partial | block/bootstrap assumptions | 252 paired days | retain CI gate; add DSR/PBO only if justified | synthetic paired tests | Partial |

| Book | Methodology principle | QuantVerse implementation | Evidence | Compliance | Remaining limitation |
|---|---|---|---|---|---|
| Hull, *Machine Learning for Economics and Finance in TensorFlow 2* | Separate prediction tasks, validate out of sample, regularize and benchmark | Chronological Ridge diagnostics, task-appropriate regression metrics, random-walk comparison | forecast engine, validation CSVs, forecast tests | Partial | no calibrated uncertainty; short OOS history; no portfolio-level alpha promotion |
| Ahlawat, *Statistical Quantitative Methods in Finance* | Match statistical method to assumptions and units; expose estimation uncertainty | return/statistical diagnostics, finite checks, normality and stationarity outputs, metric contract | statistical diagnostic outputs and tests | Partial | no comprehensive likelihood-model suite; no claim that tests establish predictability |
| Severini, *Introduction to Statistical Methods for Financial Models* | Distinguish simple and log returns, define covariance and random-walk benchmarks | simple returns for portfolio arithmetic; log returns for diagnostics/simulation; explicit random-walk forecast baseline | return artifacts, metric contract, reference validator | Implemented for current scope | provider/corporate-action and point-in-time limitations remain |
| James et al., *An Introduction to Statistical Learning* | Train/test discipline, regularization, correct regression/classification metrics, honest test error | chronological/purged Ridge; no classification metrics for return regression; negative OOS R2 allowed | forecast validation module and tests | Implemented for diagnostic scope | no nested hyperparameter search; forecast remains diagnostic |
| Dixon, Halperin and Bilokon, *Machine Learning in Finance* | Financial non-stationarity, leakage, temporal validation and governance | walk-forward ordering, leakage audit, run identity, model applicability statuses | walk-forward outputs, run registry and tests | Partial | no regime-complete history, no calibrated uncertainty, no production monitoring |
| Jansen, *Machine Learning for Algorithmic Trading* | Point-in-time data, survivorship awareness, costs, walk-forward and backtest-overfit controls | current-universe limitation labels, 10 bps turnover cost, OOS folds, paired bootstrap | universe warnings, OOS/cost/uncertainty outputs | Partial | point-in-time constituents, delistings, White/SPA/DSR/PBO not implemented |
| Palomar, *Portfolio Optimization* | Explicit objectives/constraints, covariance robustness, HRP/risk parity/CVaR, optimizer diagnostics | 13-model league; long-only capped simplex; Ledoit-Wolf; solver failures surfaced; no false fallback | league/status/risk outputs and optimizer tests | Implemented for public-data research scope | expected-return models remain fragile; no market-impact or robust-optimization uncertainty set |
| *Quantitative Economics with Python* | Reproducible simulation, model assumptions and economically meaningful interpretation | seeded random portfolios, parametric log-return Monte Carlo, explicit assumption labels, deterministic tests | random/projection outputs and tests | Partial | simulations are conditional diagnostics, not calibrated forecasts |

## Cross-Book Rule Matrix

| Rule | Book support | QuantVerse validation rule | Status |
|---|---|---|---|
| Simple returns for portfolio aggregation | Severini; Palomar | weighted simple returns; no missing-as-zero; reject return <= -100% | Implemented |
| Log returns for selected statistical tasks | Severini; Ahlawat | `log1p` only for valid simple returns; labels preserved | Implemented |
| 252-day annualization | Severini; Ahlawat; Palomar | one central daily annualization convention | Implemented |
| Covariance shrinkage | Palomar; Jansen | complete-case Ledoit-Wolf in covariance-sensitive optimizer paths | Implemented |
| Normality is not required for useful risk analysis | Ahlawat; Severini | report rejection; retain drawdown/historical CVaR/stress interpretation | Implemented |
| Stationarity test is not proof of predictability | Severini; Dixon et al. | diagnostic-only status | Implemented |
| Equal Weight is a hard benchmark | Palomar; Jansen | same OOS dates, universe, caps and costs; no automatic winner | Implemented |
| Optimizer failure must be visible | Palomar | failure/infeasible model status; no hidden EW fallback | Implemented |
| Current constituents cannot prove historical investability | Jansen; Dixon et al. | current-universe OOS label and institutional promotion blocker | Implemented as governance; data gap remains |
| Temporal leakage prevention | ISLR; Jansen; Dixon et al. | chronological windows, purged target overlap, latest available features only | Implemented |
| Random-walk forecast benchmark | Severini; Hull; Jansen | model error compared with same-horizon random-walk error | Implemented |
| Costs and turnover | Jansen; Palomar | same 10 bps L1-turnover convention across OOS models | Implemented simplification |
| Multiple-testing caution | Jansen; Dixon et al. | paired bootstrap and diagnostic-only sensitivity | Partial |
| Risk-tail optimization | Palomar | LP Min CVaR plus historical tail reporting | Implemented with sample limitations |
| Simulation assumptions must be disclosed | Hull; Quantitative Economics | seeded, log-return normal, fixed-weight Monte Carlo label | Implemented |

## Non-Compliance That Must Remain Visible

1. Historical point-in-time constituents and delistings are not available.
2. Exact broad global top-100 market-cap ranks are not supported.
3. White Reality Check, SPA, Deflated Sharpe Ratio and full PBO are not
   implemented.
4. Forecast intervals are not calibrated probabilities.
5. Transaction costs omit spreads, impact, taxes and execution latency.
6. No model has institutional approval, monitoring or a live execution audit
   trail.

These limitations prevent a production or institutional-readiness claim, even
when code validation succeeds.
