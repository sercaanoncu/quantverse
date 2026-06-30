# QuantVerse Master Project Plan

This document is the permanent planning source of truth for the QuantVerse
roadmap. It is not implementation evidence, investment advice or a performance
claim. Future sprints should use this document to decide what is in scope, what
is blocked, what must not be claimed and how success must be proven.

## Final Product Definition

QuantVerse is a scientifically audited, evidence-gated and explainable
quantitative portfolio research system. The final product should produce
portfolio candidates, test those candidates against benchmarks and blockers, and
label each result as `promoted`, `not promoted`, `diagnostic only`,
`research only` or `blocked`.

| Engine | Purpose | Inputs | Outputs | Validation Rules | Failure Modes | Acceptance Criteria |
|---|---|---|---|---|---|---|
| Data Source Engine | Track provider, source URL and as-of evidence. | Source CSVs, provider metadata, source docs. | Source registry and validation reports. | Source URL, provider and as-of date required for sourced rows. | Fake source, stale source, duplicate source. | Every row is sourced or explicitly marked proxy/manual review. |
| Universe Construction Engine | Build global equities, crypto, commodities, bonds, bills and cash proxy universes. | Sourced universe files and config. | Current and dated universe files. | Required schema, investable/signal-only/include flags. | Fake top-100 rows, missing sleeve rows. | Every requested sleeve is populated or explicitly blocked. |
| Exact/Proxy Classification Engine | Separate exact top-100, index proxy and manual-review proxy rows. | Universe metadata and source evidence. | Exact/proxy classification report. | Exact claim requires market-cap/rank evidence. | Proxy described as exact top-100. | Every sleeve has visible exact/proxy/manual-review status. |
| FX and Currency Normalization Engine | Convert non-USD local returns into USD base returns. | Local simple returns, FX series, calendars. | USD return matrix and FX audit. | Correct simple-return compounding and calendar alignment. | Mixed-currency performance, wrong base currency. | Non-USD assets are converted or global USD promotion is blocked. |
| Price and Return Engine | Prepare adjusted prices, simple returns and log returns. | Prices, universe, FX policy. | Price matrix, simple returns, log returns. | Adjusted-price assumptions, finite returns, frequency consistency. | Missing data treated as zero, split/dividend distortion. | Simple returns for portfolios; log returns for diagnostics. |
| Data-Quality Engine | Detect coverage, missingness, duplicates and outliers. | Universe, prices, returns. | Coverage, dropped-asset and outlier reports. | Missingness thresholds, duplicate ticker checks, extreme return flags. | Silent drops, stale prices, outlier success claims. | Dropped assets and red flags are visible. |
| Statistical Diagnostics Engine | Test normality, stationarity and covariance sanity. | Returns and metadata. | Normality, stationarity and covariance outputs. | Correct test-to-question mapping; no predictability overclaim. | Diagnostics treated as proof of alpha. | Diagnostics are labeled as diagnostics. |
| Clustering and Factor Diagnostics Engine | Explain correlation structure, clusters and PCA concentration. | Returns, correlations, metadata. | Cluster membership, cluster diagnostics, PCA summary. | Deterministic clustering and cluster-count rationale. | Unstable clusters used as allocation proof. | Cluster outputs are diagnostic unless separately validated. |
| Portfolio Optimization Engine | Build benchmark and constrained candidate portfolios. | Returns, covariance, metadata, constraints. | Weight files and model comparison tables. | Weight sum = 1, long-only default, cap checks, feasible optimizer. | Negative weights, cap breach, infeasible optimizer hidden. | Every full portfolio passes a weight audit or is rejected. |
| Risk Management Engine | Measure volatility, drawdown, VaR, CVaR and stress impacts. | Returns, weights, scenarios. | Risk, tail-risk and stress reports. | Sign conventions, tail visibility, scenario labels. | Tail risk hidden behind return metrics. | Risk is visible before promotion. |
| Forecasting and ML Diagnostics Engine | Run ML/time-series diagnostics without treating weak forecasts as allocation evidence. | Features, returns, labels, splits. | Forecast metrics, ML diagnostics, model status. | Metric-task compatibility, chronological validation, leakage checks. | Weak AUC/R2 overclaimed as trading signal. | ML remains diagnostic unless strict gates pass. |
| Simulation and Projection Engine | Produce Monte Carlo and scenario projection ranges. | Returns, weights, assumptions. | Projection percentiles and scenario outputs. | Reproducible seeds and stated assumptions. | Projection presented as certainty. | Projection is labeled probabilistic and non-advisory. |
| Backtesting and Walk-Forward Validation Engine | Evaluate strategies chronologically out of sample. | Dated universe, returns, constraints, costs. | Walk-forward returns, weights, turnover and cost reports. | No look-ahead, no survivorship overclaim, same dates and universe. | Current constituents used as historical evidence. | No model promotion without chronological evidence. |
| Promotion Gate and Model League Engine | Decide whether a candidate can be promoted for a named universe. | Metrics, risks, costs, blockers, random benchmark. | Promotion gate and model league summary. | Return + risk + cost + robustness + data blockers. | One-metric victory claims. | Every decision names universe and evidence layer. |
| Explainable Reporting Engine | Convert evidence into readable interpretation. | Audit outputs, model outputs, diagnostics. | Turkish PDF, HTML, presentation and captions. | Blockers before performance, charts before tables. | Raw table dump, hidden blockers. | Reader can find weights, blockers and decision. |
| Excel/PDF/HTML Output Engine | Deliver user-facing artifacts. | Reports and tables. | START_HERE workbook, PDFs, HTML. | Required sheets, source captions, full weights. | Only top holdings visible. | Full weights and red flags are easy to find. |
| Audit and Governance Engine | Enforce no-overclaim research discipline. | Tests, reports, logs, red-team review. | Failure taxonomy, audit docs, red-team review. | No fake data, no unsupported claims, reproducible validation. | Marketing language or hidden limitations. | Claims match evidence and blockers. |

