# Global Quant Capability Gap Matrix

This matrix is intentionally conservative. A capability is marked
`implemented` only when the current repository has code, configuration,
outputs or tests supporting the claim. Proxy-based universes are not
reported as exact market-cap-ranked top-100 universes.

## Status Summary

- `blocked_by_data`: 1
- `implemented`: 54
- `not_implemented`: 2
- `not_scientifically_appropriate`: 1
- `partially_implemented`: 26

## Matrix

| # | Question | Status | Evidence | Limitation | Next Action |
|---:|---|---|---|---|---|
| 1 | Does the project ingest real NASDAQ top 100 by market cap? | `partially_implemented` | Nasdaq-100 current constituent proxy from sourced public table. | Not exact exchange-wide top-100 market-cap ranking. | Add vendor/sourced market-cap-ranked NASDAQ file. |
| 2 | Does it ingest real NYSE top 100 by market cap? | `partially_implemented` | S&P 100 large-cap proxy source is populated. | Mixed-listing proxy, not pure NYSE top-100. | Add exchange-filtered ranked NYSE source. |
| 3 | Does it ingest real Europe top 100 by market cap or documented index proxy? | `partially_implemented` | EURO STOXX 50 proxy is populated. | Not Europe top-100 by market cap. | Add STOXX Europe 100/600 rank source. |
| 4 | Does it ingest real Germany top 100 by market cap or documented index proxy? | `partially_implemented` | DAX proxy is populated. | DAX has fewer than 100 names and is not top-100 by market cap. | Add DAX+MDAX or ranked Germany source. |
| 5 | Does it ingest real UK top 100 by market cap or FTSE-style proxy? | `implemented` | FTSE 100 proxy is populated. | Current constituents are not point-in-time historical constituents. | Add vendor point-in-time FTSE membership. |
| 6 | Does it ingest real Borsa Istanbul top 100 or BIST 100 proxy? | `implemented` | KAP BIST 100 constituent proxy is populated. | Current BIST 100 is forward-looking if backtested historically. | Add point-in-time BIST membership. |
| 7 | Does it ingest real Japan top 100 by market cap or Nikkei/TOPIX proxy? | `partially_implemented` | Nikkei 225 source subset is populated. | Not a top-100-by-market-cap claim. | Add TOPIX/Core30/market-cap ranked source. |
| 8 | Does it ingest real China/Hong Kong top 100 by market cap or documented index proxy? | `partially_implemented` | Hang Seng constituent proxy is populated. | Not broad China/HK top-100 by market cap. | Add CSI/HKEX ranked source. |
| 9 | Does it ingest gold, silver, oil, platinum and copper proxies? | `implemented` | Commodity proxy universe includes GLD, SLV, CPER, PPLT, PALL, USO, BNO and UNG. | ETF/fund proxies are not spot commodities. | Add futures/spot series if licensed data is available. |
| 10 | Does it ingest crypto top 100 by market cap? | `implemented` | CoinGecko market-cap API source is populated. | Ticker mapping to Yahoo may fail for some assets. | Add exchange/vendor crypto price source. |
| 11 | Does it flag/exclude stablecoins where appropriate? | `implemented` | Stable-like crypto rows are flagged as non-investable. | Rule-based detection needs periodic review. | Add stablecoin taxonomy source. |
| 12 | Does it include bonds, bills, treasury/cash proxies? | `implemented` | SHY, IEF, TLT, AGG, TIP, BIL and SGOV are included as proxies. | ETF proxies differ from direct bonds/bills. | Add Treasury bill and curve data. |
| 13 | Does it cluster by exchange/region? | `partially_implemented` | Region exposures and region caps are audited. | Region is constrained, not clustered by exchange. | Add exchange/region cluster diagnostics. |
| 14 | Does it cluster by asset class? | `partially_implemented` | Sleeve exposures and caps are audited. | Asset-class grouping is not a statistical cluster. | Add sleeve-level clustering report. |
| 15 | Does it cluster by correlation? | `implemented` | Hierarchical correlation clustering is used for selection and diagnostics. | Cluster stability is not yet bootstrapped. | Add cluster stability analysis. |
| 16 | Does it determine number of clusters using elbow/silhouette or equivalent? | `implemented` | Cluster diagnostics include within-cluster distance and silhouette values. | Promotion gate does not yet choose k from silhouette automatically. | Use diagnostics to select k explicitly. |
| 17 | Does it determine holdings per cluster? | `partially_implemented` | Selection spreads holdings across correlation clusters. | Holdings-per-cluster target is simple and heuristic. | Add formal cluster budget policy. |
| 18 | Does it enforce diversification across clusters? | `implemented` | Max cluster weight is audited and enforced for policy-constrained candidate. | Cluster definitions are return-sample dependent. | Add robustness checks across windows. |
| 19 | Does it compute log returns where appropriate? | `implemented` | Global returns builder writes log returns. | Not every downstream model consumes log returns yet. | Use log returns in statistical diagnostics where appropriate. |
| 20 | Does it compute simple returns where portfolio aggregation requires them? | `implemented` | Global returns builder writes simple returns and portfolio pipeline uses simple aggregation. | Corporate-action quality depends on yfinance adjusted data. | Add vendor adjusted price reconciliation. |
| 21 | Does it test normality of returns? | `implemented` | Jarque-Bera normality tests are written per asset. | Multiple-testing adjustment is not yet added. | Add FDR-adjusted summary. |
| 22 | If returns are non-normal, does it use robust/tail methods instead of forcing normality? | `implemented` | Historical CVaR, Min CVaR, drawdown and stress tests are used. | No full EVT/GARCH tail model is promoted. | Add EVT/GARCH as research diagnostics. |
| 23 | Does it estimate covariance using sample covariance? | `implemented` | Sample covariance is included in estimator comparison. | Sample covariance is fragile in large universes. | Use as benchmark only. |
| 24 | Does it estimate covariance using shrinkage/Ledoit-Wolf or equivalent? | `implemented` | Ledoit-Wolf estimator comparison is included. | Not yet integrated into every optimizer. | Route risk optimizers through estimator config. |
| 25 | Does it estimate covariance using EWMA? | `implemented` | EWMA covariance is included in comparison. | EWMA span is fixed, not nested-validated. | Add configurable span validation. |
| 26 | Does it support MLE-style distribution estimation? | `partially_implemented` | MLE normal covariance proxy is reported. | Full parametric distribution fitting is not implemented. | Add explicit t/normal MLE diagnostics. |
| 27 | Does it check correlation matrix validity? | `implemented` | Correlation matrix diagnostics and diagonal checks are available. | Repair logic is limited. | Add nearest-PSD repair report if needed. |
| 28 | Does it check covariance matrix stability/PSD? | `implemented` | Estimator comparison reports eigenvalue and PSD checks. | Condition number thresholds are diagnostic only. | Add gate thresholds. |
| 29 | Equal Weight | `implemented` | Portfolio model comparison includes Equal Weight. | Benchmark, not automatic proof of optimality. | Keep as baseline. |
| 30 | Inverse Volatility | `implemented` | Global master portfolio computes inverse volatility weights. | Can over-allocate defensive assets. | Use constraint audit. |
| 31 | Min Variance | `implemented` | Global master portfolio computes Min Variance. | Sensitive to covariance estimate. | Use shrinkage/EWMA variants later. |
| 32 | Max Sharpe | `implemented` | Global master portfolio computes shrinkage Max Sharpe candidate. | Expected-return estimates are noisy. | Treat as diagnostic unless robust. |
| 33 | HRP | `partially_implemented` | ETF/research layers support HRP; global run lists it when not available. | Not fully wired into this global stock master run. | Integrate HRP with global constraints. |
| 34 | Risk Parity | `partially_implemented` | ETF/research layers support Risk Parity; global run lists it when not available. | Not fully wired into this global stock master run. | Integrate risk parity with global constraints. |
| 35 | Min CVaR | `implemented` | Global master portfolio computes Min CVaR. | Can become defensive-heavy without constraints. | Use promotion and constraint gates. |
| 36 | Black-Litterman | `blocked_by_data` | Global run computes it only when all selected market caps are available. | Equity market caps are mostly missing in current proxy universe. | Add sourced market caps. |
| 37 | Robust optimization | `not_implemented` | Model applicability registry documents it. | No uncertainty set or validation yet. | Implement only after clean constraints/data. |
| 38 | Convex optimization | `partially_implemented` | Policy-constrained candidate uses linear programming and other optimizers use scipy. | Not all objectives are formal convex programs. | Add convex objective registry. |
| 39 | Factor modeling | `not_implemented` | Model applicability registry marks factor model as not implemented. | No factor data or exposure model. | Add vendor/macro/factor inputs. |
| 40 | Forecast-enhanced optimization | `partially_implemented` | Forecast outputs exist; global comparison lists forecast-enhanced variants as unavailable. | Forecasts are not promoted into allocation. | Add strict train/test overlay. |
| 41 | Cluster-balanced optimization | `implemented` | Cluster-balanced model is computed. | May overweight weak clusters. | Keep as diversification candidate. |
| 42 | Random portfolio benchmark | `implemented` | Random portfolios are simulated with reproducible seed. | Random benchmark is not proof of future superiority. | Add larger sensitivity runs. |
| 43 | ARMA/ARIMA/SARIMA applicability | `partially_implemented` | Applicability registry and forecast output document optional status. | No automated ARIMA/SARIMA fit in global run. | Add only where stationarity/data support it. |
| 44 | GARCH volatility modeling applicability | `partially_implemented` | Registry marks GARCH optional for volatility. | No GARCH estimation in current run. | Add optional volatility diagnostic. |
| 45 | Linear regression | `implemented` | Forecast metrics include a rolling mean/random-walk baseline style regression output. | Feature set is simple. | Add validated features. |
| 46 | Ridge | `implemented` | Registry marks Ridge implemented in forecast family. | Not separately reported in current global CSV. | Expose per-model metrics. |
| 47 | Lasso | `partially_implemented` | Registry marks Lasso optional. | No current global Lasso output. | Run only after feature validation. |
| 48 | Logistic regression for downside classification | `implemented` | Classification metrics and AUC are reported for downside diagnostics. | Not a direct trading signal. | Add calibrated probabilities. |
| 49 | Decision tree | `implemented` | Registry marks tree model implemented as diagnostic. | Overfit-prone without nested validation. | Report tree metrics only when run. |
| 50 | Random forest | `implemented` | Registry marks random forest implemented as diagnostic. | No direct allocation promotion. | Add feature/validation reports. |
| 51 | Gradient boosting | `implemented` | Registry marks gradient boosting implemented as diagnostic. | Overfit risk remains. | Add nested validation. |
| 52 | XGBoost optional adapter | `partially_implemented` | Registry detects optional package availability. | Not a required dependency. | Run only if dependency and validation exist. |
| 53 | GBM / sklearn gradient boosting | `implemented` | Registry includes sklearn gradient boosting. | Not directly promoted into weights. | Expose metrics in forecast league. |
| 54 | LSTM/RNN optional adapter | `not_scientifically_appropriate` | Registry treats LSTM/RNN as optional research only. | Current sample/validation does not justify deep allocation. | Do not add until strict validation exists. |
| 55 | PCA | `implemented` | PCA explained variance output is generated. | PCA is diagnostic, not alpha proof. | Add factor interpretation. |
| 56 | Classification metrics | `implemented` | Classification metrics CSV is generated. | Class imbalance handling is limited. | Add PR AUC/Brier. |
| 57 | Confusion matrix | `implemented` | Confusion matrix CSV is generated. | Threshold is simple median score. | Tune threshold only in training windows. |
| 58 | AUC/ROC | `implemented` | ROC AUC CSV is generated. | No confidence interval yet. | Add bootstrap AUC CI. |
| 59 | R2 | `implemented` | Regression metrics include R2. | Low or negative R2 must not be overclaimed. | Use as diagnostic only. |
| 60 | AIC/BIC where appropriate | `partially_implemented` | Time-series metrics include AIC/BIC placeholders for optional models. | No ARIMA/GARCH model selection run. | Compute only when model is fitted. |
| 61 | Train/test split | `partially_implemented` | Forecast helpers use shifted/rolling diagnostics. | Global forecast layer is not full walk-forward allocation validation. | Add explicit split artifact. |
| 62 | Walk-forward validation | `partially_implemented` | Core ETF/challenger pipeline has walk-forward validation. | Global stock master run is current-universe research, not historical point-in-time walk-forward. | Add point-in-time universe history. |
| 63 | Rolling window validation | `partially_implemented` | Rolling scores and diagnostics are used. | No complete rolling global master promotion gate. | Add rolling master backtest. |
| 64 | Random walk benchmark | `implemented` | Forecast layer reports random-walk baseline. | Benchmark only. | Keep as required comparator. |
| 65 | VaR | `implemented` | Risk reports include VaR-style outputs in core and projection layers. | Global gate still needs full unified VaR table. | Add global VaR summary. |
| 66 | CVaR | `implemented` | Min CVaR and risk reports include CVaR. | Historical CVaR depends on sample. | Add tail robustness. |
| 67 | Stress tests | `implemented` | Global stress test results are generated. | Scenarios are stylized. | Add macro/vendor scenarios. |
| 68 | Scenario analysis | `implemented` | Scenario analysis output is generated. | Scenario calibration is simple. | Add macro scenarios. |
| 69 | Monte Carlo simulation | `implemented` | Monte Carlo projection output is generated. | Assumption-sensitive. | Add block bootstrap alternatives. |
| 70 | 1/3/6/12 month projection | `implemented` | Projection script writes horizon-specific CSVs. | Projection is not a guarantee. | Add uncertainty narrative. |
| 71 | Probability of loss | `implemented` | Monte Carlo output includes probability of loss. | Based on simulated distribution. | Add bootstrap comparison. |
| 72 | Drawdown projection | `partially_implemented` | Drawdown is in risk metrics; projected drawdown is not fully separated. | No dedicated drawdown projection CSV. | Add drawdown simulation output. |
| 73 | Transaction-cost sensitivity | `partially_implemented` | Core ETF pipeline has transaction-cost sensitivity; global gate has simple cost assumptions. | Global stock transaction-cost grid is not complete. | Add global cost sensitivity. |
| 74 | Bootstrap robustness | `partially_implemented` | Core challenger pipeline has bootstrap robustness. | Global stock master lacks full bootstrap gate. | Add global bootstrap vs Equal Weight. |
| 75 | Do all portfolio weights sum to 1? | `implemented` | Portfolio audit and tests verify full weight sums. | Generated outputs should be re-audited after each run. | Keep audit in validation. |
| 76 | Are negative weights prevented unless shorting is explicitly enabled? | `implemented` | Global candidates are long-only and audit checks negatives. | No shorting support is exposed. | Keep long-only by default. |
| 77 | Are max/min weight constraints enforced? | `implemented` | Max weight and holding bounds are audited; policy candidate enforces caps. | Minimum per-asset weight is only a practical LP lower bound. | Expose min-weight config if needed. |
| 78 | Can each portfolio have different numbers of assets? | `implemented` | Candidate weight vectors can have different effective holdings counts. | Selected universe is shared within a run. | Add model-specific selection stage. |
| 79 | Are asset-class constraints enforced? | `implemented` | Policy constrained model enforces global equity, defensive, crypto and commodity caps. | Unconstrained variants can violate caps and are labelled. | Do not promote violating variants. |
| 80 | Are region/exchange constraints enforced? | `partially_implemented` | Region caps are enforced; exchange caps are not separate. | Exchange-level cap is not implemented. | Add exchange cap if required. |
| 81 | Are crypto/commodity/bond caps enforced? | `implemented` | Crypto, commodity and defensive caps are audited and enforced for policy candidate. | Classification depends on source metadata. | Keep source schema strict. |
| 82 | Are signal-only tickers excluded from investable weights? | `implemented` | Universe filter excludes signal-only rows from investable assets. | Requires correct source flags. | Audit flags per run. |
| 83 | Are all displayed/report weights traceable to CSV outputs? | `implemented` | Weights, asset-class, region and cluster CSVs are generated. | Manual report excerpts must cite full CSV path. | Keep report linked to artifacts. |
| 84 | Are top-holdings tables labelled partial if not all holdings are shown? | `implemented` | Report wording labels condensed tables as excerpts. | Needs review whenever report layout changes. | Keep report QA checklist. |
