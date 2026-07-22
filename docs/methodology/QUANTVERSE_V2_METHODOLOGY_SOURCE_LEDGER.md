# QuantVerse v2 Methodology Source Ledger

## Purpose And Evidence Hierarchy

This ledger records why a method is present, how QuantVerse implements it, and
what evidence class the resulting output may support. A citation does not make
an implementation correct by itself. Source support, mathematical
implementation, input suitability, out-of-sample validation, and economic
interpretation must all agree.

Evidence is resolved in this order:

1. Mathematical identities and unit contracts.
2. Primary peer-reviewed research or an authoritative original source.
3. The eight local methodology books as implementation and validation guidance.
4. Provider documentation for data semantics.
5. Explicit QuantVerse assumptions and limitations.

If sources describe different conventions, QuantVerse chooses one convention,
labels it, tests it, and does not mix the alternatives in one metric.

## Eight Local Methodology Books

The books were inspected from the user-supplied `<local-book-library>` outside
the repository. They are not redistributed by this repository, and no long
passages are reproduced.

| ID | Local file | Verified title / author | Pages | QuantVerse contribution | Implementation decision |
|---|---|---|---:|---|---|
| B1 | `_OceanofPDF.com_Machine_Learning_for_Economics_and_Finance_-_Isaiah_Hull.pdf` | *Machine Learning for Economics and Finance in TensorFlow 2*, Isaiah Hull | 321 | Chronological ML evaluation, regression/classification discipline, regularization, simulation | ML forecasts remain diagnostic until they beat a random-walk baseline out of sample and survive economic gates. |
| B2 | `_OceanofPDF.com_Statistical_Quantitative_Methods_in_Finance_-_Samit_Ahlawat.pdf` | *Statistical Quantitative Methods in Finance*, Samit Ahlawat | 301 | Return distributions, estimation, regression, likelihood and model selection | Distributional assumptions are diagnosed rather than silently imposed; AIC/BIC are not shown for models without a fitted likelihood. |
| B3 | `introduction-to-statistical-methods-for-financial-models_compress.pdf` | *Introduction to Statistical Methods for Financial Models*, Thomas A. Severini | 387 | Simple/log returns, covariance, stationarity, random-walk benchmark, sampling error | Simple returns drive portfolio arithmetic; log returns drive selected diagnostics and log-return simulation. |
| B4 | `ISLRv2_website.pdf` | *An Introduction to Statistical Learning*, second edition | 612 | Train/test separation, regularization, trees, boosting, PCA, clustering and task-appropriate metrics | Chronological finance splits replace random row splits; predictive metrics are matched to the task. |
| B5 | `machine-learning-in-finance-matthew-f-dixon-igor-halperin-paul-bilokon_compress.pdf` | *Machine Learning in Finance*, Dixon, Halperin and Bilokon | 565 | Financial ML leakage, non-stationarity, risk, time series and governance | No LSTM, RNN, RL or generic AI allocation claim is promotable in the current evidence layer. |
| B6 | `Machine_Learning_for_Algorithmic_Trading_Predictive.pdf` | *Machine Learning for Algorithmic Trading*, Stefan Jansen | 821 | Point-in-time data, survivorship bias, walk-forward evaluation, HRP, costs and backtest overfit | Current-universe walk-forward results are explicitly research evidence, not institutional point-in-time evidence. |
| B7 | `portfolio-optimization-book.pdf` | *Portfolio Optimization*, Daniel P. Palomar | 608 | Mean-variance optimization, constraints, risk parity, HRP, CVaR, robust covariance and optimizer fragility | Long-only capped portfolios are solved explicitly; infeasible or failed optimizers are not relabelled as successful models. |
| B8 | `quantitative_economics_with_python.pdf` | *Quantitative Economics with Python* | 943 | Simulation, econometric interpretation, dynamic systems, estimation and reproducibility | Statistical significance is separated from economic usefulness, and assumptions are exposed in generated artifacts. |

## Primary Research Ledger

