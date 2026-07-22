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

- 358 realized observations in the final-sample risk table;
- 252 observations across 12 walk-forward test folds;
- OOS Equal Weight CAGR 107.44%;
- OOS Equal Weight Sharpe 2.5919.

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
| Run ID | `qv2-2026-07-21-4453b1fd66455d43` |
| Data as of | `2026-07-21` |
| Universe snapshot | `universe-3b4a371b4b139640` |
| Data snapshot | `data-9ade4fbcdad81a2dc87c` |
| Config hash | `config-927e366e46f809f645ca` |
| Config scope | `composite:analysis,current_universe,master_portfolio,returns_matrix,source_universe` |
| Analysis config hash | `config-e778648d7f8155ba1884` |
| Current-universe config hash | `config-77f87687ab3f72a5b81b` |
| Master-portfolio config hash | `config-773ed7d07c1328aab394` |
| Returns config hash | `config-15c8c9e152aa1e734b86` |
| Source-universe config hash | `config-9e56cc1fe2fe5d14d1b6` |
| Input fingerprint | `input-8f10cc00eacafcf5c2eb` |

The current universe contains 890 rows. One hundred assets passed the current
return/history pipeline, 100 were scored, 99 met standard 12-month feature
history, 40 were selected, and the final Equal Weight model contains 40
holdings. Cross-artifact reconciliation passed.

All 100 scoped return assets were usable in this clean rebuild. A preceding run
had transient provider failures for UNH and BHP; that historical event remains
recorded in the execution ledger but is not attributed to this run. Coverage
exclusions and large-return outlier records remain visible diagnostics; they are
not converted to zeros or silently winsorized using future information.

## 6. Security Identity

Ticker text is not treated as a permanent security identifier. The identity
layer now separates provider-only confidence, known continuity, ticker reuse,
listing-date evidence, and manual-review states.

SPCX has only 25 valid returns in the clean run and is
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
| 1M | 0.1418 | 0.1555 |
| 3M | 0.3438 | 0.4157 |
| 6M | 0.5644 | 0.6265 |
| 12M | 1.4099 | 1.5656 |

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
| Observations | 358 | short sample |
| Arithmetic annual return | 71.62% | realized annualized estimate |
| CAGR | 98.60% | realized compounded estimate |
| Volatility | 24.22% | annualized |
| Sharpe | 2.9566 | 0% labelled research RF assumption |
| Sortino | 4.6969 | LPM2 convention |
| Calmar | 4.8308 | CAGR / drawdown magnitude |
| Max drawdown | -20.41% | realized peak-to-trough |
| Daily VaR 95 | -1.9833% | historical 5% quantile |
| Daily CVaR 95 | -3.2516% | historical tail mean |
| Total return | 165.04% | over the observed sample |

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

- Inverse Volatility: `[-0.2930, 0.3936]`;
- Risk Parity: `[-0.4118, 0.4908]`;
- HRP: `[-0.7097, 0.3982]`.

Inverse Volatility has the highest active OOS Sharpe, 2.6704, versus Equal
Weight 2.5919, but its improvement is not statistically established and it has
an extreme-metric review warning. Equal Weight therefore remains the
defensible benchmark/final research model.

If the selection table is empty or a valid Equal Weight benchmark is missing,
the result is now `not_available`; no model is fabricated.

## 15. Robustness

The bounded sensitivity grid evaluated 48 of 216 feasible configurations. Its
current-sample diagnostic winner changed materially: GMV led 26 scenarios, HRP
7, Min CVaR 6, Equal Weight 5 and Risk Parity 4. This is
`diagnostic_configuration_stability_only` and explicitly indicates model/weight
fragility rather than stable out-of-sample superiority.

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

The current suite has 392 passing tests. Black, Ruff, compileall, artifact
validation, and `git diff --check` are final release gates. A scoped Pyright
gate covers twelve financial-critical modules and currently reports zero errors
and zero warnings.

## 19. Reproducibility

Run identity separates deterministic input fingerprints from execution
metadata. Core artifacts carry run ID, as-of date, universe/data snapshot IDs,
a composite hash over analysis, current-universe, master-portfolio,
returns-matrix and source-universe configurations, component hashes, and input
fingerprint. A cost, constraint, source-policy or universe-policy change
therefore changes run identity even when market-return bytes are unchanged.

