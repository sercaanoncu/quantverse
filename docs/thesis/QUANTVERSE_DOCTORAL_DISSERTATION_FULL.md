# QuantVerse Doctoral Dissertation Full

This full manuscript is generated from the committed QuantVerse v2 engine, local methodology mapping and current public-data outputs. It is not investment advice, does not claim official exact top-100 support and does not claim institutional point-in-time validation.

## Current Engine Snapshot

- Run status: `completed`
- Universe rows: `600`
- Assets with USD returns: `582`
- Stocks scored: `582`
- Stocks selected: `40`
- Final selected model: `GMV`
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

## QuantVerse v2 Walk-Forward Evidence

| model_name | folds | avg_cagr | avg_annualized_return | avg_volatility | avg_sharpe | avg_sortino | avg_max_drawdown |
|---|---|---|---|---|---|---|---|
| Max Sharpe | 12 | 3.427856188313863 | 0.663929682097696 | 0.06940527932564623 | 2.8571862664846 | 3.3597990402605915 | -0.003242201491877872 |
| Risk Parity | 10 | 2.9285284794571522 | 0.7011558878368694 | 0.08151023425058354 | 2.735466601511407 | 6.921591008869503 | -0.0047954048458090145 |
| Policy Constrained | 12 | 3.7460193767953576 | 0.6891005986481447 | 0.07222662885233165 | 2.7312191790007407 | 9.005455344752617 | -0.004729939341729393 |
| Forecast-Enhanced Constrained Portfolio | 12 | 3.5768074816466684 | 0.6948170755633822 | 0.08273688359634336 | 2.6207447515964972 | 1.0511933462523546 | -0.00557471279269255 |
| Black-Litterman | 12 | 10.189395930538238 | 0.7241926130546226 | 0.13025321043355853 | 2.380987894333296 | 0.2985373515473274 | -0.012969012363142601 |
| GMV | 12 | 1.9796987073429246 | 0.4876204151784824 | 0.05133684823133814 | 2.322830603777223 | 6.585471861743393 | -0.0025305816393103864 |
| Equal Weight | 12 | 2.5578100379806847 | 0.6155147954890542 | 0.08794691938310377 | 2.1020228141714057 | 273.05578522844434 | -0.006465045209707439 |
| Inverse Volatility | 12 | 2.347532632622493 | 0.5913798256590147 | 0.08082049353875796 | 2.068327996783611 | 15.095833557456203 | -0.006015133258352188 |
| HRP | 12 | 1.6369187649814145 | 0.4500704428781046 | 0.06291202482346665 | 1.896033048887113 | 3.068045511899222 | -0.004367267897960316 |
| Min CVaR | 12 | 1.5719078828112556 | 0.28312583784816275 | 0.058524658840852596 | 1.188164413190731 | 7.067264222449694 | -0.003942351979371567 |

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

### Audit Expansion 7: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 7: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Simple Return

For Simple Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Log Return

For Log Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: FX Conversion

For FX Conversion, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Portfolio Return

For Portfolio Return, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Covariance

For Covariance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Volatility

For Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Sharpe

For Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Sortino

For Sortino, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Drawdown

For Drawdown, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: VaR

For VaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: CVaR

For CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Equal Weight

For Equal Weight, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Random Portfolios

For Random Portfolios, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Inverse Volatility

For Inverse Volatility, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: GMV

For GMV, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Max Sharpe

For Max Sharpe, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Min CVaR

For Min CVaR, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: HRP

For HRP, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Risk Parity

For Risk Parity, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Black-Litterman

For Black-Litterman, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: ML Forecast

For ML Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Ensemble Forecast

For Ensemble Forecast, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Walk-Forward

For Walk-Forward, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Transaction Costs

For Transaction Costs, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Risk Contribution

For Risk Contribution, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Stress Testing

For Stress Testing, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: PCA and Clustering

For PCA and Clustering, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.

### Audit Expansion 8: Model Governance

For Model Governance, the audit question is not only whether the formula was computed, but whether the claim attached to the formula is valid for the current evidence layer. The input must be named, the output must be reproducible, the model status must be explicit and the limitation must be visible in the report. If a metric is extreme, the correct interpretation is warning first, not marketing success. If the universe is current-only, the correct historical interpretation is public-data research, not institutional point-in-time proof. If the model uses expected returns, the correct validation question is whether those expectations helped net portfolio decision quality after risk, turnover and costs.