## Current State Assessment

| Area | Classification | Current Evidence | Trust Decision |
|---|---|---|---|
| ETF/multi-asset pipeline | Reliable now for research | Existing pipeline, tests and PDF/HTML outputs. | Research-grade, not production trading. |
| Current global proxy research candidate | Research-only | Current decision is `not promoted`. | Valid candidate output, not a promoted global USD portfolio. |
| Real stock/proxy universe | Partially reliable | Real stock/proxy rows exist. | Real/proxy distinction must remain visible. |
| Source coverage | Partially reliable | Source files and source coverage outputs exist. | Needs provider-grade source validation. |
| Market-cap/rank coverage | Blocked | Equity market-cap/rank evidence is incomplete. | Exact top-100 claims unsupported for many equity sleeves. |
| FX normalization | Blocked | Status is `local_currency_mixed_not_promotable`. | Hard blocker for global USD promotion. |
| Simple/log returns | Partially reliable | Policy docs and return outputs exist. | Must be rebuilt after FX normalization. |
| Normality/stationarity | Research-only | Diagnostic outputs exist. | Cannot prove predictability. |
| Covariance estimators | Partially reliable | Estimator comparison outputs exist. | Unstable covariance remains a red flag. |
| Clustering/PCA | Diagnostic-only | Cluster and PCA outputs exist. | Not promotion evidence by itself. |
| Portfolio models | Partially reliable | Equal Weight, Inverse Volatility, Min Variance, Max Sharpe, Min CVaR and Policy Constrained outputs exist. | Model status must remain explicit. |
| HRP/Risk Parity/Black-Litterman | Mixed or blocked | Model applicability outputs exist. | Black-Litterman is blocked by missing market-cap priors; HRP/Risk Parity must not be shown as run unless actually run. |
| Random portfolios | Reliable as benchmark | Random benchmark outputs exist. | Benchmark only; not proof of future superiority. |
| Monte Carlo/projections | Research-only | Projection outputs exist. | Scenario ranges only. |
| Stress tests | Partially reliable | Stress outputs exist. | More valuable after corrected returns. |
| ML diagnostics | Diagnostic-only | Forecast and classification outputs exist. | Not an allocation signal. |
| PDF/Excel outputs | Reliable reporting baseline | Visual report and START_HERE workbook exist. | Baseline should be protected against regression. |
| Promotion language | Improved but must be enforced | Report says `not promoted` and names blockers. | Future outputs must always name universe and evidence layer. |

## Full User Requirement Map