Publication loaders do not trust a passed CSV merely because its filename and
run columns look correct. Every core source is matched to the current artifact
registry by run identity, byte size, and SHA-256 before user-facing publication.
The validator rejects mixed-run, stale, or post-registration-mutated evidence.

Random portfolio, bootstrap, and simulation paths use explicit seeds. Output
files are generated and excluded from the source commit.

The independent reference validator recalculated 45 return, FX, portfolio,
risk, covariance, optimizer, OOS path, cost, random-provenance, bootstrap and
model-selection identities without calling the production metric functions.
All 45 checks passed.

## 20. Reporting

The rebuilt publication package contains:

- 27 chart images;
- 10-page executive quantitative research PDF;
- 13-page scientific methodology and validation appendix;
- responsive v2 HTML with 10 validated SVG charts;
- 69-sheet v2 analytical workbook with 18 primary reader-facing sheets;
- explainable Excel workbook with full weights and blockers.

All 23 PDF pages, all 18 reader-facing workbook sheets and the HTML report at
desktop and 390-pixel mobile width were rendered after the final rebuild.
Workbook structure was inspected across all 69 sheets and ten drawing objects;
the formula-error scan returned zero matches. The HTML contained ten nonempty
SVG charts, no document-level horizontal overflow and no detected visible
clipping.

Visual data contracts enforce an equity curve starting at 1.0, non-positive
drawdown, risk on the x-axis and return on the y-axis, non-degenerate random
benchmarks, same-horizon forecast/error comparison, and exposure sums of one.
The equity and drawdown charts now consume the selected model's raw stitched
walk-forward OOS net returns. The 253 plotted rows comprise one explicit
baseline plus every one of the 252 OOS returns; final wealth and drawdown
reconcile exactly to the raw source.

If a final-model decision is absent, visual/exposure builders no longer assume
Equal Weight.

## 21. Findings By P0/P1/P2/P3

The table counts internal correctness findings from the baseline commit
`492d8d5`. External institutional-data blockers are listed separately.

| Severity | Found | Fixed | Unresolved |
|---|---:|---:|---:|
| P0 - core result invalidation | 12 | 12 | 0 |
| P1 - material interpretation | 49 | 49 | 0 |
| P2 - robustness/quality | 33 | 26 | 7 |
| P3 - engineering/presentation | 12 | 12 | 0 |

P0 repairs covered missing-return arithmetic, FX/stablecoin master inputs,
security/price identity, feature eligibility/ranking, forecast timing,
walk-forward OOS construction, same-protocol random benchmarks, optimizer
fallbacks, Min CVaR formulation, simulation return support, and risk formulas.

P1 repairs covered Equal Weight self-comparison, model-selection thresholds and
uncertainty, metric-warning gates, absent-benchmark behavior, visual/model
fallbacks, v2/legacy weight mixing, robustness labels, covariance labels,
Black-Litterman prerequisites, risk-free labels, run identity, mixed artifacts,
stress semantics, VaR horizon semantics, and projection horizon/missingness.

The governing-objective falsification pass found eleven additional P1 defects
and repaired all eleven: optimistic robustness defaults; random-benchmark provenance
asserted without primitive evidence; non-zero risk-free formula-text drift;
unbounded/implicit missing-data transformations; exposure fallback to a
different or malformed portfolio; non-replayable FX direction; duplicate OOS
rows crashing rather than failing a gate; covariance replay using the wrong
return basis; legacy stages overwriting canonical stress evidence; and an
undeclared report-column fallback that plotted metadata as stress data; and a
full-sample static-weight equity path incorrectly labelled as stitched OOS
evidence.

The final independent review found five further P1 defects and repaired all
five:

1. drawdown functions that omitted the initial-capital peak and could miss an
   immediate first-period loss;
2. model selection that displayed leakage diagnostics but did not fail closed
   when exact current-run fold evidence was missing, failed, or stale;
3. run identity that hashed the returns config but not analysis policy such as
   transaction cost;
4. publication that trusted registered filenames/run columns without
   rechecking source byte size and SHA-256;
5. an AST missing-data audit that could classify non-zero or expression-based
   numerical fills as labels, plus optimistic diversification credit when
   correlation evidence was undefined.

Six additional P2 defects were repaired: incomplete independent reference
coverage, untagged report-critical derived risk evidence, stale publication
requirements and semantic claim checks, a hard-coded validator count in the
methodology appendix, duplicated decision fields in the reader workbook, and
non-round-trip CSV float parsing that produced a false random-weight
fingerprint failure without weakening the canonical hash contract.

