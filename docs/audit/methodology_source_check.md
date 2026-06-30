# Methodology Source Check

This check converts trusted methodology sources into practical validation rules for QuantVerse. It is intentionally conservative: a method is not treated as scientifically valid unless the data, assumptions and validation metric fit the task.

| methodology_area | trusted_source_used | practical_rule | current_quantverse_status | required_fix_if_weak |
| --- | --- | --- | --- | --- |
| Markowitz / mean-variance optimization | Portfolio Optimization; Statistical Quantitative Methods in Finance | Mean-variance uses expected return and covariance estimates to trade off risk and return. | implemented; suspicious metrics flagged | Keep diagnostic unless robust walk-forward evidence supports promotion. |
| global minimum variance | Portfolio Optimization | Global minimum variance relies mostly on covariance estimates, not expected-return forecasts. | implemented | Report as defensive/risk candidate. |
| maximum Sharpe | Portfolio Optimization; Introduction to Statistical Methods for Financial Models | Maximum Sharpe is highly sensitive to expected-return estimation error. | implemented; blocked from promotion when gates fail | Keep strong warning in reports. |
| risk parity | Portfolio Optimization | Risk parity balances risk contributions rather than capital weights. | not_available_in_global_run | Integrate only with global constraints. |
| HRP | Portfolio Optimization; Machine Learning for Algorithmic Trading | Hierarchical risk parity uses correlation clustering to allocate risk more robustly. | not_available_in_global_run | Add constrained HRP candidate later. |
| Black-Litterman | Portfolio Optimization | Black-Litterman requires a defensible prior such as market-cap weights or documented views. | blocked_by_data | Add sourced market-cap priors. |
| CVaR / expected shortfall | Portfolio Optimization; risk-management references | CVaR focuses on expected tail loss beyond VaR. | implemented | Keep sign conventions explicit. |
| robust optimization | Portfolio Optimization | Robust optimization needs explicit uncertainty sets. | not_implemented | Future work only. |
| convex optimization | Portfolio Optimization | Convex objectives/constraints can improve solvability and auditability. | partially_implemented | Report optimizer status and constraints. |
| random portfolio benchmarking | Portfolio Optimization | Random portfolios provide a distributional comparator. | implemented | Keep benchmark language conservative. |
| VaR | financial risk management references | VaR estimates a loss quantile. | implemented | Audit signs and captions. |
| CVaR | financial risk management references | CVaR estimates expected loss conditional on exceeding VaR. | implemented | Use historical/tail-aware interpretation. |
| stress testing | risk-management references | Stress tests apply adverse scenarios to exposures. | implemented | Caption as stylized. |
| scenario analysis | risk-management references | Scenario analysis compares portfolio response under defined shocks. | implemented | Add source and assumptions. |
| drawdown | Portfolio Optimization | Drawdown measures peak-to-trough loss path. | implemented | Show alongside CAGR. |
| volatility estimation | Introduction to Statistical Methods for Financial Models | Volatility must match return frequency and annualization convention. | implemented; suspicious values flagged | Flag volatility above 100%. |
| GARCH | time-series econometrics references | GARCH models conditional volatility, not direct portfolio weights. | optional_not_run | Future diagnostic. |
| bootstrap robustness | statistical learning references | Bootstrap estimates sampling uncertainty. | partially_implemented | Add global bootstrap. |
| Monte Carlo simulation | Quantitative Economics with Python; Portfolio Optimization | Simulation propagates assumptions to a distribution of outcomes. | implemented | Show 5th/95th bands. |
| simple returns vs log returns | Introduction to Statistical Methods for Financial Models | Simple returns aggregate linearly across portfolio weights; log returns add over time. | implemented | Keep policy in reports. |
| stationarity | time-series econometrics references | Stationarity affects time-series model validity. | implemented | Interpret conservatively. |
| normality testing | Introduction to Statistical Methods for Financial Models | Financial returns often reject normality. | implemented | Flag non-normality. |
| ARMA | time-series references | ARMA models stationary serial dependence. | optional_not_run | Future model only. |
| ARIMA | time-series references | ARIMA handles integration/differencing. | optional_not_run | Keep placeholders explicit. |
| SARIMA | time-series references | SARIMA adds seasonality. | not_scientifically_appropriate_by_default | Do not run blindly. |
| AIC/BIC | statistical modeling references | AIC/BIC apply to fitted likelihood-based statistical models. | guarded | Explain NaN as not run. |
| rolling window | Machine Learning for Algorithmic Trading | Rolling windows avoid using future data in time-series features. | partially_implemented | Expand global walk-forward. |
| walk-forward validation | Machine Learning for Algorithmic Trading; ISLR | Walk-forward evaluates decisions chronologically. | partially_implemented | Add point-in-time backtest. |
| random walk benchmark | time-series forecasting references | Random walk is a hard baseline for asset returns. | implemented | Keep as baseline. |
| linear regression | ISLR | Linear regression estimates conditional mean under assumptions. | implemented_diagnostic | Do not promote directly. |
| ridge | ISLR | Ridge regularizes linear regression. | implemented_diagnostic | Keep diagnostic. |
| lasso | ISLR | Lasso performs sparse linear selection. | optional | Future only. |
| logistic regression | ISLR | Logistic regression models class probabilities. | implemented_diagnostic | Keep diagnostic. |
| decision tree | ISLR | Trees can model nonlinear splits but overfit easily. | implemented_diagnostic | Keep warning. |
| random forest | ISLR; Machine Learning for Algorithmic Trading | Random forests reduce tree variance by bagging. | implemented_diagnostic | No direct promotion. |
| gradient boosting | ISLR; Machine Learning for Algorithmic Trading | Boosting sequentially fits weak learners. | implemented_diagnostic | Nested validation needed. |
| XGBoost if available | package/provider documentation and ML texts | XGBoost is optional high-capacity boosting. | optional | Keep optional. |
| LSTM/RNN limitations | Machine Learning in Finance; ML for Algorithmic Trading | Deep sequential models require large data and strict validation. | not_production | Do not implement now. |
| classification metrics | ISLR | AUC/confusion matrix apply to classification labels. | implemented | Audit task type. |
| regression metrics | ISLR | RMSE/MAE/R2 apply to continuous targets. | implemented | Audit task type. |
| train/test split | ISLR; ML for Algorithmic Trading | Training and testing must be separated chronologically for time series. | partially_implemented | Add explicit split artifacts. |
| leakage prevention | ML for Algorithmic Trading | Signals must use only information available before the trade date. | partially_implemented | Add point-in-time history. |
| survivorship bias | ML for Algorithmic Trading; portfolio texts | Current constituents can bias historical tests. | blocked_by_data | Add historical constituents/delistings. |
| look-ahead bias | ML for Algorithmic Trading | Future information must not influence past decisions. | partially_implemented | Add timestamped universe snapshots. |
| point-in-time constituents | index/provider documentation | Historical membership must be dated. | blocked_by_data | Source dated files. |
| corporate actions | market-data documentation | Adjusted prices must handle splits/dividends. | partially_implemented | Vendor reconciliation. |
| adjusted prices | market-data documentation | Adjusted closes are preferred for total-return-like historical analysis. | implemented_with_public_data | Document provider limits. |
| delistings | survivorship-bias references | Delisted assets matter in historical stock tests. | blocked_by_data | Add delisting source. |
| FX normalization | market-data and portfolio accounting practice | Non-USD local returns must be converted for a USD portfolio. | blocked_by_data | Implement FX series conversion. |
| local-currency vs USD returns | portfolio accounting practice | Local returns and base-currency returns answer different questions. | blocked_by_data | Block promotion. |
| market-cap ranking | index/exchange data-source practice | Exact top-100 requires source date, market cap or rank evidence. | blocked_by_data | Add sourced ranks. |
| index proxy vs exact top-100 distinction | source validation policy | Index constituents can be valid proxies but not exact rank evidence. | partially_implemented | Make visual reports explicit. |