| # | Requirement | Current Status | Evidence Needed | Blocker | Sprint | Acceptance Criterion |
|---:|---|---|---|---|---:|---|
| 1 | Real stocks enter analysis. | Met | Universe and weights. | Point-in-time membership missing. | 0/4 | Real rows visible with source labels. |
| 2 | NASDAQ top-100 or proxy. | Partial | Market-cap/rank source. | Exact rank missing. | 2/3 | Exact or proxy flag visible. |
| 3 | NYSE top-100 or proxy. | Partial | Exchange-filtered rank. | Pure NYSE rank missing. | 2/3 | Exact/proxy visible. |
| 4 | Europe top-100 or proxy. | Partial | Rank/cap evidence. | Broad proxy. | 2/3 | Source-qualified. |
| 5 | Germany top-100 or proxy. | Partial | Rank/cap evidence. | Proxy. | 2/3 | Source-qualified. |
| 6 | UK top-100 or proxy. | Partial | Rank/cap evidence. | Proxy. | 2/3 | Source-qualified. |
| 7 | BIST top-100 / BIST 100 distinction. | Partial | BIST source. | Index vs cap-rank distinction. | 2/3 | Distinction explicit. |
| 8 | Japan top-100 or proxy. | Partial | Rank/cap evidence. | Proxy. | 2/3 | Source-qualified. |
| 9 | China/HK top-100 or proxy. | Partial | Rank/cap evidence. | Accessible-listing ambiguity. | 2/3 | Source-qualified. |
| 10 | Gold, silver, oil, platinum and copper. | Met as proxy | Commodity source. | Spot/futures/proxy mismatch. | 0 | Proxy type visible. |
| 11 | Crypto top 100. | Partial/met | Crypto rank source. | Stablecoin filtering and ticker mapping. | 2/6 | Top crypto rows sourced and flagged. |
| 12 | Bonds, bills and cash proxies. | Met as proxy | Proxy source. | ETF/bill distinction. | 0 | Proxy type visible. |
| 13 | Source URL, provider and as-of date for every row. | Partial | Source registry. | Missing fields. | 2 | No sourced row without source fields. |
| 14 | Exact top-100 versus index proxy versus manual-review proxy. | Partial/met | Classification report. | Inconsistent labels. | 3 | Every row classified. |
| 15 | Market-cap/rank evidence for exact top-100 claims. | Blocked | Cap/rank file. | Missing equity caps. | 2 | Exact claim impossible without evidence. |
| 16 | FX-normalized global USD returns. | Blocked | FX series and conversion report. | No FX engine. | 1 | All non-USD converted or blocked. |
| 17 | Simple returns for portfolio aggregation. | Partial | Return policy and tests. | Rebuild after FX. | 6 | Weighted simple returns tested. |
| 18 | Log returns for diagnostics/time aggregation. | Partial | Log-return matrix. | Rebuild after FX. | 6/7 | Diagnostics use log returns where appropriate. |
| 19 | Normality diagnostics. | Met/diagnostic | Output CSV. | Assumption overclaim. | 7 | Labeled diagnostic. |
| 20 | Stationarity diagnostics. | Met/diagnostic | Output CSV. | Assumption overclaim. | 7 | Labeled diagnostic. |
| 21 | Covariance estimator comparison. | Partial | Estimator comparison. | Instability. | 7 | PSD/condition tests. |
| 22 | Correlation clustering. | Met/diagnostic | Cluster membership. | Unstable clusters. | 7 | Deterministic cluster report. |
| 23 | Region/sleeve clustering. | Partial | Metadata grouping. | Incomplete metadata. | 7 | Exposure sums reconcile. |
| 24 | Cluster count justification. | Partial | Elbow/silhouette report. | Subjective choice. | 7 | Method documented. |
| 25 | Holdings per cluster. | Partial | Cluster weight table. | Concentration. | 8 | Cap and min/max rules pass. |
| 26 | PCA/factor diagnostics. | Met/diagnostic | PCA output. | Overinterpretation. | 7 | Variance chart plus warning. |
| 27 | Weight sum = 1 for all full portfolios. | Met | Weight audit. | Model-specific drift. | 0/8 | Every full portfolio within tolerance. |
| 28 | Long-only unless shorting is explicit. | Met | Constraint audit. | Optimizer exception. | 8 | Negative weights blocked. |
| 29 | Negative weights blocked unless shorting is allowed. | Met | Constraint audit. | Shorting ambiguity. | 8 | No negatives unless configured. |
| 30 | Max-weight caps. | Met | Constraint audit. | Cap drift. | 8 | Cap checked. |
| 31 | Asset-class caps. | Partial | Exposure audit. | Config gaps. | 8 | Cap policy explicit. |
| 32 | Region caps. | Partial | Region weights. | FX/source issues. | 8 | Cap policy explicit. |
| 33 | Cluster caps. | Partial | Cluster weights. | Cluster instability. | 8 | Cap policy explicit. |
| 34 | Dust weights disclosed. | Met | Weight audit. | Operational noise. | 0/12 | Dust count visible. |
| 35 | Risk minimization and return maximization separated. | Partial | Model league. | Mixed claims. | 11 | Separate leagues. |
| 36 | Equal Weight benchmark. | Met | Model comparison. | Benchmark mismatch. | 8/10 | Same universe and dates. |
| 37 | Random portfolio benchmark. | Met | Random benchmark. | Not future proof. | 10/11 | Percentile used in gate. |
| 38 | Markowitz/Min Variance/Max Sharpe. | Partial | Model comparison. | Expected-return fragility. | 8 | Diagnostic unless OOS robust. |
| 39 | Min CVaR. | Partial | Risk report. | Tail-estimation limits. | 8 | CVaR method documented. |
| 40 | HRP. | Blocked/partial | Actual run proof. | Not available in global path. | 8 | Shown only if actually run. |
| 41 | Risk Parity. | Blocked/partial | Actual run proof. | Not available in global path. | 8 | Shown only if actually run. |
| 42 | Black-Litterman. | Blocked | Market-cap priors. | Missing caps/views. | 2/8 | No BL evidence without priors. |
| 43 | Robust/convex optimization where justified. | Future | Assumptions/tests. | Overengineering. | 8/13 | Only if data supports it. |
| 44 | Monte Carlo simulation. | Met/research | Projection files. | False certainty. | 12 | Confidence bands labeled. |
| 45 | Stress testing. | Met/partial | Stress outputs. | Scenario assumptions. | 7/12 | Source and scenario described. |
| 46 | Scenario analysis. | Partial | Scenario outputs. | Weak assumptions. | 12 | Scenario meaning explicit. |
| 47 | Forward projections. | Research-only | Projection files. | No forecast guarantee. | 12 | Not-advice language. |
| 48 | Train/test validation. | Partial | ML/backtest split. | Missing global walk-forward. | 9/10 | Chronological split. |
| 49 | Walk-forward validation. | Blocked/partial | Walk-forward outputs. | Point-in-time missing. | 10 | No promotion without WF. |
| 50 | Rolling windows. | Partial | Rolling outputs. | Window choice. | 10 | Window documented. |
| 51 | Random walk benchmark. | Future | Baseline model. | Not implemented. | 9/10 | Forecasts compared to naive. |
| 52 | ARMA/ARIMA/SARIMA only where assumptions fit. | Future/blocked | Stationarity + likelihood. | Misuse risk. | 9 | Diagnostic only unless valid. |
| 53 | GARCH only as volatility diagnostic unless justified. | Future | Volatility model outputs. | Production overclaim. | 9 | Volatility diagnostic only. |
| 54 | Regression metrics only for regression. | Partial/met | Metric audit. | Misuse. | 9 | Tests enforce. |
| 55 | Classification metrics only for classification. | Partial/met | Metric audit. | Misuse. | 9 | Tests enforce. |
| 56 | AIC/BIC only for fitted likelihood models. | Future | Model fit objects. | Misuse. | 9 | Tests enforce. |
| 57 | ML diagnostic discipline. | Met/partial | Model applicability matrix. | Overclaim. | 9 | ML not allocation signal. |
| 58 | LSTM/RNN/RL not production allocation engines unless justified. | Met as policy | Docs. | Hype risk. | 9/13 | Future-only unless strict validation. |
| 59 | Transaction costs. | Partial | Cost fields. | Simplistic costs. | 10/11 | Cost grid. |
| 60 | Outlier handling. | Partial | Outlier report. | Extreme metrics. | 5/6 | Red flags resolved or explained. |
| 61 | Delisting handling. | Blocked | Delisting source. | Survivorship. | 5 | Delisting audit exists. |
| 62 | Corporate-action reconciliation. | Blocked/partial | Adjusted-price audit. | Split/dividend drift. | 5 | Reconciliation report. |
| 63 | No survivorship overclaim. | Partial/met | Proxy labels. | Point-in-time absent. | 4 | Historical claims blocked. |
| 64 | No look-ahead bias. | Partial | Walk-forward tests. | Current constituents. | 4/10 | Decision-time data only. |
| 65 | PDF report understandable. | Met baseline | Visual report. | Future drift. | 12 | Chart-led Turkish report. |
| 66 | Excel workbook starts with START_HERE. | Met | Workbook. | Future drift. | 12 | START_HERE first. |
| 67 | Charts before raw tables. | Met baseline | Report. | Future drift. | 12 | Red-team QA. |
| 68 | Source captions for charts. | Met baseline | Report captions. | Future drift. | 12 | Every chart has source. |
| 69 | Red flags visible. | Met | Red flag dashboard. | Future drift. | 12 | Blockers before performance. |
| 70 | Not-promoted decision explicit. | Met | Decision JSON/report. | Wording drift. | 11/12 | Universe-specific. |
| 71 | Promoted/not promoted specifies universe. | Partial/met | Report text. | Ambiguity. | 11/12 | Every decision names universe. |
| 72 | No investment advice claim. | Met policy | Docs/report. | Language drift. | 12/13 | Banned phrase tests. |
| 73 | No guaranteed outperformance. | Met policy | Docs/report. | Language drift. | 12/13 | Banned phrase tests. |
| 74 | No fake data. | Met policy | Source validation. | Source gaps. | 2/13 | No fabricated rows. |