Two final P2 defects were also repaired: visual validation now rejects partial
NaN values rather than accepting a partly finite chart, and report model
resolution now treats the final decision artifact as the only authority rather
than falling back to a demo summary.

The closing independent re-review found four further P1 defects and repaired
all four: reader-workbook CSV inputs outside the required bundle were not bound
to the artifact registry; the publication layer trusted the persisted final
decision instead of independently rebuilding it from model-selection
evidence; run identity still omitted three effective universe/master
configuration files; and reader-facing turnover used the alternative
half-L1 convention while the executable cost path used gross traded-notional
L1. It also found four P2 defects and repaired all four: partial missing
correlation evidence could earn partial diversification credit; two
walk-forward CLI policy values were not forwarded; explicit-null forward-fill
limits and unregistered zero-filled `reindex` calls could bypass the
missing-data audit; and forecast/random/exposure chart inputs did not reject
every nonfinite or invalid Boolean value.

A subsequent two-reviewer closure pass found two further P1 defects and
repaired both: synchronized omission of the same date from model and random OOS
paths could preserve self-consistent stored hashes, and publication manifests
did not prove the exact expected package type, member set, complete run
identity and byte sizes. Primitive return-index slices now prove every
fold/model/random date set; publication validates exact type, identity,
membership, uniqueness, size and SHA-256.

The same pass found three P2 defects. Two were repaired: computed forward-fill
limits now require an exact reviewed call-site fingerprint plus a runtime
integer bound, and legacy global-master transaction-cost/promotion settings are
now passed into the executable gate and validated. One structural P2 remains:
a hypothetical positive promotion-grade robustness payload is not yet
independently reconstructed from primitive nested-OOS robustness rows. The
current run supplies diagnostic-only robustness and therefore fails that gate;
this limitation cannot promote or change the current Equal Weight decision.

The final clean package passes 157 of 157 artifact checks, 45 of 45 independent
reference-math checks, and a source-tree audit of 408 missing-data/alignment
operations with zero unapproved calls. The same results are recorded in the
append-only execution ledger.

The final local closure review found one further P1 documentation-provenance
defect: this audit's risk table had carried metrics from a preceding run after a
source-only rebuild changed provider coverage. That table was reconciled at the
time. The subsequent security-identity verification rebuild again refreshed the
entire evidence chain and this audit now matches run
`qv2-2026-07-21-4453b1fd66455d43`; the generated PDF, HTML and Excel package is
bound to the same current-run evidence.

The seven unresolved P2 items are:

1. point-in-time membership and survivorship;
2. official dated market-cap ranks/exact top-100 evidence;
3. complete delisting/corporate-action history;
4. nested OOS sensitivity across all policy dimensions;
5. multiple-testing control across the model search;
6. only 252 OOS observations and extreme point estimates;
7. independent primitive-row reconstruction for any future positive
   promotion-grade robustness claim.

The two previously unresolved P3 items were repaired with a scoped Pyright CI
gate and staged, rollback-capable, manifest-last report/workbook publication.
One additional P3 mobile-overflow defect was found during browser QA and fixed;
wide evidence tables now scroll only within bounded containers. Direct
artifact-validator execution was made independent of the caller working
directory, and final Excel QA repaired a clipped dashboard title and removed
the visual connection between unordered risk-return scatter points.

GitHub Actions then found one further P3 cross-platform portability defect:
on Linux, `Path.name` does not treat a Windows backslash as a separator, so an
adversarial Windows-form path could appear in validator error details. The
helper now uses a platform-independent Windows-path parser for basename
extraction. The previously failing Python 3.10 regression and the full
392-test suite pass locally; the missing-data source hash and 157-check
artifact validation were regenerated after the source change.

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
- every OOS visual is built from that selected-model net path, not a
  full-sample static-weight reconstruction;
- uncertainty uses paired circular block bootstrap;
- model selection requires a positive Sharpe-difference lower confidence bound;
- model selection also requires a complete, passed, current-run leakage audit
  with the exact expected check set for every fold;
- all metric warnings block active model selection pending review;
- drawdown always includes the initial capital value as a possible running
  peak, including first-period-loss edge cases;
- run identity binds both returns and analysis configs, and publication binds
  each source artifact by size and SHA-256;
- numerical fill operations require exact reviewed call-site allowlists, while
  undefined correlation evidence earns zero diversification credit;
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
