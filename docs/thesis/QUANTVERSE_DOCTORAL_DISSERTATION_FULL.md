# QuantVerse Doctoral Dissertation Full

This full manuscript is generated from the committed QuantVerse v2 engine, local methodology mapping and current public-data outputs. It is not investment advice, does not claim official exact top-100 support and does not claim institutional point-in-time validation.

## Current Engine Snapshot

- Run status: `completed`
- Universe rows: `600`
- Assets with USD returns: `589`
- Stocks scored: `589`
- Stocks selected: `40`
- Final selected model: `Policy Constrained`
- Walk-forward status: `completed_public_data_current_universe`
- Promotion decision: `not promoted`

## Base Dissertation

# QuantVerse: Çok Varlıklı, Kaynak Kanıtlı ve Evidence-Gated Küresel Portföy Araştırma Sistemi

Author: Sercan Öncü  
Project type: doctoral-dissertation-style research output  
Repository path: local QuantVerse checkout; generated artifacts are written
under `output/thesis/`.  
Branch: `integrate-fx-marketcap-gates`  
Date: 2026-07-02  
Disclaimer: Bu çalışma yatırım tavsiyesi değildir. Bulgular araştırma,
doğrulama ve metodoloji değerlendirmesi amacı taşır.
Current promotion decision: global USD master portfolio is not promoted.
The active decision layer now uses sourced current candidate equity inputs, but
it still reports `not promoted` because exact top-100, point-in-time,
delisting/corporate-action and walk-forward evidence gates remain unresolved.

## Table of Contents

1. Turkish Abstract
2. English Abstract
3. Extended Executive Summary
4. Research Problem and Motivation
5. Research Questions
6. Contribution Statement
7. Literature and Methodology Basis
8. Data and Source Governance
9. FX Normalization Methodology
10. Market-Cap/Rank Evidence Methodology
11. Portfolio Construction Methodology
12. Risk and Statistical Diagnostics
13. Model Governance
14. System Architecture
15. Experimental Pipeline and Reproducibility
16. Results
17. Discussion
18. Validity Threats and Limitations
19. Red-Team Review
20. Conclusion
21. Future Work
22. References
23. Appendices

## Notation and Glossary

| Term | Meaning |
|---|---|
| Evidence gate | Bir iddianın kabul edilmeden önce veri, yöntem, risk ve doğrulama koşullarından geçmesi. |
| Promotion | Belirli bir evren ve kanıt katmanı için aday portföyün desteklenebilir sonuç olarak işaretlenmesi. |
| Not promoted | Adayın üretildiği, fakat kanıt kapılarından geçmediği durum. |
| Proxy | Doğrudan hedef varlığı değil, ona yaklaşık maruz kalımı temsil eden araç. |
| Exact top-100 | Kaynaklı, tarihli ve market-cap/rank kanıtı olan ilk 100 iddiası. |
| Local return | Varlığın kendi işlem para birimindeki getiri. |
| USD return | FX dönüşümü sonrası ABD doları bazlı getiri. |
| CVaR | Belirli güven düzeyinde kuyruk kaybının ortalama şiddeti. |
| Black-Litterman prior | Piyasa ağırlığı veya benzeri kanıtla türetilen önsel getiri/risk görüşü. |

## 1. Turkish Abstract

Bu çalışma QuantVerse adlı çok varlıklı portföy araştırma sistemini doktora
tezi formatına yakın bir akademik araştırma çıktısı olarak değerlendirir.
Araştırmanın temel problemi, küresel hisse senedi, emtia, kripto ve defansif
varlık evrenlerinden portföy adayı üretirken veri kaynağı, para birimi,
market-cap/rank kanıtı, model uygunluğu ve raporlama açıklanabilirliği
blokajlarının saklanmamasıdır. Çalışma, "başarılı portföy" iddiasını yalnızca
getiriyle değil, kaynak kanıtı, FX normalizasyonu, kısıt geçerliliği, risk
metrikleri, random benchmark, Equal Weight karşılaştırması, model governance ve
bilimsel sanity audit sonuçlarıyla değerlendirir.

Mevcut kanıt katmanı global USD master portfolio için promosyon vermez.
Kaynaklı güncel aday equity CSV'leri oluşturulmuş ve global evren artık boş
değildir; ancak bu aday dosyalar resmi exchange/index-provider exact top-100
kanıtı değildir. `global_master_decision_summary.json` çıktısı `not promoted`
sonucunu göstermektedir. Bunun nedeni exact top-100 desteği, point-in-time
tarihsel üyelik, delisting/corporate-action kanıtı ve global walk-forward
doğrulamasının tamamlanmamış olmasıdır. Bu sonuç bilimsel dürüstlüğün gereğidir:
proje desteklenmeyen iddiaları promote etmemektedir.

## 2. English Abstract

This dissertation-style report evaluates QuantVerse as a multi-asset,
source-aware and evidence-gated portfolio research system. The central problem
is not merely producing portfolio weights, but proving whether the data,
currency treatment, market-cap/rank evidence, model applicability, risk
diagnostics and reporting layer are sufficient to support a named portfolio
claim. The system is designed to produce candidates and then allow the evidence
gate to say "not promoted" when blockers remain.

The current evidence does not promote a global USD master portfolio. Sourced
current candidate equity files now populate the active global equity universe,
but the source class is public-provider current research input, not official
exchange or index-provider exact top-100 evidence. Exact top-100 claims remain
unsupported; Black-Litterman can only be read as diagnostic/governance-sensitive
while priors come from current public-provider market-cap fields; and
point-in-time historical claims remain unsupported without dated constituents,
delistings and corporate-action handling. The main contribution is therefore an
auditable research framework that refuses unsupported portfolio promotion.

## 3. Extended Executive Summary