## Critical Blocker Ranking

| Rank | Blocker | Why It Matters | Methodology Basis | Failure If Ignored | Affected Layers | Exact Fix Required | Tests Required | Acceptance Criteria | Dependencies |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | FX normalization | Global portfolio metrics must use one base currency. | Return aggregation and portfolio math. | Fake USD performance. | FX, returns, portfolio, reports. | FX series, calendar alignment and simple-return compounding. | FX conversion unit/integration tests. | No non-USD unconverted asset in promoted USD portfolio. | Source/currency metadata. |
| 2 | Market-cap/rank evidence | Exact top-100 and Black-Litterman require evidence. | Portfolio priors and source governance. | Fake top-100 and invalid priors. | Universe, source, BL. | Sourced caps/ranks with as-of dates. | Source schema tests. | Exact claim only with rank/cap evidence. | Provider docs. |
| 3 | Point-in-time membership | Avoids survivorship and look-ahead bias. | Backtesting and ML validation. | Historical false winners. | Universe and backtest. | Dated membership tables and rebalance-time lookup. | No-look-ahead tests. | Historical claims only from PIT files. | Market-cap/rank data. |
| 4 | Delistings | Missing failed assets biases history. | Backtesting bias control. | Survivorship bias. | Universe and price ingestion. | Delisting status and handling rules. | Delisting fixture tests. | Delisted assets handled or explicitly blocked. | PIT data. |
| 5 | Corporate actions | Splits/dividends distort returns if mishandled. | Financial data quality. | False jumps or false losses. | Price and returns. | Adjusted-price and corporate-action reconciliation. | Split/dividend sanity tests. | Suspicious jumps reviewed. | Price provider. |
| 6 | Provider/source quality | Outputs must be auditable. | Model governance. | Unverifiable results. | Source registry and reports. | Provider registry and required source fields. | Required-source tests. | No missing source fields for sourced rows. | None. |
| 7 | Ticker mapping | Prevents wrong-security analysis. | Data engineering. | Wrong asset mapped to ticker. | Universe and price ingestion. | Mapping table and ambiguity resolution. | Duplicate/ambiguity tests. | Ambiguous tickers blocked or resolved. | Source registry. |
| 8 | Local currency versus USD return treatment | Same asset can change risk/return after FX conversion. | Return math. | Mixed-currency risk. | Reports and gates. | FX status in every output. | Report schema tests. | Explicit blocker visible. | FX engine. |
| 9 | Data coverage | Optimizers are sensitive to missingness. | Statistical estimation. | Unstable estimates. | Returns and models. | Coverage thresholds and dropped-asset explanations. | Coverage tests. | Dropped assets explained. | Price ingestion. |
| 10 | Outlier handling | Extreme metrics are already red flags. | Risk/statistical diagnostics. | False success claims. | Diagnostics and risk. | Outlier review and red-flag dashboard. | Extreme metric tests. | Red flags not presented as success. | Returns rebuild. |
| 11 | Covariance instability | Risk models depend on covariance quality. | Portfolio optimization. | Unstable weights. | Covariance and optimizers. | PSD and condition-number checks. | Covariance tests. | Unstable covariance -> diagnostic only. | Corrected returns. |
| 12 | Model applicability | Prevents invalid method claims. | Model governance. | Blocked models shown as valid evidence. | Model league and reports. | Status matrix enforcement. | Applicability tests. | Unavailable models not shown as run. | Data prerequisites. |
| 13 | Walk-forward validation | Promotion requires OOS evidence. | Backtesting/ML validation. | Overfit promoted. | Backtest and gate. | Chronological walk-forward engine. | Leakage tests. | No promotion without walk-forward. | PIT and returns. |
| 14 | Reporting clarity | User trust depends on explanation. | Governance and auditability. | Hidden blockers. | PDF/Excel/HTML. | Permanent report contract. | Report tests. | Blockers before metrics. | Audit outputs. |