| ID | Primary source | Principle used | QuantVerse rule | Current status |
|---|---|---|---|---|
| P1 | Markowitz, H. (1952), “Portfolio Selection,” *Journal of Finance*, 7(1), 77-91. DOI: https://doi.org/10.1111/j.1540-6261.1952.tb01525.x | Portfolio return is linear in weights; portfolio variance depends on covariance; return and risk are distinct objectives. | Risk-return charts put volatility on x and return on y. GMV and Max Sharpe are separate models. | Implemented; Max Sharpe is diagnostic because expected-return error is material. |
| P2 | Sharpe, W. F. (1994), “The Sharpe Ratio,” Stanford reprint: https://web.stanford.edu/~wfsharpe/art/sr/SR.htm | Sharpe uses differential return relative to a defined benchmark or risk-free rate. | Every Sharpe output carries `risk_free_rate_annual` and `risk_free_policy`; current policy is explicitly 0% annual. | Implemented with a disclosed research assumption, not a claim that cash earned 0%. |
| P3 | Ledoit, O. and Wolf, M. (2004), “A well-conditioned estimator for large-dimensional covariance matrices.” DOI: https://doi.org/10.1016/S0047-259X(03)00096-4 | Sample covariance can be ill-conditioned; linear shrinkage improves conditioning. | Covariance-dependent optimizers use complete-case Ledoit-Wolf where implemented. Estimator labels are written to outputs. | Implemented for the v2 optimizer paths; sample covariance remains only in explicitly labelled diagnostics. |
| P4 | DeMiguel, V., Garlappi, L. and Uppal, R. (2009), “Optimal Versus Naive Diversification.” DOI: https://doi.org/10.1093/rfs/hhm075 | Estimation error can erase optimized-portfolio gains out of sample; 1/N is a demanding benchmark. | Equal Weight is mandatory but not an automatic winner. Active models must clear comparable net OOS and uncertainty gates. | Implemented. |
| P5 | Lopez de Prado, M. (2016), “Building Diversified Portfolios that Outperform Out-of-Sample.” DOI: https://doi.org/10.3905/jpm.2016.42.4.059 | HRP uses correlation structure and recursive allocation without covariance inversion. | HRP is evaluated as a risk-allocation candidate under the same selected universe and walk-forward calendar. | Actually run; not hard-coded as champion. |
| P6 | Rockafellar, R. T. and Uryasev, S. (2000), “Optimization of Conditional Value-at-Risk,” *Journal of Risk*, 2(3), 21-41. Author publication list: https://uryasev.ams.stonybrook.edu/publications/ | CVaR can be represented in an optimization-friendly form and targets the loss tail. | Min CVaR uses an explicit linear program; optimizer failure is surfaced. Historical CVaR is reported as a negative return-tail mean. | Implemented with a historical-sample limitation. |
| P7 | White, H. (2000), “A Reality Check for Data Snooping.” DOI: https://doi.org/10.1111/1468-0262.00152 | Reusing one history for repeated specification search inflates apparent evidence. | Configuration sensitivity is labelled diagnostic and cannot promote a model; multiple-testing controls remain a documented gap. | Partial: no White Reality Check/SPA implementation. |
| P8 | Bailey, D. H. and Lopez de Prado, M. (2014), “The Deflated Sharpe Ratio.” SSRN: https://ssrn.com/abstract=2460551 | Sharpe evidence is inflated by non-normality, selection bias and multiple trials. | Paired block-bootstrap Sharpe-difference uncertainty is required for active promotion; DSR/PBO remain future validation work. | Partial: paired uncertainty implemented; DSR and PBO not implemented. |

## Method-To-Code Traceability

