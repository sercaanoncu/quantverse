# QuantVerse v2 Decision Register

This register records concise, auditable rationale. It does not contain private
chain-of-thought and it is not investment advice. `Observed impact` is updated
from generated evidence; a decision is invalidated when the listed conditions
occur.

## QV2-DEC-001 - Robustness Evidence Fails Closed

| Field | Record |
|---|---|
| Problem | Model selection exposed an optimistic `stable` default even though the implemented sensitivity grid is diagnostic configuration stability, not nested OOS robustness. |
| Evidence | `global_parameter_sensitivity_summary.json`; `global_model_selection_report.csv`; source caller chain. |
| Why it matters | Missing evidence must not become positive evidence or promote an active model. |
| Affected system | Robustness, model selection, release validator, reports. |
| Previous method | Any status not containing a fragile token could pass; default was `stable`. |
| Candidate methods | Negative-token list; positive promotion-grade whitelist; numeric stability score. |
| Alternative 1 | Negative-token list. |
| Why rejected | Unknown future labels can pass silently. |
| Alternative 2 | Numeric stability score. |
| Why rejected | Current grid is not nested OOS, so a score cannot create promotion evidence. |
| Chosen method | Positive whitelist plus `promotion_eligible`, nested chronological method and same-run identity. |
| Why chosen | It is fail-closed, explicit and auditable. |
| Mathematical basis | No missing-data imputation is valid for a Boolean evidence gate. |
| Statistical basis | Configuration sensitivity and nested OOS robustness answer different questions. |
| Financial/economic basis | Capital-allocation claims require evidence that survives chronological implementation changes and costs. |
| Book support | Palomar; Severini; Ahlawat; Hull; ISLR; López de Prado-oriented validation discussion in *Machine Learning for Algorithmic Trading*. |
| Academic support | Model-risk and data-snooping literature; no claim that current diagnostic sensitivity is nested validation. |
| Assumptions | Promotion-grade evidence, if added later, declares method, run identity and promotion eligibility. |
| Parameters | Allowed status: `promotion_grade_nested_walk_forward_oos`; method: `nested_chronological_walk_forward_oos`. |
| Sensitivity | Unknown, missing, diagnostic, fragile, failed and stale states all fail. |
| Expected impact | Prevent false active-model selection. |
| Observed impact | Current active models remain unpromoted because robustness is diagnostic only. |
| Validation | Missing, stale, diagnostic, fragile and genuine promotion-grade fixtures. |
| Invalidation conditions | Any caller can bypass the evidence object; status whitelist accepts diagnostic evidence; run identity is not checked. |
| Residual limitation | Full nested OOS robustness is not implemented. |
| Status | Implemented; current evidence remains diagnostic. |

## QV2-DEC-002 - Random Benchmark Requires Artifact-Bound Provenance

| Field | Record |
|---|---|
| Problem | A scope string could label a distribution `walk_forward_oos_net` without proving common dates, fold rules, universe, constraints, caps, rebalance or costs. |
| Evidence | Raw model/random OOS returns, fold windows, selected tickers, turnover and run manifest. |
| Why it matters | Comparing an OOS model to an in-sample or differently constrained random distribution is not a valid benchmark. |
| Affected system | Walk-forward, random benchmark, model selection, validator. |
| Previous method | Scope label and non-degenerate Sharpe values. |
| Candidate methods | Trust label; registry hash only; persist raw random OOS rows plus protocol manifest. |
| Alternative 1 | Trust label. |
| Why rejected | It proves semantics by assertion. |
| Alternative 2 | Registry hash only. |
| Why rejected | File identity does not prove protocol equivalence. |
| Chosen method | Persist raw random OOS rows, date hashes, fold/universe hashes, protocol parameters, run identity and protocol hash. |
| Why chosen | Independent validators can reconstruct and falsify the comparison. |
| Mathematical basis | Percentiles require observations from the declared reference distribution. |
| Statistical basis | Benchmark and candidate must share the evaluation sample and data-generating protocol. |
| Financial/economic basis | Max-weight, turnover and cost conventions materially change implementable outcomes. |
| Book support | Palomar; *Machine Learning for Algorithmic Trading*; Dixon, Halperin and Bilokon; ISLR validation principles. |
| Academic support | Out-of-sample benchmarking and data-snooping literature. |
| Assumptions | Current-universe public-data scope; not institutional PIT evidence. |
| Parameters | Train/test/step, max assets/weight, costs, seed, risk-free policy. |
| Sensitivity | Any date, run, config, data, universe or protocol mismatch blocks the gate. |
| Expected impact | Eliminate relabeled static random evidence. |
| Observed impact | Current random distribution is verified against raw same-date OOS net paths. |
| Validation | Static-label, stale-run and mismatched-date adversarial fixtures. |
| Invalidation conditions | Raw random rows are missing; protocol fields are stale; hashes cannot be reproduced. |
| Residual limitation | Random portfolios remain a benchmark, not proof of future superiority. |
| Status | Implemented for current public-data walk-forward. |

## QV2-DEC-003 - Daily Compounded Risk-Free Contract

| Field | Record |
|---|---|
| Problem | A reference formula string used annual-return subtraction while production used a daily compounded hurdle. Zero RF masked the difference. |
| Evidence | Portfolio-risk source, metric contract, reference validator and 5% RF fixture. |
| Why it matters | Frequency mismatch biases Sharpe and Sortino when RF is non-zero. |
| Affected system | Risk metrics, uncertainty bootstrap, documentation. |
| Previous method | Mixed formula wording. |
| Candidate methods | Annual subtraction; simple annual/252; compounded daily hurdle. |
| Alternative 1 | Annual subtraction after annualizing return. |
| Why rejected | It does not exactly match the implemented daily excess-return series. |
| Alternative 2 | Annual rate divided by 252. |
| Why rejected | It ignores compounding. |
| Chosen method | `rf_daily = (1 + rf_annual)^(1/252) - 1`; compute daily excess then annualize. |
| Why chosen | Frequency and compounding are explicit and consistent. |
| Mathematical basis | Equivalent-period rate conversion. |
| Statistical basis | Mean and downside semideviation operate on aligned daily excess observations. |
| Financial/economic basis | The hurdle reflects the declared annual opportunity-cost assumption. |
| Book support | Severini; Ahlawat; Palomar; Hull. |
| Academic support | Sharpe ratio definition and periodic return consistency. |
| Assumptions | 252 trading days and constant annual research hurdle. |
| Parameters | Current config is 0%; regression fixture is 5%. |
| Sensitivity | Non-zero RF changes Sharpe/Sortino; CAGR and volatility are unchanged. |
| Expected impact | Prevent hidden frequency-contract drift. |
| Observed impact | Production and independent metrics reconcile at 5% RF. |
| Validation | Non-zero RF regression and 39-check reference run. |
| Invalidation conditions | Report formula differs; another module uses annual/252; RF frequency is unlabeled. |
| Residual limitation | A constant annual hurdle is simpler than a dated risk-free series. |
| Status | Implemented. |