## Master Architecture Plan

1. Source Registry Layer validates source files, provider, URL, as-of date and source method before universe construction.
2. Universe Population Layer builds sleeve-specific current and dated universes.
3. Exact/Proxy Classification Layer assigns `exact_market_cap_rank`, `index_proxy` or `manual_review_required` and blocks unsupported exact claims.
4. Market-Cap/Rank Enrichment Layer adds market-cap and rank evidence for exact top-100 claims and Black-Litterman priors.
5. FX Normalization Layer converts local simple returns to USD simple returns with calendar alignment.
6. Price Ingestion Layer loads adjusted prices and records provider/cache assumptions.
7. Return Matrix Layer creates simple and log returns with consistent dates and frequency.
8. Data Quality and Coverage Layer flags missingness, stale prices, duplicates, drops and outliers.
9. Outlier and Corporate Action Review Layer separates real market moves from split/dividend/provider errors.
10. Statistical Diagnostics Layer runs normality, stationarity, covariance and tail diagnostics.
11. Clustering and PCA Layer explains correlation clusters, region/sleeve clusters and factor concentration.
12. Forecasting/ML Diagnostic Layer produces regression/classification/time-series diagnostics without allocation overclaim.
13. Portfolio Optimization Layer creates benchmark and constrained candidates only when prerequisites pass.
14. Risk and Tail-Risk Layer computes drawdown, VaR, CVaR, stress and scenario risk.
15. Backtesting and Walk-Forward Layer evaluates strategies chronologically with costs and no leakage.
16. Random Benchmark Layer creates reproducible random portfolios and percentile comparisons.
17. Promotion Gate Layer blocks promotion on data, FX, rank, OOS, cost, risk or robustness failures.
18. Reporting and Explainability Layer creates Turkish chart-led interpretation.
19. Excel/PDF/HTML Output Layer writes user-facing artifacts with full weights and blockers.
20. Governance and Red-Team Layer enforces failure taxonomy, no-overclaim tests and reproducibility discipline.

## Sprint Roadmap

### Sprint 0 - Lock Current Scientific Audit and Visual Explainability Baseline

- Objective: stabilize the current audit/reporting layer.
- Why it matters: future work must not regress clarity.
- Prerequisites: current audit outputs and report baseline.
- Affected files: audit/report scripts, docs and tests.
- Implementation outline: freeze report contract, START_HERE schema, promotion wording tests and red-team checklist.
- Tests: report schema, Excel sheets, no-overclaim strings, PDF smoke where feasible.
- Validation commands: `python -m pytest -q`, `python -m black --check src scripts tests`, `python -m ruff check src scripts tests`, `python -m compileall src scripts`.
- Expected outputs: locked audit report, workbook and red-team document.
- Acceptance criteria: report says `not promoted`, names the universe and exposes blockers.
- What not to do: do not change models or fabricate data.
- Blocker risk: low.
- Complexity: low.
- Internet/current data access: no.
- Local books needed: methodology matrix only.

### Sprint 1 - FX Normalization Engine

- Objective: convert non-USD local returns into USD base returns.
- Why it matters: this is the top blocker for global USD promotion.
- Prerequisites: currency metadata and FX source policy.
- Affected files: global returns module, FX docs, configs and tests.
- Implementation outline: define FX ticker map, align calendars, compound simple returns, write FX audit.
- Tests: USD unchanged, EUR/TRY/JPY/HKD conversion, missing FX blocks promotion.
- Validation commands: focused FX tests plus full pytest.
- Expected outputs: FX-normalized returns and FX status report.
- Acceptance criteria: no promoted USD portfolio with unconverted non-USD returns.
- What not to do: do not infer FX silently.
- Blocker risk: high.
- Complexity: high.
- Internet/current data access: likely yes.
- Local books needed: returns and financial statistics.

### Sprint 2 - Market-Cap/Rank Source Engine

- Objective: add sourced market-cap/rank evidence where possible.
- Why it matters: exact top-100 and Black-Litterman require cap/rank evidence.
- Prerequisites: source registry schema.
- Affected files: source validators, universe source files, docs and configs.
- Implementation outline: add source adapters/templates, cap/rank validation and as-of evidence.
- Tests: exact claim requires cap/rank/source/as-of.
- Expected outputs: market-cap coverage report.
- Acceptance criteria: exact top-100 allowed only for evidenced sleeves.
- What not to do: do not fabricate ranks or caps.
- Blocker risk: high.
- Complexity: high.
- Internet/current data access: yes.
- Local books needed: portfolio theory and data governance.

### Sprint 3 - Exact Top-100 versus Proxy Enforcement