QuantVerse is a research-grade quantitative portfolio analytics system. It
combines universe construction, returns calculation, portfolio optimization,
risk diagnostics, random portfolio benchmarking, scientific sanity auditing and
explainable reporting. The system has two layers: an established ETF/multi-asset
pipeline and a newer global stock/master-portfolio research layer. This thesis
package focuses on the latter because it carries the largest scientific risk:
global equities require source provenance, market-cap/rank evidence, currency
normalization, calendar alignment, corporate-action treatment and point-in-time
constituent discipline.

The present result is deliberately conservative. Real current candidate equity
rows and proxy rows exist locally, and USD-normalized research outputs can be
rebuilt. The active master decision summary still says `not promoted`. That
means the current output must not be described as a promoted global USD master
portfolio. Public-provider current research input is useful for debugging and
methodology design, but it is not final investment evidence.

The scientifically valid part of the project is the evidence-gated framework:
it shows what was attempted, what data exists, what data is missing, which
models are diagnostic, which models are blocked, and why a promotion decision
must remain negative. In a doctoral defense, this is a defensible contribution:
the system formalizes when not to believe a quantitative portfolio result.

## 4. Research Problem and Motivation

Many portfolio research projects fail not because they cannot optimize weights,
but because they hide weak inputs. A system can generate impressive-looking
Sharpe ratios while silently mixing local currencies, using current constituents
as historical evidence, treating ETF proxies as exact exposures, fitting models
without prerequisites, or presenting unstable covariance-driven optimizers as
robust discoveries.

QuantVerse addresses this problem by moving from a "model says buy" structure
to an evidence-gated research structure. The core question becomes: what must
be true before a portfolio claim is allowed? For a global master portfolio, the
answer includes source evidence, FX conversion, exact/proxy classification,
constraints, risk, random benchmark comparison, walk-forward validation and
clear limitations.

The motivation is academic and practical. Academically, the project must be
understandable to a reader who does not know the code. Practically, a user must
be able to open the PDF or Excel output and answer: which universe is being
tested, which assets are in the candidate, what weights were assigned, what
risks were measured, which blockers remain, and why the final decision is or is
not promoted.

## 5. Research Questions

1. Can a global multi-asset/stock portfolio research system be built without
   fabricating unsupported universe evidence?
2. How does FX normalization affect global USD portfolio validity?
3. What evidence is required before exact top-100 market-cap claims?
4. When should advanced models remain blocked or diagnostic only?
5. What validation gates are required before a portfolio candidate may be
   promoted?
6. How can reporting make blockers, weights and model status clear to a
   non-specialist reader without oversimplifying the mathematics?

## 6. Contribution Statement

The project contributes an evidence-gated promotion framework. A portfolio
candidate is not treated as valid merely because an optimizer returns weights.
Instead, the candidate is evaluated against data-source requirements, FX
normalization, exact/proxy status, risk metrics, constraint audits, random
portfolio benchmarks and model applicability.

The second contribution is FX normalization discipline. The system distinguishes
local returns from USD returns and documents the conversion formula. A global
USD result remains blocked if selected non-USD assets cannot be converted with
appropriate FX series, calendars and compounding logic.

The third contribution is market-cap/rank source gating. Exact top-100 claims
require source provider, source URL, as-of date, rank universe, rank method and
positive market-cap or rank evidence. Template files and proxy lists are not
evidence.

The fourth contribution is model governance. Equal Weight, Inverse Volatility,
Min Variance, Max Sharpe, Min CVaR, HRP, Risk Parity and Black-Litterman are
not treated as interchangeable. Each model must be labelled as actually run,
diagnostic only, blocked by data, not available or future candidate.

The fifth contribution is an explainable reporting layer. The thesis package,
visual audit and Excel workbook are designed to show decisions, red flags and
full weights before raw tables.

## 7. Literature and Methodology Basis

The methodology basis combines eight local books and external thesis-formatting
sources. Portfolio Optimization by Daniel P. Palomar anchors constrained
portfolio construction, covariance fragility, risk parity, CVaR and robust
optimization caution. Statistical finance texts by Severini and Ahlawat support
return definitions, covariance, MLE and statistical assumption discipline.
Machine-learning finance texts by Jansen, Dixon/Halperin/Bilokon and Hull
support leakage prevention, time-series validation, simulation and the warning
that ML prediction quality is not automatically portfolio decision quality.
ISLR provides model validation, regression/classification metric separation,
regularization, PCA and clustering discipline. Quantitative Economics with
Python supports numerical reproducibility and simulation-based economic
reasoning.

The literature-to-implementation rule is simple: every method must be mapped to
the question it can answer. Normality tests answer whether normal-only
interpretation is weak; they do not prove alpha. PCA and clustering describe
structure; they do not prove a superior allocation. Max Sharpe solves an
optimization problem; it does not prove that expected returns were estimated
reliably. Black-Litterman needs priors and views; without them it is blocked.

External academic writing sources support structure rather than financial
claims. The thesis uses monograph front matter, IMRaD logic, reproducibility
notes, references and appendices. The defense deck follows a contribution-led
story: problem, methods, evidence, limitations and decision.

## 8. Data and Source Governance

Data governance begins with universe construction. A row is not merely a ticker;
it is a claim about investability, source, sleeve, region, asset type, currency
and evidence status. For exact top-100 equity claims, the row must also carry
market-cap/rank evidence. If a row is a proxy, the report must say so.

The current source-governance conclusion is blocker-aware. Commodity and
defensive assets include proxy instruments such as ETFs or funds. These can be
useful research proxies, but they are not spot commodities, futures contracts or
direct Treasury bills. Equity top-100 claims remain unsupported when
market-cap/rank evidence is missing. The exact/proxy report explicitly states:
"Exact top-100 market-cap claim is not supported for these sleeves."