## QV2-DEC-004 - Independent Validation Uses Primitive Evidence

| Field | Record |
|---|---|
| Problem | The earlier independent validator did not cover several material path and gate calculations. |
| Evidence | Reference validator expanded from 21 to 39 checks. |
| Why it matters | Calling production functions or checking only schemas cannot falsify shared errors. |
| Affected system | Risk, walk-forward, random benchmark, covariance, optimizers, selection. |
| Previous method | Prices/returns, final metrics, final weights and risk contributions. |
| Candidate methods | Duplicate production calls; independent NumPy/pandas replay; external package only. |
| Alternative 1 | Duplicate production calls. |
| Why rejected | Shared implementation errors can pass. |
| Alternative 2 | External package only. |
| Why rejected | Package conventions may differ and obscure project contracts. |
| Chosen method | Primitive arithmetic replay from persisted inputs without importing production metric/optimizer functions. |
| Why chosen | It is transparent, deterministic and convention-aware. |
| Mathematical basis | Direct identities for compounding, covariance, turnover, cost, tail risk and constraints. |
| Statistical basis | Replays the actual sample and paired dates. |
| Financial/economic basis | Verifies net, implementable OOS paths rather than gross summaries. |
| Book support | All eight methodology books, mapped in the compliance matrix. |
| Academic support | Reproducible research and independent model-validation practice. |
| Assumptions | Generated raw evidence is complete and carries one run identity. |
| Parameters | Absolute tolerance `1e-9`; relative tolerance `1e-7`. |
| Sensitivity | Ill-conditioned covariance compares classification and material scale, not unstable last digits. |
| Expected impact | Detect wrong signs, dates, units, costs, constraints and stale evidence. |
| Observed impact | Caught and repaired a validator return-basis mismatch; current evidence passes 39/39. |
| Validation | Tampered CAGR, protocol, robustness and covariance fixtures. |
| Invalidation conditions | A check imports production formulas; required raw evidence is absent; tolerances hide material differences. |
| Residual limitation | It does not independently solve every optimizer objective from scratch yet. |
| Status | Implemented; further optimizer-objective replay remains future work. |

## QV2-DEC-005 - Current Final Research Model

| Field | Record |
|---|---|
| Problem | Select a defensible public-data research model without preserving a prior conclusion. |
| Evidence | Full-sample league, 12-fold stitched OOS net returns, paired block bootstrap, random benchmark, risk and diagnostic robustness. |
| Why it matters | A final label must reflect evidence, not model sophistication or a single point estimate. |
| Affected system | Final weights and all user-facing reports. |
| Previous method | HRP before prior numerical corrections; Equal Weight after the prior red-team audit. |
| Candidate methods | Equal Weight and all actually-run active models. |
| Alternative 1 | Inverse Volatility. |
| Why rejected | Higher OOS point Sharpe is not significant under paired uncertainty and robustness is not promotion-grade. |
| Alternative 2 | HRP. |
| Why rejected | Defensive behavior does not establish statistically robust OOS superiority. |
| Chosen method | Equal Weight as the current public-data research final model and benchmark. |
| Why chosen | No active challenger clears all uncertainty, downside, cost, random and robustness gates. |
| Mathematical basis | Long-only weights sum to one; current 40 holdings are equally weighted. |
| Statistical basis | Path metrics use stitched non-overlapping net OOS returns. |
| Financial/economic basis | Transparent diversification with low estimation dependence. |
| Book support | Palomar and diversification/estimation-error principles across the methodology sources. |
| Academic support | 1/N benchmark and estimation-error literature. |
| Assumptions | Current public-data universe, not PIT institutional membership. |
| Parameters | Current rebuilt config and data snapshot. |
| Sensitivity | The choice can reverse if a challenger obtains current promotion-grade evidence. |
| Expected impact | Honest conservative final label. |
| Observed impact | Equal Weight remains; decision remains `not promoted`. |
| Validation | Model-selection report, decision JSON, independent validator and artifact validator. |
| Invalidation conditions | A challenger clears all gates; benchmark evidence is stale; current run fails validator. |
| Residual limitation | Short OOS history and no nested robustness. |
| Status | Confirmed by the clean rebuild and local validation; still `not promoted` and not an investment recommendation. |

## QV2-DEC-006 - User-Facing Artifacts Publish As One Verified Package

| Field | Record |
|---|---|
| Problem | Sequentially writing PDF, HTML or Excel targets can leave a mixed package when a later write fails. |
| Evidence | Report and workbook builders publish multiple related files; existing outputs can otherwise survive beside partial replacements. |
| Why it matters | A visually valid old artifact and a numerically updated new artifact could be interpreted as one coherent run. |
| Affected system | PDF, HTML, Excel, artifact validator and reproducibility. |
| Previous method | Builders wrote directly to final paths without a package-completion manifest. |
| Candidate methods | Direct writes; preflight only; staged files with rollback and manifest-last publication. |
| Alternative 1 | Direct writes. |
| Why rejected | Failure after the first write can leave mixed evidence. |
| Alternative 2 | Check all staged files before moving them. |
| Why rejected | A replacement or manifest failure can still occur after the preflight check. |
| Chosen method | Build in a unique staging directory, back up existing targets, replace all targets, publish a run/hash manifest last and roll back handled failures. |
| Why chosen | Consumers can distinguish a complete hash-bound package, while recoverable failures restore the previous coherent package. |
| Mathematical basis | Artifact identity is established with SHA-256 equality, not filename equality. |
| Statistical basis | All reported estimates must refer to the same run and input evidence. |
| Financial/economic basis | Portfolio decisions cannot be defended when holdings, metrics and limitations come from different executions. |
| Book support | Reproducible workflows and validation discipline across the eight methodology sources; this is primarily a research-engineering control. |
| Academic support | Reproducible research and model-risk governance practice. |
| Assumptions | Files are on the same local filesystem and handled exceptions reach the rollback path. |
| Parameters | Unique publication ID; run ID; config/input/universe/data identity; SHA-256 per artifact. |
| Sensitivity | Any missing staged file, duplicate target, stale run ID or hash mismatch fails validation. |
| Expected impact | Prevent a handled failed run from appearing as a complete current report package. |
| Observed impact | PDF A, PDF B, compatibility PDF, HTML and Excel are staged, hash-bound to one run and published with manifest-last semantics; synthetic second-target failure restores all previous targets. |
| Validation | Incomplete-stage, rollback, hash, stale-run, mixed-run evidence and staging-cleanup tests; artifact validator independently verifies package manifests. |
| Invalidation conditions | A builder bypasses the helper; consumers ignore the manifest; an unhandled process or machine failure interrupts rollback. |
| Residual limitation | Cross-file replacement is not a filesystem-wide ACID transaction; manifest-last semantics make interrupted packages fail validation. |
| Status | Implemented in report and workbook builders. |