- Objective: enforce exact/proxy/manual-review labels.
- Why it matters: prevents misleading claims.
- Prerequisites: Sprint 2 partial or complete.
- Implementation outline: hard gates in universe builder and reports.
- Tests: exact without cap/rank fails; proxy remains allowed as research.
- Acceptance criteria: all reports show exact/proxy by sleeve.
- Complexity: medium.
- Internet/current data access: no unless refreshing sources.
- Local books needed: no.

### Sprint 4 - Point-In-Time Universe Framework

- Objective: prevent current constituents from being used as historical evidence.
- Why it matters: avoids survivorship and look-ahead bias.
- Prerequisites: dated universe schema.
- Implementation outline: add as-of membership tables, effective-date logic and historical labels.
- Tests: rebalance date sees only prior membership.
- Acceptance criteria: no historical stock-selection claim without PIT files.
- Complexity: high.
- Internet/current data access: likely yes.
- Local books needed: backtesting and ML validation sources.

### Sprint 5 - Delisting, Corporate Action and Data Quality Reconciliation

- Objective: improve adjusted prices, delisting treatment, split/dividend handling, ticker mapping and provider reconciliation.
- Why it matters: backtests are biased without lifecycle and action handling.
- Implementation outline: add delisting status, split/dividend sanity checks and ticker ambiguity resolution.
- Tests: delisted fixture, split jump fixture, duplicate ticker fixture.
- Acceptance criteria: data-quality report separates data errors from real outliers.
- Complexity: high.
- Internet/current data access: yes.
- Local books needed: financial data/statistical validation.

### Sprint 6 - Rebuild Global Returns After FX and Data Fixes

- Objective: regenerate global simple returns, log returns, coverage reports, outlier reports and FX status.
- Why it matters: all later models depend on corrected returns.
- Tests: simple/log consistency, finite returns and aligned dates.
- Acceptance criteria: FX status clean or explicit blocker.
- Complexity: medium.
- Internet/current data access: maybe.
- Local books needed: returns and time-series rules.

### Sprint 7 - Statistical Diagnostics Rebuild

- Objective: rerun normality, stationarity, covariance, PCA, clustering and tail-risk diagnostics after corrected returns.
- Why it matters: current diagnostics are based on blocked return layer.
- Tests: output schemas, covariance PSD/condition and deterministic clustering.
- Acceptance criteria: diagnostics are labeled and red flags visible.
- Complexity: medium.
- Internet/current data access: no.
- Local books needed: statistics, econometrics and portfolio optimization.

### Sprint 8 - Portfolio Optimization Revalidation

- Objective: rerun Equal Weight, Inverse Volatility, Min Variance, Max Sharpe, Min CVaR, HRP, Risk Parity, Black-Litterman and policy-constrained candidates only where prerequisites are satisfied.
- Why it matters: portfolio evidence must not come from invalid inputs.
- Tests: weights sum, long-only, caps, optimizer infeasibility fallback and model availability.
- Acceptance criteria: Black-Litterman only runs with cap priors; HRP/Risk Parity appear as run only when actually executed.
- Complexity: medium/high.
- Internet/current data access: no if corrected inputs exist.
- Local books needed: portfolio optimization.

### Sprint 9 - Forecasting and ML Diagnostic Governance

- Objective: keep ML/time-series outputs diagnostic unless strict validation supports use.
- Why it matters: weak forecasts must not become allocation signals.
- Tests: metric-task compatibility, random-walk benchmark and leakage guard.
- Acceptance criteria: regression/classification/AIC/BIC used only in valid contexts.
- Complexity: medium.
- Internet/current data access: no.
- Local books needed: ISLR, ML finance and econometrics.

### Sprint 10 - Walk-Forward and Out-of-Sample Global Validation

- Objective: evaluate strategies chronologically with costs, constraints, no look-ahead and no survivorship overclaim.
- Why it matters: promotion requires out-of-sample evidence.
- Tests: no-look-ahead synthetic tests, date alignment, turnover and cost grid.
- Acceptance criteria: every promoted model has walk-forward evidence.
- Complexity: high.
- Internet/current data access: maybe.
- Local books needed: backtesting and ML validation.

### Sprint 11 - Promotion Gate and Model League

- Objective: define and enforce broad default, return challenger, defensive candidate, diagnostic and rejected labels.
- Why it matters: one model should not be called best for every objective.
- Tests: gate blockers, allowed labels and universe-specific decisions.
- Acceptance criteria: promotion cannot ignore FX/source/OOS blockers.
- Complexity: medium.
- Internet/current data access: no.
- Local books needed: governance and validation principles.

### Sprint 12 - Final Product Reporting and User Experience

- Objective: produce final PDF, Excel, HTML and presentation outputs that explain data, methods, weights, risks, blockers and decisions.
- Why it matters: non-expert readers must understand the evidence.
- Tests: required sheets, captions, chart/source checks, no raw-table-first, PDF smoke.
- Acceptance criteria: full weights visible; blockers before metrics; no advice language.
- Complexity: medium.
- Internet/current data access: no.
- Local books needed: no, unless methodology text changes.

### Sprint 13 - Institutional-Grade Hardening

- Objective: prepare packaging, reproducibility, config discipline, data contracts, documentation and optional vendor integration.
- Why it matters: clean GitHub/research/interview credibility.
- Tests: clean-clone validation, no local paths, generated outputs excluded.
- Acceptance criteria: reproducible local run and clean docs.
- Complexity: medium/high.
- Internet/current data access: maybe.
- Local books needed: no.

