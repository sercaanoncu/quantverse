# QuantVerse v2 Full-System Architecture Audit

## Executive Architecture Verdict

QuantVerse v2 is a research pipeline, not a production trading platform. Its
defensible architecture is:

`source evidence -> security identity -> USD returns -> statistical diagnostics
-> history-eligible scoring -> diagnostic forecasts -> constrained portfolio
league -> risk -> walk-forward OOS evidence -> uncertainty and benchmark gates
-> final public-data research decision -> reports`

The architecture is scientifically coherent only when every downstream artifact
shares one run identity and no downstream stage reuses stale output. Current
public-data evidence remains constrained by current-universe survivorship,
delisting/corporate-action incompleteness, a limited US equity investable set,
provider dependence and simplified implementation costs.

## Stage-Level Data Lineage Matrix

| Stage | Input artifacts | Output artifacts | Function / module | Formula / transformation | Frequency | Unit | As-of convention | Missing-data treatment | Run-ID behavior | Validation | Known limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Source data | sourced/manual universe CSVs and provider metadata | source validation reports | universe validation/build scripts | schema, source and claim classification | current snapshot | identifiers and metadata | explicit source/as-of fields | missing source/rank becomes blocker | initializes run fingerprint inputs | source schema and exact/proxy checks | not institutional reference data |
| Universe | source universe rows | `current_global_equity_universe.csv` | `build_current_global_universe.py` | canonical concat plus explicit investable/signal flags | current snapshot | one row per sleeve/security role | run data-as-of date | incomplete rows remain proxy/blocked | contributes universe snapshot hash | eligibility and stable-value checks | cross-sleeve signal-only overlap is intentional |
| Security identity | canonical universe and manual overrides | identity/history audits | `security_identity.py` | canonical identity resolution and listing-date gate | event/current metadata | identifiers and dates | verified listing history where available | uncertain continuity blocks eligibility | run metadata attached | ticker-reuse and pre-listing tests | no complete institutional security master |
| Price data | validated `price_ticker` set | adjusted price matrix and coverage | `build_global_returns_matrix.py` | provider adjusted close ingestion | daily | local-currency price | through `data_as_of_date` | missing series excluded and reported | run manifest created before downstream writes | coverage, outlier and identity checks | provider adjustment semantics and delistings limited |
| FX normalization | local prices/returns and FX map | USD simple/log returns and FX report | `global_returns.py` | `(1+r_local)*(1+r_fx)-1`, with quote inversion when required | daily | USD decimal return | same or prior available market date under declared alignment | missing required FX blocks asset | same run ID | quote direction/inversion tests | current v2 investable set is USD; broader sleeves remain governance-limited |
| Return matrix | adjusted prices, FX and identity eligibility | simple/log USD matrices | returns builder | `pct_change`; `log1p(simple)` | daily | decimal return | date index through run as-of | never filled with zero | registered artifacts | impossible-return and coverage checks | asynchronous-market alignment remains simplified |
| Eligibility | return counts and listing identity | feature-history eligibility | reconciliation module | minimum common history and status classification | daily-history count | observations/status | evaluated at each scoring date | short history remains diagnostic | attached run metadata | 1M/3M/6M/12M eligibility tests | 252 returns require at least 253 valid prices |
| Feature engineering | trailing eligible returns | per-security raw features | `global_stock_scoring.py` | momentum, volatility, downside, trend, mean reversion, diversification | trailing daily windows | decimals/ranks | train-end only in walk-forward | missing required feature prevents standard score | run metadata attached | monotonicity/history tests | score weights are policy choices |
| Stock scoring | eligible features and metadata | stock score/rank table | `build_global_stock_scores` | component ranks plus configured weighted composite | rebalance date | percentile/rank/score | current or fold train-end | ineligible assets excluded from standard rank | run metadata attached | independent rank and selection-count tests | no fundamental/valuation signal |
| Forecasting | lagged historical returns/features | forecasts and validation tables | forecast engine and validation | purged chronological Ridge and horizon return targets | 1M/3M/6M/12M horizons | decimal horizon return/error | forecast origin | insufficient history blocks forecast | run metadata attached | random-walk, scale and leakage tests | heuristic uncertainty; diagnostic only |
| Portfolio league | selected returns, scores, optional diagnostic forecasts | league metrics, weights and model status | `global_portfolio_league.py` | 1/N, shrinkage GMV, inverse vol, HRP, risk parity, LP CVaR and diagnostics | static sample / rebalance train window | weights and decimal metrics | uses only supplied sample | complete selected-weight return rows required | run metadata attached | constraints, PSD, convergence and no-fallback tests | expected-return models fragile |
| Risk | returns and model weights | risk, tail, contribution and stress reports | `global_portfolio_risk.py` | arithmetic return, CAGR, volatility, LPM Sortino, drawdown, historical VaR/CVaR | daily to annualized | decimal returns/ratios | sample end | missing weighted ticker fails | run metadata attached | independent reference math and sanity checks | historical/stylized estimates |
| Walk-forward | full returns, universe and config | OOS returns, weights, folds, turnover and leakage audit | `global_walk_forward.py` | 252-day train, 21-day test/step, up to 12 non-overlapping folds | daily OOS | net decimal return | train end precedes each test | fold eligibility recomputed; no zero fill | run metadata attached | date-overlap, leakage and same-protocol tests | current-universe survivorship bias |
| Random benchmark | fold selected universe and constraints | OOS random distribution | walk-forward random benchmark | positive uniform raw scores projected to capped simplex | every fold / daily OOS | weights and net metrics | same folds as models | same common-return policy | run metadata attached | seed, cap, sum and non-degeneracy tests | not uniform over feasible capped simplex |
| Robustness | returns, scores, configs | sensitivity/stability artifacts | `global_robustness.py` | bounded deterministic base plus seeded scenario sample | current sample | metrics/config values | current run | infeasible combinations skipped explicitly | run metadata attached | dimension-coverage tests | not nested OOS; cannot promote |
| Model selection | league, OOS, risk, random, uncertainty and robustness | selection report and final decision | `global_model_selection.py` | hard gates then OOS Sharpe rank | one decision per run | booleans, ratios, status | one coherent run | missing evidence fails active gates | run identity required | EW self-comparison and gate tests | no White/SPA/DSR/PBO |
| Final weights/exposure | final decision and league weights | full weights and exposure tables | exposure/report scripts | direct aggregation by sleeve/region/sector/etc. | one run snapshot | weights summing to 1 | same final run | missing metadata becomes warning, not invented | run metadata attached | reconciliation and sum tests | economic-country coverage incomplete |
| Reporting/validation | all registered artifacts | PDF, HTML, Excel, visual CSVs, validator JSON | report builders and validators | no model choice; render validated evidence | run snapshot | labelled display units | run ID/as-of visible | missing required artifact fails | mixed run IDs rejected | artifact, visual and independent math validation | output quality still requires rendered QA |