## QV2-DEC-007 - Missing Financial Observations Fail Closed

| Field | Record |
|---|---|
| Problem | Unbounded forward/backward fill and implicit `pct_change` filling can turn unavailable prices or returns into fabricated zero-return observations. |
| Evidence | Repository-wide AST inventory of active `fillna`, `dropna`, `reindex`, `merge`, `join`, `ffill` and `bfill` operations; synthetic long-gap price fixtures. |
| Why it matters | Fabricated observations change expected returns, covariance, drawdown, tail risk, portfolio weights and OOS evidence. |
| Affected system | Price cleaning, returns, diagnostics, market-signal alignment, exposure reconciliation and all downstream models. |
| Previous method | Bounded fill was followed by unbounded forward/backward fill; pandas return calculation could implicitly fill; market signals used unbounded forward fill. |
| Candidate methods | Unlimited imputation; bounded fill plus drop incomplete assets; dynamic missing-asset portfolios. |
| Alternative 1 | Unlimited forward/backward fill. |
| Why rejected | Backfill creates look-ahead and unlimited forward fill creates arbitrarily stale prices. |
| Alternative 2 | Dynamically renormalize weights whenever an asset return is absent. |
| Why rejected | It creates an undocumented daily trading rule and changes the portfolio being evaluated. |
| Chosen method | Apply only an explicit bounded price-gap policy, drop assets still incomplete, compute returns with `fill_method=None`, bound diagnostic signal forward fill and reject invalid final exposure weights. |
| Why chosen | It preserves a fixed, observable portfolio contract and fails before missing data can masquerade as cash or no movement. |
| Mathematical basis | Portfolio return `r_p,t = w_t' r_t` is undefined for a selected asset with an unavailable return unless an explicit cash/trading rule is defined. |
| Statistical basis | Imputation alters the sample, dependence structure, variance and tail distribution. |
| Financial/economic basis | A missing quote is not an executed zero-return position or an automatic rebalance. |
| Book support | Severini; Ahlawat; Palomar; *Machine Learning for Algorithmic Trading*; Dixon, Halperin and Bilokon. |
| Academic support | Missing-data, stale-price, nonsynchronous-trading and leakage controls. |
| Assumptions | A finite configured price gap can be bridged only by a documented bounded rule; longer gaps make the asset ineligible for that matrix. |
| Parameters | Explicit finite fill limit; simple returns use no implicit fill; diagnostic market-signal limit is five observations. |
| Sensitivity | A stricter gap limit can reduce the eligible universe; a looser limit increases stale-price bias. |
| Expected impact | Eliminate look-ahead backfill, implicit zero returns and silent portfolio renormalization. |
| Observed impact | The final active-source inventory contains 408 reviewed operations and zero unapproved operations, including exact allowlists for structural-zero and non-zero numerical call sites. |
| Validation | Long-gap asset exclusion, no implicit return fill, no unbounded source fill, invalid exposure-weight rejection and AST inventory tests. |
| Invalidation conditions | Any active `.bfill()`; unbounded `.ffill()`; selected return zero-fill; unexplained sample reduction; exposure fallback to another model. |
| Residual limitation | Exchange closures and asynchronously traded markets still require explicit calendar-aware treatment beyond a generic finite gap limit. |
| Status | Implemented; current audit has zero unapproved active operations. |

## QV2-DEC-008 - Reader-Facing Reports Separate Decisions From Technical Evidence

| Field | Record |
|---|---|
| Problem | A single table-heavy artifact could not serve executive decision review, methodology audit and technical reproduction without obscuring limitations. |
| Evidence | Existing PDF/HTML/Excel structure, user requirements and current run artifacts. |
| Why it matters | Correct numbers that are unreadable or ambiguously scoped remain incomplete research evidence. |
| Affected system | Executive PDF, methodology appendix, HTML and analytical workbook. |
| Previous method | One broad report and a workbook whose reader path was dominated by technical tables. |
| Candidate methods | One monolithic report; two PDFs plus responsive HTML and tiered workbook; dashboard-only output. |
| Alternative 1 | One monolithic report. |
| Why rejected | Executive findings and detailed validation compete for space and hierarchy. |
| Alternative 2 | Dashboard-only output. |
| Why rejected | It cannot carry formulas, assumptions, lineage and invalidation conditions needed for scientific audit. |
| Chosen method | Executive chart-led PDF A, methodology PDF B, responsive HTML and workbook with 18 reader-facing decision sheets followed by separated technical evidence. |
| Why chosen | Each audience receives an appropriate first view while all outputs remain bound to the same run and source evidence. |
| Mathematical basis | Every displayed metric and chart is sourced from validated artifacts rather than recomputed decorative summaries. |
| Statistical basis | OOS, uncertainty and benchmark scope are presented separately from full-sample diagnostics. |
| Financial/economic basis | Portfolio holdings, downside risk, costs, exposure and promotion status are visible before implementation claims. |
| Book support | The eight local methodology sources support the quantitative content; information architecture is a research-communication control. |
| Academic support | Reproducible research, model documentation and risk-governance practice. |
| Assumptions | A complete one-run evidence package and final weights exist. |
| Parameters | Ten non-decorative chart contracts; each declares method, interpretation, limitation and invalidation condition. |
| Sensitivity | Missing or stale evidence blocks publication rather than silently omitting a section. |
| Expected impact | Make the result reviewable by portfolio, risk, quantitative and engineering readers without weakening scientific caveats. |
| Observed impact | PDF A, PDF B, HTML and a 69-sheet workbook were generated from the current evidence package; every PDF page, all reader-facing workbook sheets and desktop/mobile HTML were visually inspected and repaired where needed. |
| Validation | Mixed-run loader rejection, publication manifests, workbook schema/formula checks, artifact validator and full-page/sheet visual QA. |
| Invalidation conditions | Raw tables dominate reader-facing sections; model or promotion scope is ambiguous; charts lack provenance; visual QA fails. |
| Residual limitation | Static PDFs cannot provide the same exploration depth as the HTML or workbook. |
| Status | Implemented; clean rebuild and visual QA passed locally. |