The active master decision also reports insufficient sourced global equity
universe inputs. Therefore any global research candidate must be described as a
research candidate or smoke/proxy output, not as a promoted global USD master
portfolio.

## 9. FX Normalization Methodology

Global portfolios cannot be evaluated honestly if local-currency returns are
mixed and then labelled as USD performance. The required simple-return
conversion is:

```text
usd_return = (1 + local_asset_return) * (1 + fx_return_to_usd) - 1
```

The FX return must represent the local currency's return against USD. If a data
provider supplies local currency per USD, the quote must be inverted before
computing the FX return. USD-native assets are already in the base currency and
do not require conversion.

This is a hard promotion rule: "Global USD master portfolio promotion is
blocked until non-USD local returns are converted into USD with appropriate FX
series, calendars and compounding logic." The project may still generate
diagnostics, but global USD promotion is not valid while selected non-USD
assets are missing FX-normalized returns.

## 10. Market-Cap/Rank Evidence Methodology

An exact top-100 claim is stronger than a proxy or index-membership claim. It
requires a defined rank universe, rank method, provider, source URL, as-of date
and positive market-cap or rank evidence. Example CSV files are schema
templates only. They do not prove current rank, market cap or investability.

The market-cap/rank evidence gate prevents three errors. First, it prevents
public-provider, manual-review or index-proxy lists from being described as
official exact top-100 lists. Second, it prevents Black-Litterman output from
being treated as promotion-grade allocation evidence when priors come from
current public-provider fields rather than institutional point-in-time market
capitalization data. Third, it prevents current constituent lists from being
treated as point-in-time historical memberships.

Crypto market-cap evidence also cannot be generalized to equities. A top crypto
ranking and an equity market-cap ranking have different data providers,
definitions, liquidity issues and investability constraints.

## 11. Portfolio Construction Methodology

The current global research layer includes benchmark and candidate concepts:
Equal Weight, random portfolios, Inverse Volatility, Min Variance, Max Sharpe,
Min CVaR, Policy Constrained and model-availability statuses for HRP, Risk
Parity and Black-Litterman. A model is valid only for the question it can
answer. Equal Weight is the transparent benchmark. Random portfolios are a
benchmark distribution, not future proof. Inverse Volatility is a simple risk
scaling baseline. Min Variance is defensive and covariance-sensitive. Max
Sharpe is diagnostic when expected-return estimates are weak. Min CVaR is
tail-aware but data-sensitive. Black-Litterman is computed only as a
governance-sensitive diagnostic while current public-provider market-cap fields
are used instead of official point-in-time priors.

The weight audit is central. Generated candidate weights show weight sums of
1.0 for the listed candidate models, no negative weights in the inspected
weights, and model-specific max-weight/dust-weight behavior. However, these
weights are not a promoted global USD master portfolio because the active
decision layer is `not promoted`.

## 12. Risk and Statistical Diagnostics

Risk diagnostics include volatility, drawdown, VaR, CVaR, covariance condition,
normality, stationarity, PCA, clustering and outlier checks. These diagnostics
are not decorative. They are the basis for rejecting overconfident narratives.

Normality rejection means normal-only interpretation is weak. Ill-conditioned
covariance means optimizer outputs can be unstable. Extreme CAGR, Sharpe,
Sortino or total return values must be warning flags until the data, FX and
validation layer are proven. Tail risk must be visible through CVaR, drawdown
and stress scenarios, not hidden behind a single return metric.

## 13. Model Governance

Model governance assigns each method a status:

- `actually run`: the pipeline produced evidence for the named method.
- `benchmark only`: the method is a comparison baseline.
- `blocked by data`: prerequisites are missing.
- `diagnostic only`: useful for interpretation but not direct allocation proof.
- `not appropriate`: method does not match the current question/data.
- `future candidate`: method may be added after prerequisites exist.

Under this governance, ML diagnostics are not trading signals. ARIMA, GARCH,
LSTM, RNN, Transformer and reinforcement learning are not promoted allocation
engines in the current global master portfolio layer. Black-Litterman is
diagnostic/governance-sensitive because promotion-grade market-cap priors,
views and point-in-time support are not available in the required institutional
form.

## 14. System Architecture

```text
Source CSVs and provider evidence
        |
        v
Universe construction and exact/proxy classification
        |
        v
Price, return and FX normalization layer
        |
        v
Data-quality, covariance, normality and stationarity diagnostics
        |
        v
Portfolio construction and random benchmark layer
        |
        v
Risk, stress, CVaR and constraint audit layer
        |
        v
Promotion gate and model governance layer
        |
        v
Scientific sanity audit, thesis report, defense presentation and Excel output
```

This architecture is intentionally conservative. Each layer can block the next
layer's claim. A report generated after a blocker is not invalid; it is valid as
a blocker-aware research report.

## 15. Experimental Pipeline and Reproducibility

The reproducibility stack uses local commands:

```powershell
python scripts/build_doctoral_thesis_report.py
python scripts/build_doctoral_defense_presentation.py
python -m pytest -q
python -m black src scripts tests
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m compileall src scripts
git status --short --branch
```

Focused global evidence commands may be run when fresh evidence is required:

```powershell
python scripts/validate_source_universe_inputs.py --config configs/source_universe_validation.yaml
python scripts/build_global_returns_matrix.py --config configs/global_returns_matrix.yaml
python scripts/validate_real_global_universe.py
python scripts/run_global_quant_research.py --config configs/global_quant_research.yaml
python scripts/audit_global_scientific_sanity.py
```

Generated outputs under `output/` and `data/processed/` are not committed. The
source-of-truth scripts and thesis docs are committed so the package can be
rebuilt.