## Layer Audit

| Layer | Primary code | Required invariant | Failure behavior | Audit status |
|---|---|---|---|---|
| Source universe | `security_universe.py`, universe builders | no fabricated top-100, market cap, rank or source | unsupported claims become blockers | Controlled |
| Security identity | `security_identity.py` | ticker is not treated as a permanent identifier | uncertain/reused identities are blocked or manual review | Controlled with public-source limitations |
| Returns and FX | `global_returns.py`, returns builder | adjusted-price semantics, no zero-filled missing return, USD only after validated FX | missing/invalid inputs excluded or fail | Controlled with provider/corporate-action limitations |
| Statistical diagnostics | `global_statistical_diagnostics.py` | correct return type and labelled estimator | non-applicable statistics are not promoted | Diagnostic |
| History eligibility | `security_history_reconciliation.py`, scoring | 12-month features require common 252-observation history | short history remains visible but not standard eligible | Controlled |
| Stock scoring | `global_stock_scoring.py` | equity-only default, historical features only, finite comparable inputs | ineligible assets do not enter standard ranking | Research input |
| Forecasting | forecast engine and validators | chronological/purged training, no future target leakage, random-walk benchmark | weak models remain diagnostic | Diagnostic only |
| Portfolio league | `global_portfolio_league.py` | long-only, full investment, cap feasibility, explicit optimizer status | no silent fallback under a false model label | Controlled |
| Portfolio risk | `global_portfolio_risk.py` | coherent units/signs and complete weighted inputs | impossible/non-finite outputs fail validation | Controlled, historical/stylized |
| Walk-forward | `global_walk_forward.py` | same dates/universe/costs, train strictly before test | leakage or incomparable folds fail | Primary public-data comparative evidence |
| Uncertainty | paired block bootstrap | synchronized model/EW pairs and CI gate | CI crossing zero blocks active promotion | Implemented, not multiple-testing complete |
| Random benchmark | `global_model_selection.py` | reproducible cap-valid weights and labelled sampling method | degenerate/invalid distribution fails | Diagnostic |
| Robustness | `global_robustness.py` | sampled grid covers configured dimensions; evidence scope explicit | cannot promote because not nested OOS | Diagnostic only |
| Model selection | `global_model_selection.py` | benchmark self-comparison handled; rank after hard gates | no active pass means EW remains benchmark/final | Controlled |
| Run identity | `run_identity.py` | common `run_id`, as-of date and universe snapshot | mixed/stale artifacts fail validator | Controlled |
| Reporting | v2 visual/PDF/HTML/Excel builders | dynamic final model, formulas, limitations and source paths | raw-table or contradictory output is incomplete | Requires final rendered QA |