## QV2-DEC-009 - Incremental Static Typing Covers The Financial Critical Path

| Field | Record |
|---|---|
| Problem | Runtime tests did not statically constrain heterogeneous dataframe results, nullable state or evidence-package key types in critical finance modules. |
| Evidence | Initial Pyright run over eight modules reported 120 errors; adding the returns module exposed seven more before repair. |
| Why it matters | A dataframe/series ambiguity, nullable return matrix or wrongly typed evidence package can reach a financial calculation even when a happy-path fixture passes. |
| Affected system | Returns, identity, portfolio contract, league, walk-forward, risk, numerical integrity and model selection. |
| Previous method | Black, Ruff, tests and compile checks only. |
| Candidate methods | Full-repository strict rewrite; broad diagnostic suppression; incremental basic-mode critical-path gate. |
| Alternative 1 | Full strict rewrite. |
| Why rejected | It is disproportionately large and could introduce behavioral risk unrelated to material correctness. |
| Alternative 2 | Disable pandas-related diagnostic classes globally. |
| Why rejected | It would make the gate appear green while hiding the exact dataframe ambiguities the gate should detect. |
| Chosen method | Pyright basic mode with pandas stubs and an explicit twelve-module include list; no ignore list and no disabled diagnostic categories. |
| Why chosen | It provides an enforceable, reviewable gate on the highest-risk path while allowing safe incremental expansion. |
| Mathematical basis | Financial scalar operations must receive declared scalar values; portfolio output packages must have stable typed fields. |
| Statistical basis | Nullable or wrong-shaped evidence must be resolved before sample calculations. |
| Financial/economic basis | Missing returns, wrong model keys or malformed weights must not be accepted through dynamic type ambiguity. |
| Book support | Reproducibility and validation principles across the methodology sources; static typing is primarily an engineering control. |
| Academic support | Software assurance and reproducible computational research practice. |
| Assumptions | Python 3.10 minimum; current supported pandas API and matching stubs. |
| Parameters | `typeCheckingMode=basic`; twelve explicit critical modules; `pandas-stubs` and Pyright in dev dependencies. |
| Sensitivity | Stub upgrades may expose new API ambiguities and require reviewed source changes. |
| Expected impact | Detect nullable state, wrong package keys, dataframe/series ambiguity and invalid scalar conversions before execution. |
| Observed impact | Current scoped gate reports zero errors and zero warnings; 66 targeted behavior tests passed across the typed returns and finance paths. |
| Validation | `python -m pyright`; CI gate; config-contract test; targeted financial regression tests. |
| Invalidation conditions | An include path is removed; an ignore or broad diagnostic override is added; Pyright is omitted from CI; the gate reports an error. |
| Residual limitation | Modules outside the declared critical list are not yet type-gated. |
| Status | Implemented and CI-enforced. |

## QV2-DEC-010 - Validators Must Replay FX Evidence And Reject Invalid OOS Without Crashing

| Field | Record |
|---|---|
| Problem | The independent validator checked native-USD equality but could not reconstruct a non-native FX conversion; duplicate OOS rows later caused bootstrap pivot failure instead of a controlled rejection. |
| Evidence | Adversarial wrong-direction and duplicate model-date fixtures. |
| Why it matters | FX direction can reverse economic exposure, and a validator crash can conceal rather than classify invalid OOS evidence. |
| Affected system | Returns output, independent reference math, bootstrap inputs and adversarial audit. |
| Previous method | FX report labels plus native-base equality; bootstrap pivot assumed unique model-date rows. |
| Candidate methods | Trust metadata; persist raw FX evidence and replay; aggregate duplicate OOS rows. |
| Alternative 1 | Trust FX direction labels. |
| Why rejected | Labels do not prove that the numeric conversion used the declared direction. |
| Alternative 2 | Aggregate duplicate OOS rows before bootstrap. |
| Why rejected | Aggregation hides overlapping test windows and double-counted evidence. |
| Chosen method | Persist raw FX prices and finite fill policy, independently replay inversion/compounding, and reject duplicate model-date rows before pivot. |
| Why chosen | Both errors become reproducible failed checks with explicit invalidation conditions. |
| Mathematical basis | `R_base=(1+R_local)(1+R_FX_to_base)-1`; one stitched net OOS return per model/date. |
| Statistical basis | Duplicate dates invalidate paired sample size and path-dependent bootstrap evidence. |
| Financial/economic basis | A wrong currency quote direction reverses the portfolio's currency translation effect. |
| Book support | Severini; Ahlawat; Palomar; Hull; time-ordered validation principles in the ML sources. |
| Academic support | Base-currency return identities and paired time-series resampling requirements. |
| Assumptions | Raw FX prices, quote direction, inversion flag and finite alignment policy are persisted. |
| Parameters | Up to five representative normalized assets replayed; existing numerical tolerances; duplicate count must equal zero. |
| Sensitivity | If no non-native asset is present, the check is explicitly scope-limited rather than claiming empirical FX coverage. |
| Expected impact | Wrong-direction FX, missing raw FX evidence and overlapping OOS rows cannot pass. |
| Observed impact | All 12 adversarial attack classes are rejected; the duplicate-date crash was converted into a deterministic failed validation row. |
| Validation | Reference-math adversarial fixture, FX normalization tests and model-selection provenance tests. |
| Invalidation conditions | Raw FX prices are not persisted for a normalized asset; quote policy is absent; duplicate rows are aggregated or ignored. |
| Residual limitation | Current public-data run may contain only native-base assets, so non-native replay remains validated through synthetic regression evidence until such assets enter the run. |
| Status | Implemented. |