## 16. Results

Current branch: `integrate-fx-marketcap-gates`.

Current key decision: `global_master_decision_summary.json` reports
`not promoted`. The sourced current candidate equity universe is no longer
empty, but it is public-provider current research input rather than official
exact top-100 evidence. Therefore the global USD master portfolio is not
promoted.

Scientific sanity audit issue counts are generated locally and should be read
from `data/processed/global_scientific_sanity_summary.csv` after each run. The
important decision is qualitative and stable: promotion blockers remain for
exact top-100 support, point-in-time membership, delisting/corporate-action
evidence and global walk-forward validation.

FX status: FX policy and reports exist, including USD-native and non-USD FX
coverage fields. The current returns matrix is USD-normalized where FX data is
available, but global USD promotion remains blocked until the source-quality
and historical-validation gates pass.

Market-cap/rank status: current public-provider market-cap and computed rank
fields exist for the sourced equity candidate files. Exact top-100 market-cap
support is still not available for the required sleeves because official or
vendor-grade rank evidence is missing. Black-Litterman output is therefore
diagnostic/governance-sensitive, not promotion-grade allocation proof.

Model results are available in local generated tables, but they must be read
under the current decision state. Generated model comparison tables may show
computed metrics for candidate models. Those metrics do not override
insufficient inputs, missing exact top-100 evidence or missing point-in-time
history.

## 17. Discussion

The main scientific improvement is that QuantVerse now refuses to convert weak
evidence into strong claims. In many quantitative projects, a high Sharpe ratio
is presented before the reader sees data problems. QuantVerse reverses that
order. It asks whether the universe is sourced, whether currencies are
normalized, whether model prerequisites exist, whether constraints pass and
whether the decision names the correct universe.

This means "not promoted" can be the correct academic result. A doctoral
committee would not require the system to outperform; it would require the
system to know what it has and has not proven. Current QuantVerse has not
proven a promotable global USD master portfolio, but it has built the audit
structure needed to prevent unsupported promotion.

## 18. Validity Threats and Limitations

The largest remaining validity threat is not a missing current universe; it is
that the populated current candidate universe is not official point-in-time
exact top-100 evidence. The second threat is the absence of dated historical
membership, delisting and corporate-action reconciliation. The third threat is
global walk-forward validation without look-ahead. These block historical
top-100 claims and promotion-grade global stock-selection claims.

Currency is another threat. Non-USD assets must be converted to USD with
appropriate FX series, calendar alignment and compounding logic. Public data
provider limitations, stale tickers, missing prices, outliers and calendar
mismatches can distort results. Model uncertainty remains material, especially
for expected-return optimizers and any ML forecast layer.

Finally, reporting itself can be a validity threat. If a PDF hides blockers or
shows raw tables without explanation, it can mislead the reader even if the
code is correct. The reporting layer must therefore emphasize decisions,
evidence and limitations before performance.

## 19. Red-Team Review

The project could overclaim in several ways. It could call proxy lists exact
top-100 lists. The exact/proxy gate blocks this. It could call a local-currency
portfolio a global USD portfolio. The FX gate blocks this. It could treat
current constituents as historical constituents. The source governance docs
block this. It could run Black-Litterman without priors. The prerequisite gate
blocks this. It could use ML diagnostics as allocation signals. Model
governance blocks this. It could present high returns while hiding outliers.
Scientific sanity audit blocks this.

Remaining unresolved risks are not hidden: official/vendor-grade exact top-100
reconciliation, point-in-time data, delistings, corporate actions,
cross-listing/domicile review, walk-forward validation and final promotion-gate
hardening remain future work.

## 20. Conclusion

QuantVerse is not yet a promoted global USD master portfolio system. It is,
however, a scientifically stronger research system than a simple optimizer
because it records why promotion is blocked. The current package can be
defended as an evidence-gated architecture, methodology and reporting system.
It cannot be defended as a proof of investable superiority.

The correct final decision is: global stock master portfolio is not promoted
because exact top-100 support, point-in-time historical evidence,
delisting/corporate-action evidence, walk-forward validation and complete
promotion-gate evidence remain blocked.

## 21. Future Work

The next sprint should replace or reconcile public-provider current candidate
CSV files with official or vendor-grade market-cap-ranked sources, add
point-in-time membership effective dates, add delisting/corporate-action
evidence, and then build global stock walk-forward validation. Only then should
transaction-cost checks, random portfolio percentile tests and final promotion
gates be interpreted as promotion-grade evidence.

Additional future work includes point-in-time constituents, delistings,
corporate-action reconciliation, vendor data comparison, institutional audit
trail, role/access control, monitoring and more formal model-approval workflow.

## 22. References

Internal references:

- `docs/roadmap/QUANTVERSE_MASTER_PROJECT_PLAN.md`
- `docs/data/global_returns_fx_policy.md`
- `docs/data/sourced_top100_universe_population.md`
- `docs/audit/market_cap_rank_source_engine_plan.md`
- `docs/thesis/thesis_style_source_audit.md`
- `docs/thesis/methodology_literature_mapping.md`
- `docs/thesis/ACADEMIC_EVIDENCE_PACK.md`
- `docs/thesis/DOCTORAL_OUTPUT_RED_TEAM_REVIEW.md`

Local methodology books:

- Daniel P. Palomar, Portfolio Optimization.
- Thomas A. Severini, Introduction to Statistical Methods for Financial Models.
- Samit Ahlawat, Statistical Quantitative Methods in Finance.
- Stefan Jansen, Machine Learning for Algorithmic Trading.
- Matthew F. Dixon, Igor Halperin and Paul Bilokon, Machine Learning in Finance.
- Isaiah Hull, Machine Learning for Economics and Finance in TensorFlow 2.
- Gareth James, Daniela Witten, Trevor Hastie and Robert Tibshirani, An
  Introduction to Statistical Learning.