## Dependency And Contamination Boundaries

1. Security identity and listing eligibility precede all feature and return use.
2. Returns are rebuilt before scores, forecasts, covariance or walk-forward
   evidence.
3. Scores may use only information available at the scoring date.
4. Forecast outputs cannot become allocation priors unless their evidence status
   permits it.
5. Static league metrics cannot substitute for walk-forward metrics in model
   promotion.
6. Current-sample sensitivity cannot substitute for nested OOS robustness.
7. Report builders read the final decision artifact; they do not choose a model.
8. Generated artifacts are disposable evidence and are not source-of-truth code.

## Data-Lineage Contract

Every material generated artifact must be traceable through:

- `run_id`;
- `data_as_of_date`;
- `generated_at`;
- `universe_snapshot_id`;
- source artifact path;
- transformation or method label;
- evidence class.

The final validator must reject a report package that mixes run identities.
Independent arithmetic validation must recompute key portfolio metrics from
source returns and weights rather than accepting report totals.

## Model Responsibilities

| Model | Intended responsibility | Prohibited interpretation |
|---|---|---|
| Equal Weight | hard benchmark and robust default candidate | automatic winner or future outperformance proof |
| GMV | covariance-driven variance minimization | expected-return champion |
| Inverse Volatility | transparent defensive risk scaling | formal equal-risk-contribution solution |
| Risk Parity | risk-budget allocation | guaranteed diversification or return alpha |
| HRP | hierarchical covariance/risk allocation | guaranteed OOS superiority |
| Min CVaR | historical left-tail allocation | complete model of future tail risk |
| Max Sharpe | expected-return/covariance diagnostic | production allocation recommendation |
| Black-Litterman | prior/view integration diagnostic | institutional equilibrium portfolio without valid point-in-time priors/views |
| Policy Constrained | explicit score/constraint allocation | successful model when its feasible set or solver failed |
| Ridge forecast | predictive diagnostic versus random walk | direct trading signal |

## Principal Architectural Risks

### Data

- Current constituents introduce survivorship and look-back universe bias.
- Delisted names and historical constituent changes are not fully represented.
- Exact market-cap-ranked top-100 support is absent for the claimed broad global
  sleeves.
- Public provider adjustments and security-master metadata are not
  institutional reference data.

### Statistical

- OOS history is short relative to the number of models and market regimes.
- Paired block-bootstrap intervals do not solve all multiple-testing risk.
- Forecast confidence is a labelled heuristic, not calibrated probability.
- Tail estimates are historical and sample-sensitive.

### Economic

- Cost is a linear gross-notional turnover proxy; spread, market impact, tax and execution
  constraints are absent.
- The annual risk-free rate is set to 0% as a disclosed simplification.
- Stress scenarios are stylized rather than positions revalued through a full
  factor model.

### Engineering

- Generated evidence must be rebuilt in dependency order.
- Every executable script must set the repository `src` import path or rely on a
  documented installed-package environment. Clean orchestration exposed and
  repaired one missing path bootstrap in the statistical diagnostics script.
- PDF, HTML and Excel semantic agreement must be checked after every rebuild.

## Promotion Boundary

The final public-data research model is selected dynamically from clean
walk-forward evidence. It does not imply:

- a promoted institutional global USD master portfolio;
- a valid historical top-100 backtest;
- a live trading recommendation;
- expected future outperformance.

Institutional promotion remains blocked until point-in-time constituent,
delisting, corporate-action, reference-data, transaction-cost and model-approval
requirements are implemented.

## Architecture Conclusion

The repaired architecture is suitable for reproducible public-data research if
all final validation gates pass. It is not suitable for live trading or
institutional model approval. The final merge-readiness verdict must be based on
the clean rebuilt artifacts, independent arithmetic checks, full test suite and
rendered artifact QA, not on this design document alone.