## QV2-DEC-011 - Canonical Evidence Paths Have One Declared Owner And Schema

| Field | Record |
|---|---|
| Problem | A legacy global-master stage and a projection stage could overwrite the canonical run-bound stress-test artifact with different, untagged schemas; the report stress chart also accepted an undeclared fallback pair of columns. |
| Evidence | The first clean rebuild failed publication identity validation on `global_stress_test_results.csv`; rendered PDF page 7 then exposed a metadata-driven blank stress chart. |
| Why it matters | A reused filename can mix runs or silently change the meaning of a downstream chart while all files still exist. |
| Affected system | Stress testing, publication identity, PDF/HTML charts and artifact validation. |
| Previous method | Three stages reused one output path, and the chart fell back to the last two columns when expected columns were absent. |
| Candidate methods | Keep overwriting and infer schema; choose the latest file; give each producer a unique path and require declared chart columns. |
| Alternative 1 | Choose whichever stress file was written last. |
| Why rejected | Execution order is not scientific provenance and does not prove schema or run identity. |
| Alternative 2 | Continue positional column fallback. |
| Why rejected | Metadata such as config and input hashes can be plotted as if they were scenarios and losses. |
| Chosen method | Preserve `global_stress_test_results.csv` for canonical risk evidence, namespace legacy master/projection outputs, and accept only declared current or explicit legacy stress columns. |
| Why chosen | Artifact ownership, identity and visualization semantics become deterministic and fail closed. |
| Mathematical basis | A stress chart plots a declared scenario against a numeric portfolio-loss estimate; arbitrary column position has no valid mathematical interpretation. |
| Statistical basis | Each plotted observation must belong to the same selected model and run; metadata fields are not statistical outcomes. |
| Financial/economic basis | Scenario losses must represent explicit portfolio shocks, not incidental execution identifiers. |
| Book support | Palomar and the financial-statistics sources support explicit scenario/risk semantics; artifact ownership is primarily a research-engineering control. |
| Academic support | Reproducible research, data lineage and model-risk governance practice. |
| Assumptions | The canonical risk builder remains the owner of the current stress schema. |
| Parameters | Current schema: `model_name`, `scenario`, `portfolio_loss_estimate`; explicit legacy schema: `Scenario`, `Portfolio_Impact`. |
| Sensitivity | Any unknown, empty or mixed schema raises instead of producing a chart. |
| Expected impact | Prevent mixed-run publication and semantically false stress graphics. |
| Observed impact | The second clean rebuild completed under one run identity; page 7 now displays the declared scenario-loss bars. |
| Validation | Canonical-file preservation regression, two stress-schema tests, one-run publication loader and artifact validator. |
| Invalidation conditions | Another stage writes the canonical path; chart code accepts positional columns; stress rows lack the final-model filter or run identity. |
| Residual limitation | Scenarios remain stylized sensitivities and are not calibrated event probabilities. |
| Status | Implemented and visually verified. |

## QV2-DEC-012 - Canonical Float Fingerprints Require Round-Trip CSV Parsing

| Field | Record |
|---|---|
| Problem | A persisted random-weight matrix failed its declared canonical frame hash even though the CSV text was produced by the same clean run. |
| Evidence | Default pandas parsing and `float_precision="round_trip"` produced numerically equivalent values but different low-order binary representations and therefore different frame hashes. |
| Why it matters | A false provenance failure blocks valid evidence; weakening or skipping the hash would instead admit real benchmark drift. |
| Affected system | Random benchmark provenance, independent reference math, artifact validation and publication evidence loading. |
| Previous method | Hash-critical CSVs used pandas' default float parser. |
| Candidate methods | Relax the fingerprint tolerance; hash raw CSV bytes only; parse serialized decimals with round-trip precision and retain the canonical frame contract. |
| Alternative 1 | Relax numeric equality or ignore the mismatch. |
| Why rejected | The benchmark contract requires exact replay of dates, labels and weights; tolerance could hide a real changed portfolio. |
| Alternative 2 | Hash only raw CSV bytes. |
| Why rejected | Byte hashes are sensitive to harmless line-ending/format differences and do not verify the canonical tabular content consumed by research code. |
| Chosen method | Use round-trip float parsing for hash-critical evidence and then compute the unchanged canonical frame fingerprint. |
| Why chosen | It reconstructs the serialized decimal values faithfully while preserving exact content provenance. |
| Mathematical basis | IEEE-754 values reconstructed from decimal text must round-trip to the same binary float before byte-level canonical hashing. |
| Statistical basis | No statistic or tolerance is changed; only deterministic evidence reconstruction is corrected. |
| Financial/economic basis | Random portfolio weights and protocol evidence remain exactly the portfolios against which the candidate was evaluated. |
| Book support | Reproducibility principles across the methodology sources; this is principally a numerical/data-engineering control. |
| Academic support | Reproducible computational research and canonical serialization practice. |
| Assumptions | CSV numeric fields were serialized with sufficient decimal precision. |
| Parameters | `float_precision="round_trip"` on the shared hash-critical CSV reader. |
| Sensitivity | Any actual value, row, column, date or label change still changes the fingerprint. |
| Expected impact | Valid persisted evidence replays exactly without reducing provenance strictness. |
| Observed impact | The current random-weight file reproduces its production `frame-333aea...` fingerprint; the default parser's false `frame-af15...` mismatch is eliminated. |
| Validation | Dedicated round-trip fingerprint regression, current independent reference replay and artifact validator. |
| Invalidation conditions | A hash-critical reader returns to default parsing; a writer loses sufficient precision; the canonical column/order contract changes without versioning. |
| Residual limitation | Other external formats require their own canonicalization contracts. |
| Status | Implemented. |

## QV2-DEC-013 - OOS Visuals Must Consume The Raw Stitched Net Decision Path