- Thomas J. Sargent and John Stachurski, Quantitative Economics with Python.

Web structure references are listed in `docs/thesis/thesis_style_source_audit.md`.

## 23. Appendices

### Appendix A: Commands

The validation commands are listed in Section 15. Focused global evidence
commands should be used instead of the full ETF pipeline unless the full
pipeline is explicitly in scope.

### Appendix B: Data Schemas

Universe rows require ticker, name, sleeve, region, country, exchange,
currency, asset type, source, provider, as-of date, investability flags and
exact/proxy classification fields. Exact top-100 claims additionally require
market-cap or rank evidence.

### Appendix C: FX Mapping

FX mapping must define currency, base currency, FX ticker, source, quote
direction, inversion requirement and fallback behavior. Missing FX is a
promotion blocker.

### Appendix D: Market-Cap/Rank Schema

Required fields include market-cap native, market-cap USD, market-cap rank,
rank universe, rank method, source name, source URL, source provider and
as-of date.

### Appendix E: Test List

The current test suite passed 117 tests at the start of this sprint. Final test
count is recorded in the final response after validation.

### Appendix F: Model Applicability Matrix

Model applicability is sourced from `data/processed/model_applicability_matrix.csv`
when present. The thesis does not treat unavailable or blocked models as valid
allocation evidence.

### Appendix G: Requirement Traceability

Requirement traceability is sourced from
`data/processed/user_requirement_traceability_matrix.csv` when present. Missing
or partial requirements are blockers or future work, not hidden assumptions.

### Appendix H: Failure Mode Taxonomy

Failure modes include data-source error, FX/currency error, return/risk math
error, portfolio construction error, model validity error, backtest validation
error, ML/forecasting validation error and reporting/explainability error.

### Appendix I: Generated Output Paths

Generated thesis outputs:

- `output/thesis/quantverse_doctoral_dissertation.md`
- `output/thesis/quantverse_doctoral_dissertation.pdf`
- `output/thesis/quantverse_doctoral_defense_presentation.pdf`

These outputs are generated artifacts and are not committed.

### Appendix J: Non-Advice Disclaimer

This project is not investment advice, does not recommend buying or selling any
asset, does not guarantee performance and does not replace professional
financial, legal, tax or institutional risk review.


## QuantVerse v2 Model League Evidence

| model_name | model_family | objective | actual_status | prerequisites | prerequisites_satisfied | expected_return_source | covariance_source |
|---|---|---|---|---|---|---|---|
| Random Portfolios | benchmark_distribution | Random constrained portfolio benchmark. | benchmark_only | returns and max-weight constraint | True | none | not optimized |
| Equal Weight | benchmark | Transparent diversification baseline. | benchmark_only | returns and selected universe | True | none or historical risk model | daily USD returns covariance |
| Inverse Volatility | risk_allocation | Lower volatility concentration. | actually_run | returns and selected universe | True | none or historical risk model | daily USD returns covariance |
| GMV | risk_allocation | Minimize variance. | actually_run | sufficient returns and feasible long-only cap constraints | True | none or historical risk model | daily USD returns covariance |
| Max Sharpe | expected_return_optimization | Maximize in-sample expected return per unit risk. | diagnostic_only | sufficient returns and feasible long-only cap constraints | True | historical mean with shrinkage covariance | daily USD returns covariance |
| Min CVaR | risk_allocation | Reduce empirical tail loss. | actually_run | sufficient returns and feasible long-only cap constraints | True | none or historical risk model | daily USD returns covariance |
| HRP | risk_allocation | Allocate through correlation hierarchy. | actually_run | sufficient returns and feasible long-only cap constraints | True | none or historical risk model | daily USD returns covariance |
| Risk Parity | risk_allocation | Equalize risk contribution. | actually_run | sufficient returns and feasible long-only cap constraints | True | none or historical risk model | daily USD returns covariance |
| Black-Litterman | expected_return_optimization | Market-cap prior allocation diagnostic. | diagnostic_only | positive market caps, covariance, documented views for promotion | True | public-provider market-cap prior diagnostic | daily USD returns covariance |
| ML Forecast | forecast_overlay | Forecast diagnostic, not direct allocation. | diagnostic_only | generated return forecasts and chronological validation | False | forecast engine ensemble | daily USD returns covariance |
| Ensemble Forecast | forecast_overlay | Expected return diagnostic. | diagnostic_only | generated return forecasts and chronological validation | False | forecast engine ensemble | daily USD returns covariance |
| Forecast-Enhanced Constrained Portfolio | forecast_overlay | Use forecast under strict caps. | diagnostic_only | generated return forecasts and chronological validation | True | forecast engine ensemble | daily USD returns covariance |
| Policy Constrained | policy_constraint | Use composite score under caps. | actually_run | returns and selected universe | True | none or historical risk model | daily USD returns covariance |

## Robust Model Selection Evidence

The final public-data model is no longer selected by a simple in-sample Sharpe or CAGR sort. The selection layer excludes diagnostic and blocked models, then evaluates eligible models with walk-forward evidence, transaction-cost-adjusted return, turnover, drawdown, CVaR, Equal Weight and random portfolio percentiles. If no active model clears the gate, Equal Weight remains the defensible benchmark and no active model is promoted.