## Dependency Graph

- FX normalization must precede global USD promotion.
- Market-cap/rank evidence must precede exact top-100 claims.
- Market-cap/rank evidence must precede Black-Litterman market-cap priors.
- Point-in-time constituents must precede historical stock-selection claims.
- Delisting and corporate-action reconciliation must precede institutional-grade backtests.
- Corrected FX-normalized returns must precede diagnostics rebuild.
- Corrected diagnostics must precede optimizer revalidation.
- Optimizer revalidation, costs and random benchmarks must precede promotion gate decisions.
- Walk-forward validation must precede promoted model league status.
- Audit outputs must precede final PDF/Excel/HTML reporting.
- Red-team review must precede final release or hardening claims.

## Model Governance Plan

| Method | Current Status | Required Inputs | Valid Metrics | Invalid Misuse | Promotion Requirements | User-Facing Report Status |
|---|---|---|---|---|---|---|
| Equal Weight | Benchmark now. | Returns. | CAGR, Sharpe, drawdown, CVaR. | Proof of superiority. | Same universe, dates and costs. | Yes. |
| Random portfolios | Benchmark now. | Returns and constraints. | Percentile, Sharpe/CAGR distribution. | Proof of future superiority. | Reproducible seed and same constraints. | Yes. |
| Markowitz | Diagnostic/conditional. | Expected returns and covariance. | OOS return/risk. | In-sample optimum as proof. | Walk-forward and stable estimates. | Yes with warning. |
| GMV/Min Variance | Defensive candidate. | Covariance. | Volatility, drawdown, CVaR. | Return champion claim. | Covariance sanity and OOS checks. | Yes. |
| Max Sharpe | Diagnostic. | Expected returns and covariance. | OOS Sharpe. | Expected-return overclaim. | Robust OOS and bootstrap evidence. | Yes with warning. |
| Inverse Volatility | Allowed candidate. | Return volatility. | Sharpe and drawdown. | Return maximization proof. | Cost, OOS and risk gates. | Yes. |
| Min CVaR | Tail-risk candidate. | Sufficient tail data. | CVaR and drawdown. | Precise tail guarantee. | Tail diagnostics and OOS checks. | Yes. |
| HRP | Conditional. | Returns/correlation. | Risk and drawdown. | Highest-return claim. | Actually run and OOS validated. | Yes if run. |
| Risk Parity | Conditional. | Covariance/risk model. | Risk contribution. | Return proof. | Actually run and risk audit. | Yes if run. |
| Black-Litterman | Blocked by data. | Market-cap priors and documented views. | Posterior weights and risk. | Fake priors or hindsight views. | Sourced caps and documented views. | Only as blocked until fixed. |
| Robust/convex optimization | Future. | Uncertainty sets and constraints. | Robustness metrics. | Complexity theater. | Justified assumptions. | Limited. |
| PCA | Diagnostic. | Returns. | Explained variance. | Alpha model alone. | Stability checks. | Yes as diagnostic. |
| Clustering | Diagnostic. | Correlations and metadata. | Cluster stats. | Promotion proof. | Stable cluster policy. | Yes as diagnostic. |
| Monte Carlo | Research projection. | Returns and weights. | Percentiles. | Forecast certainty. | Assumptions visible. | Yes. |
| Stress/scenario | Risk tool. | Shocks and weights. | Impact and drawdown. | Probability claim. | Scenario rationale. | Yes. |
| ARMA/ARIMA/SARIMA | Future diagnostic. | Stationary fitted series. | AIC/BIC and forecast error. | Allocation proof. | Fitted likelihood and OOS tests. | Limited. |
| GARCH | Future volatility diagnostic. | Returns. | Volatility forecast error. | Return prediction. | Volatility validation. | Limited. |
| Linear/ridge/lasso | Diagnostic/future. | Features and labels. | Regression metrics. | Allocation proof. | No leakage and walk-forward. | Limited. |
| Logistic/tree/RF/GB/XGBoost | Diagnostic/future. | Labels and features. | AUC, confusion, calibration. | Market certainty. | Purged or walk-forward validation. | Limited. |
| LSTM/RNN/RL | Not appropriate now. | Large validated PIT data. | Strict OOS metrics. | Production allocation engine. | Institutional validation. | No, roadmap only. |
| LLM allocation agent | Not appropriate. | Governed text system. | None for allocation. | Autonomous portfolio manager. | Not in current scope. | No, only research assistant role. |

## Data Governance Plan

Every asset/security row must define:

- `ticker`
- `name`
- `sleeve`
- `region`
- `country`
- `exchange`
- `currency`
- `asset_type`
- `sector`
- `industry`
- `market_cap_usd`
- `market_cap_rank`
- `source_url`
- `source_name`
- `source_method`
- `as_of_date`
- `exact_proxy_status`
- `investable`
- `signal_only`
- `price_source`
- `price_coverage_status`
- `fx_normalization_status`
- `corporate_action_status`
- `delisting_status`
- `notes`

Permanent data validation rules:

- No sourced row without source URL, provider and as-of date.
- No exact top-100 claim without market-cap/rank evidence.
- No global USD promotion with non-USD unconverted returns.
- No silent price-coverage drops.
- No stablecoins in risk allocation unless explicitly configured.
- No duplicate ticker ambiguity without resolution.
- No current constituent file used as historical point-in-time evidence.
- No missing adjusted-price assumption.

## Reporting Standard