| Field | Record |
|---|---|
| Problem | The equity/drawdown report path was labelled OOS but was rebuilt from full-sample USD returns and static final weights; dividing by the first wealth value also removed the first return's effect. |
| Evidence | The prior chart had 356 observations beginning in 2025-02 and a -20.45% drawdown, while the selected model's walk-forward path had 252 observations from 2025-07-14 through 2026-07-14 and a -13.25% drawdown. |
| Why it matters | A visually plausible chart can materially misstate horizon, portfolio process, costs and risk while contradicting model-selection evidence. |
| Affected system | Visual analytics CSVs, executive PDF, HTML, Excel, drawdown interpretation and publication validation. |
| Previous method | Apply static final weights to the full available return matrix, cumulate, then normalize the first observed wealth to 1. |
| Candidate methods | Relabel it as full-sample diagnostic; reconstruct OOS from folds; consume the persisted selected-model stitched OOS net path directly. |
| Alternative 1 | Keep the path and change only the label. |
| Why rejected | It would remain a different construction from the decision evidence and could not support an OOS section. |
| Alternative 2 | Reconstruct from fold summaries. |
| Why rejected | Fold summaries lose daily path dependence and can omit turnover-cost timing or duplicate dates. |
| Chosen method | Filter the raw walk-forward return artifact to the selected model, require unique finite chronological dates, prepend an explicit pre-OOS baseline of 1.0, and compound every net simple return once. |
| Why chosen | The chart becomes a direct view of the same primitive path used for OOS performance, uncertainty and model selection. |
| Mathematical basis | \(W_0=1\), \(W_t=W_{t-1}(1+R_t)\), and \(DD_t=W_t/\max_{u\le t}W_u-1\). |
| Statistical basis | Path-dependent statistics require one non-overlapping observation per OOS date; no fold averaging or full-sample substitution is valid. |
| Financial/economic basis | Net walk-forward returns include the declared rebalance turnover cost and changing historical portfolio weights. |
| Book support | Palomar, Severini, Ahlawat and the ML validation sources support chronological OOS evaluation and path-consistent portfolio measurement. |
| Academic support | Walk-forward evaluation, reproducible backtesting and drawdown path dependence. |
| Assumptions | The raw walk-forward return artifact is one-run, selected-model, non-overlapping and net of declared costs. |
| Parameters | 252 OOS returns plus one explicit baseline; baseline date is the preceding business day. |
| Sensitivity | A selected-model change, return correction, cost correction or date correction forces the chart and all reports to rebuild. |
| Expected impact | Reported OOS wealth and drawdown reconcile exactly to model-selection evidence. |
| Observed impact | Current final wealth is 2.07441116148399 and max drawdown is -0.13252777500154134 over 2025-07-14 to 2026-07-14; every raw return is included once. |
| Validation | Exact cumulative-product replay, drawdown recomputation, source-scope check, duplicate-date rejection and adversarial full-sample-mislabel fixture. |
| Invalidation conditions | Source scope is not `walk_forward_oos_net`; model/date rows overlap; any return is omitted; baseline is not 1; chart metrics fail source reconciliation. |
| Residual limitation | The OOS sample remains short and current-universe biased; accurate visualization does not create institutional PIT evidence. |
| Status | Implemented, rebuilt and visually verified. |

## QV2-DEC-014 - Initial Capital Is Part Of Every Drawdown Path

| Field | Record |
|---|---|
| Problem | Several active and legacy drawdown functions initialized the running peak from the first post-return wealth observation rather than from initial capital. |
| Evidence | The path `[-20%, +25%]` could report no initial loss even though capital fell from 1.0 to 0.8 before recovering. |
| Why it matters | Drawdown is path-dependent capital loss; omitting the initial peak understates downside risk and can alter Calmar, stress and model comparisons. |
| Affected system | Portfolio risk, backtest metrics, regime diagnostics, simulations, dashboard data, tearsheets, reports and independent reference math. |
| Previous method | Compute cumulative wealth and divide by its post-return cumulative maximum. |
| Candidate methods | Prepend a 1.0 wealth row; clip the running peak at 1.0; special-case only the first return. |
| Alternative 1 | Prepend a synthetic dated row in every internal series. |
| Why rejected | It changes internal indexing and observation counts where only the peak initialization is required. |
| Alternative 2 | Special-case a negative first return. |
| Why rejected | It duplicates the general running-peak identity and is easier to drift across modules. |
| Chosen method | Treat 1.0 as the minimum running peak by initialization or `cummax().clip(lower=1.0)`. |
| Why chosen | It preserves existing return observations while implementing the exact capital-path definition. |
| Mathematical basis | \(W_0=1\), \(W_t=\prod_{u=1}^t(1+R_u)\), \(DD_t=W_t/\max_{0\le u\le t}W_u-1\). |
| Statistical basis | No distributional assumption is required; the statistic is an exact deterministic function of the ordered return path. |
| Financial/economic basis | Initial invested capital is a real prior peak and a first-period loss is economically meaningful. |
| Book support | Palomar and the financial-statistics sources treat drawdown as loss relative to the historical capital peak. |
| Academic support | Path-dependent risk measurement and Calmar-ratio definitions. |
| Assumptions | Returns are chronological, finite and no return is below -100%. |
| Parameters | Initial wealth 1.0; numerical tolerance only for validation. |
| Sensitivity | Any first-return or path change recomputes the complete wealth, peak and drawdown sequence. |
| Expected impact | First-period losses are never omitted and drawdown remains non-positive. |
| Observed impact | The deterministic `[-20%, +25%]` regression returns a -20% maximum drawdown; current full-sample and OOS results remain internally reconciled. |
| Validation | Cross-module edge-case tests, visual source replay and independent reference calculation. |
| Invalidation conditions | Peak starts after the first return, wealth omits an observation, drawdown is positive, or the source path is not chronological. |
| Residual limitation | Historical drawdown does not estimate future crisis loss or market liquidity. |
| Status | Implemented and regression-tested. |

## QV2-DEC-015 - Leakage Evidence Is A Fail-Closed Selection Gate