| model_name | model_status | eligible_final_model | constraint_pass | walk_forward_supported | walk_forward_annualized_return | walk_forward_volatility | walk_forward_sharpe |
|---|---|---|---|---|---|---|---|
| Policy Constrained | actually_run | True | True | True | 0.6902484870688234 | 0.072115337472777 | 2.7322648279755115 |
| Risk Parity | actually_run | True | True | True | 0.6968560574178227 | 0.0819299817816758 | 2.7098970048954696 |
| GMV | actually_run | True | True | True | 0.4823590639539034 | 0.0517858440149857 | 2.278016880047272 |
| Equal Weight | benchmark_only | True | True | True | 0.6092757046832314 | 0.0890991077073453 | 2.073119785122713 |
| Inverse Volatility | actually_run | True | True | True | 0.5865272266873832 | 0.0815374934799282 | 2.047099591980376 |
| HRP | actually_run | True | True | True | 0.4479618002227921 | 0.0626370961928234 | 1.8979708957161217 |
| Min CVaR | actually_run | True | True | True | 0.283895051160752 | 0.0580972252439665 | 1.2109201460238623 |
| Random Portfolios | benchmark_only | False | True | False | 2.5012907077053184 | 0.3600033916750189 | 6.952269895993722 |
| Max Sharpe | diagnostic_only | False | True | True | 0.6602214290872263 | 0.0705590379554826 | 2.7853196837905347 |
| Black-Litterman | diagnostic_only | False | True | True | 0.7225080475194483 | 0.1332693416981858 | 2.3712230546674413 |
| ML Forecast | diagnostic_only | False | False | False | 0.0 | 0.0 | 0.0 |
| Ensemble Forecast | diagnostic_only | False | False | False | 0.0 | 0.0 | 0.0 |
| Forecast-Enhanced Constrained Portfolio | diagnostic_only | False | True | True | 0.6888281051229556 | 0.0842723908617595 | 2.585671061329047 |

## Random Portfolio Percentile Evidence

Random portfolios are used as a benchmark distribution under the same selected universe and max-weight constraint. They do not prove future superiority, but they answer whether the candidate is unusual relative to simple constrained alternatives.

| model_name | return_percentile | volatility_percentile | sharpe_percentile | max_drawdown_percentile | cvar_percentile | better_than_random_median_sharpe | better_than_random_75th_sharpe |
|---|---|---|---|---|---|---|---|
| Random Portfolios | 0.517 | 0.509 | 0.514 | 0.505 | 0.491 | True | False |
| Equal Weight | 0.507 | 0.586 | 0.565 | 0.51 | 0.549 | True | False |
| Inverse Volatility | 0.873 | 0.24 | 0.584 | 0.217 | 0.198 | True | False |
| GMV | 0.994 | 1.0 | 1.0 | 1.0 | 1.0 | True | True |
| Max Sharpe | 0.017 | 0.97 | 0.67 | 0.978 | 0.974 | True | False |
| Min CVaR | 0.825 | 0.99 | 0.999 | 0.999 | 1.0 | True | True |
| HRP | 0.001 | 1.0 | 1.0 | 1.0 | 1.0 | True | True |
| Risk Parity | 0.897 | 0.972 | 0.998 | 0.988 | 0.969 | True | True |
| Black-Litterman | 0.749 | 1.0 | 1.0 | 1.0 | 1.0 | True | True |
| ML Forecast |  |  |  |  |  | False | False |
| Ensemble Forecast |  |  |  |  |  | False | False |
| Forecast-Enhanced Constrained Portfolio | 0.999 | 0.487 | 0.996 | 0.878 | 0.615 | True | True |
| Policy Constrained | 0.016 | 0.993 | 0.839 | 0.988 | 0.999 | True | True |

## Sensitivity and Robustness Evidence

The sensitivity layer varies max assets, max weight, transaction costs and random seeds on a bounded grid. Fragile model choice or unstable weights are reported as limitations rather than hidden behind the final headline.

| final_model | scenario_count | scenario_share | mean_selection_score | mean_net_annualized_return | mean_sharpe | mean_max_drawdown | mean_cvar_95 |
|---|---|---|---|---|---|---|---|
| Equal Weight | 48 | 1.0 | 23.663878956942103 | 2.3476760170812154 | 6.9444462180057505 | -0.04955617797824774 | -0.031131090221267876 |

## Economic Exposure Interpretation

The final model is interpreted by region, country, currency, sleeve, sector and top holding. This converts weights into an economic story that a reviewer can inspect before reading raw optimization tables.

| model_name | ticker | name | weight | sleeve | region | country | currency |
|---|---|---|---|---|---|---|---|
| Policy Constrained | BRH.F | BERKSHIRE HATHAWAY INC.       R | 0.07785158970025594 | global_equity_europe | Europe | Europe exchange listing | EUR |
| Policy Constrained | 1NVDA.MI | NVIDIA CORP | 0.06735896495945583 | global_equity_europe | Europe | Europe exchange listing | EUR |
| Policy Constrained | TRHOL.IS | TERA FINANSAL YAT. HOL. | 0.06282553176956632 | global_equity_turkey | Europe / Middle East | Turkey | TRY |
| Policy Constrained | MSFT.SW | MICROSOFT CORP | 0.0587483313757804 | global_equity_europe | Europe | Europe exchange listing | CHF |
| Policy Constrained | INTC.SW | INTEL CORP | 0.0550934475185916 | global_equity_europe | Europe | Europe exchange listing | CHF |
| Policy Constrained | 1AVGO.MI | BROADCOM | 0.05155932113154669 | global_equity_europe | Europe | Europe exchange listing | EUR |
| Policy Constrained | DSTKF.IS | DESTEK FINANS FAKTORING | 0.04889203573202459 | global_equity_turkey | Europe / Middle East | Turkey | TRY |
| Policy Constrained | GUNDG.IS | GUNDOGDU GIDA | 0.04532573912151908 | global_equity_turkey | Europe / Middle East | Turkey | TRY |
| Policy Constrained | HY9H.F | SK Hynix Inc.                 R | 0.045313698232531584 | global_equity_europe | Europe | Europe exchange listing | EUR |
| Policy Constrained | ODINE.IS | ODINE TEKNOLOJI | 0.04213022688470368 | global_equity_turkey | Europe / Middle East | Turkey | TRY |
| Policy Constrained | SNDK | Sandisk Corporation | 0.041170408895424976 | global_equity_us | North America | United States | USD |
| Policy Constrained | 3986.HK | GIGADEVICE | 0.03883913096187267 | global_equity_china | Asia | China/Hong Kong listing | HKD |
| Policy Constrained | OZATD.IS | OZATA DENIZCILIK | 0.03727875715784017 | global_equity_turkey | Europe / Middle East | Turkey | TRY |
| Policy Constrained | 285A.T | KIOXIA HOLDINGS CORPORATION | 0.036764044443852964 | global_equity_japan | Asia | Japan | JPY |
| Policy Constrained | ARMGD.IS | ARMADA GIDA | 0.03207996083465896 | global_equity_turkey | Europe / Middle East | Turkey | TRY |

