# Global Quant Failure Mode Taxonomy

This taxonomy defines what counts as an error before the project is audited.

## A. Data-Source Errors

- fake ticker,
- fake source URL,
- missing as-of date,
- index proxy mislabelled as exact top-100,
- missing market-cap coverage,
- insufficient price coverage,
- duplicate ticker,
- stablecoin entering risk allocation.

## B. FX and Currency Errors

- non-USD local returns mixed as USD,
- FX normalization missing but portfolio promoted,
- currency field missing or wrong,
- FX blocker hidden in report.

## C. Return and Risk Math Errors

- simple/log return misuse,
- annualization mismatch,
- risk-free frequency mismatch,
- CAGR/volatility/Sharpe unit mismatch,
- VaR/CVaR sign confusion,
- drawdown inconsistency,
- covariance instability hidden.

## D. Portfolio Construction Errors

- weights do not sum to 1,
- negative weight without shorting,
- max weight cap breach,
- asset-class cap breach,
- region cap breach,
- cluster cap breach,
- excessive dust weights,
- too many max-cap weights,
- economic concentration despite formal constraints.

## E. Model Validity Errors

- running models where assumptions are not met,
- reporting AIC/BIC without a fitted likelihood-based model,
- reporting AUC/confusion matrix for regression,
- reporting R2 for classification,
- claiming Black-Litterman without market caps,
- claiming HRP/Risk Parity if not wired into the global run,
- using ML/deep learning as an allocation engine without strict validation.

## F. Reporting Errors

- raw DataFrame dumps,
- `Unnamed: 0` columns shown,
- no charts,
- no explanation of what a table means,
- top holdings not labelled partial,
- decimals not converted to percentages,
- no source path or caption,
- blockers buried or hidden,
- report not understandable to the user.