| Field | Record |
|---|---|
| Problem | Walk-forward leakage checks were reported but did not always participate in model eligibility. |
| Evidence | Missing, failed, stale or incomplete audit rows could coexist with an otherwise eligible model-selection row. |
| Why it matters | A model cannot be promoted on out-of-sample evidence when the temporal boundary itself is unproven. |
| Affected system | Walk-forward audit, model-selection CSV/JSON, final decision, publication and artifact validation. |
| Previous method | Display leakage diagnostics and rely primarily on return/uncertainty/robustness gates. |
| Candidate methods | Warning only; one aggregate boolean; exact per-fold current-run evidence gate. |
| Alternative 1 | Retain a nonblocking warning. |
| Why rejected | It permits a scientifically invalid model to remain selectable. |
| Alternative 2 | Trust one aggregate leakage status. |
| Why rejected | It cannot prove every expected fold/check combination or detect stale evidence. |
| Chosen method | Require the exact expected per-fold check set, all passed, current run identity and known evidence scope. |
| Why chosen | Eligibility now depends on the primitive temporal-validation evidence rather than a label. |
| Mathematical basis | Boolean conjunction over expected fold/check keys, pass flags, run identity and scope. |
| Statistical basis | Chronological OOS inference requires strict separation between information available at rebalance and subsequent test observations. |
| Financial/economic basis | Trading decisions cannot use prices, features, constituents or targets that were unavailable at decision time. |
| Book support | ISLR, Hull, Jansen and the finance-ML sources require leakage-free train/test ordering. |
| Academic support | Walk-forward validation, look-ahead-bias prevention and reproducible backtesting. |
| Assumptions | The walk-forward engine emits the declared complete check taxonomy for every fold. |
| Parameters | Exact check-set equality; no optimistic default for missing evidence. |
| Sensitivity | Any fold, check, run ID or scope change invalidates the gate until evidence is rebuilt. |
| Expected impact | Missing or stale leakage evidence makes all affected strategies ineligible. |
| Observed impact | Current eligible rows have `leakage_gate_pass=True` and `verified_current_no_lookahead_with_survivorship_limitation`; adversarial states produce `not_available`. |
| Validation | Missing, failed, stale, incomplete and valid-current-run fixtures plus independent reconciliation. |
| Invalidation conditions | An expected check is absent, any check fails, run identity differs, evidence scope is unknown, or selection ignores the gate. |
| Residual limitation | Leakage control does not cure current-universe survivorship or absent institutional point-in-time membership. |
| Status | Implemented, rebuilt and independently verified. |

## QV2-DEC-016 - Run Identity And Publication Bind All Decision Inputs

| Field | Record |
|---|---|
| Problem | Run identity omitted analysis-policy inputs, and publication could trust a registered source after its bytes changed. |
| Evidence | Changing transaction cost did not affect a returns-only config hash; a CSV could retain its filename/run column after post-registration mutation. |
| Why it matters | Two economically different analyses or two byte-different evidence files must not share one authoritative publication identity. |
| Affected system | Run manifest, all run-tagged artifacts, artifact registry, PDF/HTML/Excel publication and validator. |
| Previous method | Hash the returns config and validate source filenames/run columns. |
| Candidate methods | Hash every repository file; named composite config components plus content-addressed artifact registry; timestamp-only execution ID. |
| Alternative 1 | Hash the entire repository. |
| Why rejected | Unrelated documentation or generated changes would invalidate an otherwise identical analysis and obscure the decision boundary. |
| Alternative 2 | Use timestamps only. |
| Why rejected | Timestamps are not deterministic content identity and cannot prove equivalence. |
| Chosen method | Hash named analysis, current-universe, master-portfolio, returns-matrix and source-universe config components; bind every publication source by current run identity, byte size and SHA-256. |
| Why chosen | The identity changes for material policy drift and detects stale or mutated evidence without including unrelated files. |
| Mathematical basis | Deterministic canonical hashes over named config payloads and raw artifact bytes. |
| Statistical basis | Reproducibility requires identical data, protocol and policy inputs for comparable estimates. |
| Financial/economic basis | Costs, constraints and model policies change net portfolio decisions even when market returns are identical. |
| Book support | The validation and backtesting sources require predeclared protocols and reproducible evidence. |
| Academic support | Computational reproducibility, provenance and content-addressed data integrity. |
| Assumptions | Config components are complete for the declared pipeline and the registry is written after source publication. |
| Parameters | SHA-256, exact file size, named component order and canonical serialization. |
| Sensitivity | Any component or source-byte change forces a new hash and publication rebuild. |
| Expected impact | Stale, analysis-drifted or post-registration-mutated evidence cannot be published as current. |
| Observed impact | Current scope is `composite:analysis,current_universe,master_portfolio,returns_matrix,source_universe`; policy/config mutation changes run identity; post-registration mutation is rejected. |
| Validation | Component-mutation regressions, source-mutation adversarial tests, registry replay and 157-check artifact validator. |
| Invalidation conditions | A material input is omitted from component hashing, hash verification is skipped, or publication accepts an unregistered source. |
| Residual limitation | External provider revisions with identical local bytes cannot be detected without provider-side immutable version identifiers. |
| Status | Implemented, rebuilt and verified. |

## QV2-DEC-017 - Numerical Fills And Undefined Evidence Require Exact Conservative Policy

| Field | Record |
|---|---|
| Problem | AST classification could label numerical expressions as metadata fills, and undefined correlations could receive positive diversification credit. |
| Evidence | A non-zero/expression `fillna` could evade numerical review; single-asset or unavailable-correlation cases used an optimistic score. |
| Why it matters | Silent numerical imputation changes returns, covariance and ranks, while no-evidence diversification credit can promote an incomparable asset. |
| Affected system | Repository missing-data audit, zero/numeric call-site allowlists and global stock scoring. |
| Previous method | Infer fill intent from broad syntax/category and use a positive fallback for unavailable average correlation. |
| Candidate methods | Ban all numerical fills; exact reviewed call-site allowlists; permit broad category defaults. |
| Alternative 1 | Ban every numerical fill. |
| Why rejected | Structural zero weights and explicitly reviewed diagnostics have valid, non-return meanings. |
| Alternative 2 | Keep broad category defaults. |
| Why rejected | It cannot distinguish a harmless label from a financially material numerical expression. |
| Chosen method | Classify AST fill values by type and require exact fingerprinted allowlists for zero and non-zero numerical operations; undefined correlation earns zero credit. |
| Why chosen | Every numerical fallback has a reviewable rationale, and absence of evidence cannot improve selection rank. |
| Mathematical basis | Exact call-site fingerprint matching and a neutral-lower-bound diversification score of zero when correlation is undefined. |
| Statistical basis | Missingness is not evidence of a zero return or favorable dependence structure. |
| Financial/economic basis | Fabricated observations and optimistic no-history scores distort allocation and risk. |
| Book support | The statistics, portfolio and finance-ML sources require explicit missing-data policy and comparable feature windows. |
| Academic support | Missing-data mechanisms, estimation-error control and conservative model governance. |
| Assumptions | Allowlist entries are manually reviewed, source-tree-bound and restricted to declared semantics. |
| Parameters | Exact AST fingerprint, source path/line and written rationale; no wildcard approval. |
| Sensitivity | Source edits move/fingerprint call sites and require review before the audit passes again. |
| Expected impact | Unreviewed numerical fills fail; undefined correlation cannot inflate a score. |
| Observed impact | The final inventory contains 408 reviewed operations and zero unapproved operations; synthetic expression/non-zero attacks fail. |
| Validation | Repository-wide AST audit, exact allowlist tests, string/bool controls and single-asset correlation regression. |
| Invalidation conditions | A numerical operation bypasses the audit, an allowlist becomes wildcard-based, or missing correlation receives positive credit. |
| Residual limitation | Reviewed complete-case deletion can still alter sample composition and remains disclosed rather than statistically corrected. |
| Status | Implemented and source-audited. |