## Forecast Validation Evidence

Forecasts remain diagnostic unless they beat a random-walk baseline and prove better net portfolio decision quality after risk and costs. Validation output therefore reports errors, random-walk comparison and allocation-signal status separately.

| horizon | horizon_days | forecast_count | mean_rmse | mean_mae | mean_random_walk_mae | mae_improvement_vs_random_walk | fraction_beating_random_walk |
|---|---|---|---|---|---|---|---|
| 12M | 252 | 589 | 1.0150916527161846 | 0.9454311966934937 | 0.9569678801178028 | 0.011536683424309024 | 0.6702127659574468 |
| 1M | 21 | 589 | 0.1355948098285233 | 0.1122678141597502 | 0.11431728880532882 | 0.002049474645578614 | 0.5783132530120482 |
| 3M | 63 | 589 | 0.247426968848533 | 0.21370607746073567 | 0.22819787252243495 | 0.014491795061699286 | 0.553448275862069 |
| 6M | 126 | 589 | 0.3844768618134196 | 0.3499193668891391 | 0.37935940960031594 | 0.02944004271117684 | 0.6045296167247387 |

## QuantVerse v2 Walk-Forward Evidence

| model_name | folds | avg_cagr | avg_annualized_return | avg_volatility | avg_sharpe | avg_sortino | avg_max_drawdown |
|---|---|---|---|---|---|---|---|
| Max Sharpe | 12 | 3.339250155423263 | 0.6602214290872263 | 0.07055903795548263 | 2.7853196837905347 | 3.979982031849199 | -0.003587228569195383 |
| Policy Constrained | 12 | 3.772072485702133 | 0.6902484870688234 | 0.07211533747277703 | 2.7322648279755115 | 9.465351744826476 | -0.004714223994268037 |
| Risk Parity | 10 | 2.855941714815176 | 0.6968560574178227 | 0.08192998178167586 | 2.7098970048954696 | 6.940059571606407 | -0.004537631077465021 |
| Forecast-Enhanced Constrained Portfolio | 12 | 3.4546746076712354 | 0.6888281051229556 | 0.08427239086175958 | 2.585671061329047 | 1.0031966392117793 | -0.005390391254159382 |
| Black-Litterman | 12 | 10.175073703804538 | 0.7225080475194483 | 0.1332693416981858 | 2.3712230546674413 | 0.2804153456173414 | -0.013155601977030093 |
| GMV | 12 | 1.885372933218249 | 0.48235906395390343 | 0.051785844014985795 | 2.278016880047272 | 6.562231923423521 | -0.0024134364938768285 |
| Equal Weight | 12 | 2.4689834218694977 | 0.6092757046832314 | 0.0890991077073453 | 2.073119785122713 | 273.03341898772055 | -0.006351739259590418 |
| Inverse Volatility | 12 | 2.285051288087289 | 0.5865272266873832 | 0.08153749347992824 | 2.0470995919803756 | 15.03111920224316 | -0.005885620345926333 |
| HRP | 12 | 1.6064866487507796 | 0.44796180022279214 | 0.06263709619282341 | 1.8979708957161219 | 3.3952355082362105 | -0.004017362495055503 |
| Min CVaR | 12 | 1.5605674189168017 | 0.28389505116075203 | 0.058097225243966565 | 1.2109201460238623 | 7.904709714606649 | -0.003904079494478454 |

## Simple Return

Formula: `R_t = P_t / P_{t-1} - 1`.

Simple Return is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Log Return

Formula: `r_t = log(P_t / P_{t-1})`.

Log Return is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## FX Conversion

Formula: `R_USD = (1 + R_local) * (1 + R_FX) - 1`.

FX Conversion is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Portfolio Return

Formula: `R_p = sum_i w_i R_i`.

Portfolio Return is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Covariance

Formula: `Sigma_ij = cov(R_i, R_j)`.

Covariance is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Volatility

Formula: `sigma_ann = sigma_daily * sqrt(252)`.

Volatility is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Sharpe

Formula: `Sharpe = (E[R_p] - R_f) / sigma_p`.

Sharpe is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Sortino

Formula: `Sortino = (E[R_p] - R_f) / downside_sigma`.

Sortino is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Drawdown

Formula: `DD_t = Wealth_t / running_max(Wealth) - 1`.

Drawdown is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## VaR

Formula: `VaR_95 = 5th percentile of returns`.

VaR is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## CVaR

Formula: `CVaR_95 = average return below VaR_95`.

CVaR is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Equal Weight

Formula: `w_i = 1 / N`.

Equal Weight is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Random Portfolios

Formula: `w sampled on capped long-only simplex`.

Random Portfolios is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Inverse Volatility

Formula: `w_i proportional to 1 / sigma_i`.