- Turkish summary first.
- Excel `START_HERE` sheet first.
- Executive summary before metrics.
- Blockers before model performance.
- Charts before raw tables.
- Every chart answers: `Ne goruyorum?`, `Neden onemli?`, `Kirmizi bayrak ne?`, `Hangi karari destekliyor?`, `Kaynak dosya ne?`.
- Full weights are always available.
- Top holdings are clearly labeled as partial.
- `promoted` / `not promoted` always specifies universe.
- Exact top-100 versus proxy status is always visible.
- Blocked, unavailable and diagnostic models are never shown as executed allocation evidence.
- Suspicious metrics are flagged, not hidden.
- No investment advice language.
- No guaranteed outperformance language.

## Testing and Validation Standard

| Test Type | Prevents | Expected Location | Command |
|---|---|---|---|
| Unit tests | Local math/function bugs. | `tests/` | `python -m pytest -q` |
| Integration tests | Broken pipeline contracts. | `tests/` | `python -m pytest -q` |
| Data-contract tests | Schema drift. | Universe/source tests. | `python -m pytest -q` |
| Source schema tests | Fake or incomplete source rows. | Source validation tests. | `python -m pytest -q` |
| FX conversion tests | Currency math errors. | FX tests. | `python -m pytest -q` |
| Returns math tests | Simple/log misuse. | Returns tests. | `python -m pytest -q` |
| Covariance tests | Non-PSD or ill-conditioned covariance use. | Covariance tests. | `python -m pytest -q` |
| Diagnostics tests | Missing normality/stationarity outputs. | Diagnostics tests. | `python -m pytest -q` |
| Weight tests | Invalid portfolios. | Portfolio invariant tests. | `python -m pytest -q` |
| Model applicability tests | Invalid model claims. | Model tests. | `python -m pytest -q` |
| Metric-task tests | Wrong ML metrics. | ML tests. | `python -m pytest -q` |
| Leakage tests | Look-ahead and same-period leakage. | Walk-forward tests. | `python -m pytest -q` |
| Report schema tests | Missing sheets/captions. | Report tests. | `python -m pytest -q` |
| PDF smoke tests | Unreadable PDF. | Report QA scripts/tests. | Render first page when PDF changes. |
| Generated-output tests | Dirty commits. | Git status checks. | `git status --short --branch` |
| Local-path tests | Nonportable files. | Hygiene tests. | `python -m pytest -q` |

Standard validation stack:

```powershell
python -m black src scripts tests
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
git status
```

## Definition of Done Levels

| Level | Meaning | Requirements | Allowed Claims | Forbidden Claims |
|---|---|---|---|---|
| Level 0 - Prototype | Scripts run locally. | Basic outputs. | Exploratory prototype. | Reliable portfolio. |
| Level 1 - Reproducible Research Pipeline | Deterministic tests and configs. | Tests, docs, no fake data. | Reproducible research pipeline. | Institutional-grade system. |
| Level 2 - Audit-Ready Research System | Source/audit/reporting clear. | Red flags, START_HERE, model status. | Audited research candidate. | Promoted global USD portfolio. |
| Level 3 - Global USD Research Candidate | FX-normalized current universe. | FX, source and quality reports. | USD research candidate. | Historical top-100 proof. |
| Level 4 - Promotable Global USD Master Portfolio | OOS and gates pass. | PIT, costs, walk-forward, risk, random benchmark. | Promoted for a specified universe and evidence layer. | Guaranteed returns or advice. |
| Level 5 - Institutional-Grade Research Platform | Vendor-grade lineage and governance. | Delistings, corporate actions, approvals, monitoring. | Institutional research platform. | Production execution unless explicitly built. |

## Permanent Context Engineering Protocol

Every future Codex sprint prompt should include:

- mission
- current branch
- source-of-truth files
- user requirement being addressed
- what not to do
- methodology basis
- implementation phases
- tests
- validation commands
- output contract
- commit rules
- final response requirements
- red-team checklist

Prompt template:

```text
You are Codex. Repository: [path]. Branch: [branch].
Mission: [one sprint objective].
Source of truth: [files].
User requirement addressed: [requirement IDs].
Do not: [forbidden actions].
Methodology basis: [books/docs/rules].
Implementation phases: [phases].
Tests required: [tests].
Validation commands: [commands].
Outputs: [expected files].
Commit rule: commit source/docs/tests only; do not push; do not commit generated outputs.
Final response must include: branch, files, behavior, tests, outputs, blockers, commit hash, next command.
Red-team checklist: [overclaim/data/FX/model/report checks].
```

## Next Best Action

Sprint 0.1 should save this roadmap as the permanent source-of-truth document.
After Sprint 0.1, the next implementation sprint should be Sprint 1 - FX
Normalization Engine, unless Sprint 0 baseline locking still needs cleanup.

FX should come before market-cap/rank work because even perfect market-cap
evidence cannot make a global USD portfolio promotable while local-currency
returns remain unconverted. Market-cap/rank work remains the second major
blocker because it is required for exact top-100 claims and Black-Litterman
priors.

Recommended next approval phrase:

```text
APPROVED: IMPLEMENT SPRINT 1 - FX Normalization Engine
```

## Implementation Guardrail

This roadmap is a planning document. It does not implement Sprint 1, does not
claim global USD promotion, does not fabricate data and does not provide
investment advice.

To implement a future sprint, the user must explicitly write:

```text
APPROVED: IMPLEMENT SPRINT [number] - [sprint name]
```