## QV2-DEC-018 - Publication Recomputes Claims From Registered Primitive Evidence

| Field | Record |
|---|---|
| Problem | Optional workbook inputs and persisted decision/turnover labels could bypass the exact evidence and formula contracts used by the executable pipeline. |
| Evidence | An unregistered additional CSV could enter Excel; a mutated `promoted` JSON could remain plausible; reader turnover used half-L1 while costs used gross L1. |
| Why it matters | A publication is a scientific claim surface and must not weaken provenance, promotion or transaction-cost definitions. |
| Affected system | Publication evidence loader, artifact validator, executive/methodology reports and analytical workbook. |
| Previous method | Validate required files, trust the final decision artifact and compute a reader turnover view independently. |
| Candidate methods | Trust signed filenames; validate every source and recompute material claims; remove optional workbook evidence. |
| Alternative 1 | Trust filenames and run columns. |
| Why rejected | They do not prove byte identity or protect against post-registration mutation. |
| Alternative 2 | Remove every optional sheet. |
| Why rejected | Useful evidence can remain when it is held to the same registry contract. |
| Chosen method | Registry-bind every CSV/JSON by run, size and SHA-256; independently reconstruct the model decision; use gross traded-notional L1 throughout. |
| Why chosen | The reader package cannot be stronger, newer or mathematically different from its primitive evidence. |
| Mathematical basis | Exact content hashes, deterministic selection replay and turnover \( \sum_i |w_{i,t}-w_{i,t-1}| \). |
| Statistical basis | Reported OOS inference must correspond to the same observations, policy and selection gates. |
| Financial/economic basis | Promotion and costs change the economic interpretation of a portfolio result. |
| Book support | Portfolio/backtesting sources require explicit costs, comparable benchmarks and reproducible methodology. |
| Academic support | Reproducible research, content-addressed provenance and audit-trail controls. |
| Assumptions | The artifact registry itself is produced last from the completed run and required inputs are enumerated. |
| Parameters | SHA-256, byte size, exact run identity and gross-L1 turnover. |
| Sensitivity | Any source-byte, decision-row or weight-path change requires regeneration. |
| Expected impact | Unregistered/mutated evidence and conflicting promotion or turnover claims fail closed. |
| Observed impact | Current reports reconcile to Equal Weight / `not promoted`; every workbook CSV is registered; turnover matches the cost engine. |
| Validation | Unregistered-source, post-registration mutation, promoted-decision mutation and turnover regressions plus the 157-check validator. |
| Invalidation conditions | A publication source bypasses registry validation, decision replay is skipped or turnover conventions diverge. |
| Residual limitation | Local hashing cannot prove the immutability or legal authority of an upstream provider. |
| Status | Implemented, rebuilt and independently verified. |

## QV2-DEC-019 - Partial Evidence Cannot Satisfy A Complete Scientific Contract

| Field | Record |
|---|---|
| Problem | Several aggregate checks accepted a partly valid object: incomplete correlations, explicit-null fill bounds, omitted CLI policy values or partly finite chart frames. |
| Evidence | Synthetic fixtures passed one valid pair/value while retaining an invalid or absent companion value. |
| Why it matters | A single valid element does not validate a full feature, OOS protocol, missing-data operation or chart. |
| Affected system | Stock scoring, walk-forward CLI, missing-data AST audit and visual analytics validation. |
| Previous method | Aggregate `any`/syntax-presence checks and orchestration defaults. |
| Candidate methods | Warning-only partial evidence; complete predicate over every required element; silent row deletion. |
| Alternative 1 | Keep partial evidence with a warning. |
| Why rejected | Incomparable scores and partly corrupted visuals can still affect selection or interpretation. |
| Alternative 2 | Silently delete invalid rows. |
| Why rejected | It changes the sample and can conceal a data failure. |
| Chosen method | Require complete pairwise/finite/type validity, exact configured policy forwarding and exact reviewed bounds/call sites. |
| Why chosen | Scientific validity is conjunctive across every required observation and policy input. |
| Mathematical basis | Boolean conjunction over required elements; no positive score from undefined dependence evidence. |
| Statistical basis | Pairwise missingness and selective finite subsets can change estimands and comparability. |
| Financial/economic basis | Incomplete covariance, cost or exposure inputs can alter holdings and risk interpretation. |
| Book support | The financial-statistics and ML sources require consistent samples, explicit preprocessing and train/test protocol. |
| Academic support | Complete-case disclosure, leakage prevention and fail-closed model governance. |
| Assumptions | Required fields and call-site policy are enumerated prospectively. |
| Parameters | Positive finite fill bounds, exact call-site fingerprints and complete finite/type checks. |
| Sensitivity | Any invalid required element rejects the affected feature, operation or chart. |
| Expected impact | Partial corruption never receives a passing aggregate label. |
| Observed impact | Adversarial partial-correlation, fill-limit, zero-reindex, NaN, Boolean and exposure fixtures are rejected; clean evidence passes. |
| Validation | Deterministic unit fixtures, 408-operation source audit and 157-check artifact validator. |
| Invalidation conditions | Any aggregate check proves only one valid element, a config value is not forwarded or an unregistered fill is accepted. |
| Residual limitation | Complete current-sample checks do not solve structural PIT/survivorship limitations. |
| Status | Implemented, rebuilt and independently verified. |