| Method | Source basis | Code evidence | Output evidence | Evidence class |
|---|---|---|---|---|
| Simple return arithmetic | B3, P1 | `src/project/data_pipeline/global_returns.py`; `src/project/research/global_portfolio_league.py` | `global_security_simple_returns_usd.csv`; league and walk-forward returns | Core arithmetic |
| Log-return diagnostics | B2, B3 | `src/project/research/global_statistical_diagnostics.py` | `global_security_log_returns_usd.csv`; statistical diagnostics | Diagnostic |
| Ledoit-Wolf covariance | B7, P3 | `src/project/research/global_portfolio_league.py`; `src/project/research/global_master_portfolio.py` | model status and covariance comparison artifacts | Allocation input |
| Equal Weight | B7, P4 | `src/project/research/global_portfolio_league.py` | portfolio league and OOS comparison | Mandatory benchmark |
| GMV | B7, P1, P3 | `src/project/research/global_portfolio_league.py` | portfolio league and OOS comparison | Candidate |
| Max Sharpe | B7, P1, P3 | `src/project/research/global_portfolio_league.py` | portfolio league and OOS comparison | Diagnostic only |
| Inverse Volatility / Risk Parity | B7 | `src/project/research/global_portfolio_league.py` | portfolio league and OOS comparison | Risk-allocation candidate |
| HRP | B6, B7, P5 | `src/project/optimization/hierarchical.py`; league builder | portfolio league and OOS comparison | Risk-allocation candidate |
| Min CVaR | B7, P6 | `src/project/optimization/cvar_optimization.py`; league builder | portfolio league and risk report | Tail-risk candidate |
| Black-Litterman | B7 | `src/project/optimization/black_litterman.py` | prerequisite report and model status | Diagnostic only with current, non-point-in-time priors |
| Stock score | B1, B4, B6 | `src/project/research/global_stock_scoring.py` | `global_stock_scores.csv` | Research ranking input |
| Ridge forecast | B1, B4, B5, B6 | `src/project/projection/global_forecast_engine.py`; validation module | forecast and random-walk comparison artifacts | Diagnostic only |
| Walk-forward | B4, B5, B6 | `src/project/research/global_walk_forward.py` | OOS returns, weights, turnover, leakage audit | Primary comparative evidence, current-universe biased |
| Paired block bootstrap | B5, B6, P7, P8 | `src/project/research/global_walk_forward.py` | `global_walk_forward_uncertainty.csv` | Uncertainty evidence |
| Random portfolios | B7, B8 | `src/project/research/global_model_selection.py` | constrained random distributions and percentiles | Benchmark diagnostic, not a probability of future success |
| Monte Carlo projection | B2, B3, B8 | `src/project/projection/portfolio_projection.py` | projection summary and bands | Parametric scenario diagnostic |
| Stress testing | B7, B8 | `src/project/research/global_portfolio_risk.py` | stress test results | Stylized scenario diagnostic |

## Conflict Resolution Decisions

1. **Simple versus log returns:** simple returns are used for weighted portfolio
   aggregation and realized compounding. Log returns are used for selected
   distribution diagnostics and the parametric Monte Carlo model. A simple
   return at or below -100% is rejected.
2. **Equal Weight versus optimized models:** Equal Weight is a benchmark, not a
   prior winner. Selection uses comparable net walk-forward evidence. No active
   model is promoted merely because it wins in sample.
3. **Covariance estimators:** optimizer paths prefer complete-case Ledoit-Wolf.
   A sample-covariance risk-contribution table is permitted only when the output
   labels the estimator and remains diagnostic.
4. **Normality:** normality tests describe model risk; rejection does not delete
   data and does not establish predictability. Tail and drawdown measures remain
   mandatory.
5. **Forecasting:** lower predictive error is insufficient for allocation.
   Forecasts remain diagnostic unless chronological OOS performance beats the
   random-walk baseline and survives portfolio-level cost/risk gates.
6. **Robustness:** the bounded configuration grid is current-sample sensitivity.
   Its unused test-window field is explicitly marked `test_window_applied=false`.
   It cannot satisfy a promotion gate.
7. **Point-in-time evidence:** a current constituent universe cannot establish a
   historical investable universe. All OOS results retain survivorship and
   delisting limitations.
8. **Risk-free rate:** 0% is an explicit simplifying research assumption. It is
   not a historical cash-return reconstruction.

## Methods Deliberately Not Claimed

- No institutional point-in-time top-100 selection claim.
- No White Reality Check, SPA, Deflated Sharpe Ratio or full PBO estimate.
- No calibrated probabilistic forecast interval.
- No LSTM, Transformer, reinforcement-learning or LLM allocation engine.
- No market-impact, bid-ask spread, tax, borrow, fractional-share or execution
  simulation.
- No production model approval, live limit system, access control or trade audit
  trail.