Inverse Volatility is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## GMV

Formula: `min_w w' Sigma w`.

GMV is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Max Sharpe

Formula: `max_w (w' mu - R_f) / sqrt(w' Sigma w)`.

Max Sharpe is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Min CVaR

Formula: `min_w expected tail loss`.

Min CVaR is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## HRP

Formula: `cluster assets by correlation then allocate by cluster variance`.

HRP is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Risk Parity

Formula: `RC_i = RC_j for all assets`.

Risk Parity is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Black-Litterman

Formula: `posterior return combines prior and views`.

Black-Litterman is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## ML Forecast

Formula: `forecast is diagnostic unless walk-forward validated`.

ML Forecast is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Ensemble Forecast

Formula: `combine transparent forecast components`.

Ensemble Forecast is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Robust Model Selection

Formula: `score = validation + risk + benchmark - costs - warnings`.

Robust Model Selection is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Random Percentile

Formula: `percentile = share(random_metric <= candidate_metric)`.

Random Percentile is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Sensitivity Analysis

Formula: `vary constraints, costs and seeds on a bounded grid`.

Sensitivity Analysis is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Exposure Interpretation

Formula: `portfolio exposure = grouped sum of weights`.

Exposure Interpretation is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Forecast Validation

Formula: `compare model error with random-walk baseline`.

Forecast Validation is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Walk-Forward

Formula: `train on past window, test on next chronological window`.

Walk-Forward is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Transaction Costs

Formula: `net return subtracts turnover times cost`.

Transaction Costs is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Risk Contribution

Formula: `CRC_i = w_i * marginal_risk_i`.

Risk Contribution is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Stress Testing

Formula: `scenario loss equals exposure times assumed shock`.

Stress Testing is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## PCA and Clustering

Formula: `diagnose dependence, not standalone alpha`.

PCA and Clustering is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.

## Model Governance

Formula: `status controls what may be claimed`.

Model Governance is included because QuantVerse must explain the mathematical operation behind every portfolio result before the reader sees a model ranking. A quantitative portfolio report is not credible when it shows a table of returns without defining the return unit, the compounding rule, the risk convention and the decision boundary. The implementation therefore records the formula, the input file, the output file and the status label attached to the method.

The public-data setting matters. The current universe is built from current public-provider candidates and not from an institutional point-in-time constituent database. That means the formula can be valid while the claim remains limited. This distinction is central to the project: correct mathematics is necessary, but it is not sufficient for promotion. Data lineage, FX treatment, survivorship controls and walk-forward validation must also pass.

In the codebase, this concept is reflected through deterministic functions, stable CSV schemas and tests that check invariants such as weight sums, long-only constraints, ordered prediction intervals, chronological train/test splits and explicit model statuses. The methodology mapping translates portfolio theory, financial statistics, econometrics and machine-learning validation principles into these software checks.

Interpretation for a banker, portfolio analyst, risk analyst or quant recruiter should be conservative. A high point estimate is not enough. The reader must ask whether the result survives costs, drawdown, CVaR, random portfolios, Equal Weight, source limitations and out-of-sample validation. QuantVerse v2 is designed to show those questions directly instead of hiding them in code.


## Promotion, Limitations and Claim Control

QuantVerse v2 is allowed to be a strong public-data research demo while still
refusing unsupported institutional claims. The current engine can score stocks,
estimate diagnostic expected returns, build a model league, calculate portfolio
risk, run a current-universe walk-forward validation and generate PDF, HTML and
Excel outputs. Those are real engineering and quantitative research
capabilities.

The same engine must also say what it has not proven. It has not proven official
exact top-100 membership. It has not proven point-in-time historical membership.
It has not reconciled delistings and corporate actions to institutional vendor
standards. It has not built a production execution system, tax engine, live
monitoring stack or model-approval workflow. These limitations do not invalidate
the public-data demo, but they do prevent stronger claims.

The correct product claim is therefore: QuantVerse v2 is a Python-based
public-data global equity selection and portfolio research platform with USD FX
normalization, stock scoring, return forecasting diagnostics, portfolio
optimization league, risk diagnostics, current-universe walk-forward validation,
scientific audit gates and explainable PDF/Excel outputs.

### Audit Expansion 1: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Robust Model Selection

For Robust Model Selection, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Random Percentile

For Random Percentile, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Sensitivity Analysis

For Sensitivity Analysis, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Exposure Interpretation

For Exposure Interpretation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Forecast Validation

For Forecast Validation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 1: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Robust Model Selection

For Robust Model Selection, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Random Percentile

For Random Percentile, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Sensitivity Analysis

For Sensitivity Analysis, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Exposure Interpretation

For Exposure Interpretation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Forecast Validation

For Forecast Validation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 2: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Robust Model Selection

For Robust Model Selection, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Random Percentile

For Random Percentile, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Sensitivity Analysis

For Sensitivity Analysis, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Exposure Interpretation

For Exposure Interpretation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Forecast Validation

For Forecast Validation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 3: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Robust Model Selection

For Robust Model Selection, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Random Percentile

For Random Percentile, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Sensitivity Analysis

For Sensitivity Analysis, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Exposure Interpretation

For Exposure Interpretation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Forecast Validation

For Forecast Validation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 4: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Robust Model Selection

For Robust Model Selection, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Random Percentile

For Random Percentile, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Sensitivity Analysis

For Sensitivity Analysis, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Exposure Interpretation

For Exposure Interpretation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Forecast Validation

For Forecast Validation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 5: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Robust Model Selection

For Robust Model Selection, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Random Percentile

For Random Percentile, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Sensitivity Analysis

For Sensitivity Analysis, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Exposure Interpretation

For Exposure Interpretation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Forecast Validation

For Forecast Validation, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 6: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.
