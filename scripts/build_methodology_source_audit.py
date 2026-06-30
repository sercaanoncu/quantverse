"""Build methodology source inventory and source-check documents."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

BOOK_DIR = Path("..") / "book"
OUTPUT_DIR = Path("data/processed")
AUDIT_DIR = Path("docs/audit")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-dir", default=str(BOOK_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--audit-dir", default=str(AUDIT_DIR))
    return parser.parse_args()


def build_source_inventory(book_dir: str | Path = BOOK_DIR) -> pd.DataFrame:
    """Return local methodology book inventory."""
    rows = []
    for path in sorted(Path(book_dir).glob("*.pdf")):
        rows.append(_book_row(path))
    return pd.DataFrame(rows)


def build_methodology_source_check() -> pd.DataFrame:
    """Return methodology guardrails used by the visual audit sprint."""
    rows = [
        _method(
            "Markowitz / mean-variance optimization",
            "Portfolio Optimization; Statistical Quantitative Methods in Finance",
            "Mean-variance uses expected return and covariance estimates to trade off risk and return.",
            "Useful as a benchmark optimizer when estimates are stable and constraints are explicit.",
            "Fragile when expected returns are noisy or covariance is unstable.",
            "OOS CAGR, volatility, Sharpe, drawdown, turnover, constraint audit.",
            "Treating in-sample optimum as investment proof.",
            "implemented; suspicious metrics flagged",
            "Keep diagnostic unless robust walk-forward evidence supports promotion.",
        ),
        _method(
            "global minimum variance",
            "Portfolio Optimization",
            "Global minimum variance relies mostly on covariance estimates, not expected-return forecasts.",
            "Defensive allocation and covariance diagnostics.",
            "Can concentrate in low-volatility assets and miss return objectives.",
            "Volatility, drawdown, CVaR, concentration.",
            "Calling low variance a return champion.",
            "implemented",
            "Report as defensive/risk candidate.",
        ),
        _method(
            "maximum Sharpe",
            "Portfolio Optimization; Introduction to Statistical Methods for Financial Models",
            "Maximum Sharpe is highly sensitive to expected-return estimation error.",
            "Diagnostic optimizer under strict constraints and validation.",
            "Weak when expected returns are noisy or in-sample.",
            "OOS Sharpe, bootstrap CI, cost sensitivity.",
            "Promoting a high in-sample Sharpe without robustness.",
            "implemented; blocked from promotion when gates fail",
            "Keep strong warning in reports.",
        ),
        _method(
            "risk parity",
            "Portfolio Optimization",
            "Risk parity balances risk contributions rather than capital weights.",
            "Risk-balanced defensive allocation.",
            "Not proof of high return and not wired into current global run.",
            "Risk contribution, volatility, drawdown.",
            "Claiming it ran when output says not available.",
            "not_available_in_global_run",
            "Integrate only with global constraints.",
        ),
        _method(
            "HRP",
            "Portfolio Optimization; Machine Learning for Algorithmic Trading",
            "Hierarchical risk parity uses correlation clustering to allocate risk more robustly.",
            "Useful when covariance inversion is unstable.",
            "Not wired into current global stock master output.",
            "OOS risk, drawdown, cluster stability.",
            "Claiming HRP output without generated weights.",
            "not_available_in_global_run",
            "Add constrained HRP candidate later.",
        ),
        _method(
            "Black-Litterman",
            "Portfolio Optimization",
            "Black-Litterman requires a defensible prior such as market-cap weights or documented views.",
            "Combining priors and views when source data exists.",
            "Blocked when market caps are missing.",
            "Weight plausibility, view sensitivity, OOS metrics.",
            "Running BL with fabricated market caps.",
            "blocked_by_data",
            "Add sourced market-cap priors.",
        ),
        _method(
            "CVaR / expected shortfall",
            "Portfolio Optimization; risk-management references",
            "CVaR focuses on expected tail loss beyond VaR.",
            "Tail-risk-aware defensive optimization and risk reporting.",
            "Sample-tail estimates can be noisy.",
            "Historical CVaR, stress, bootstrap.",
            "Ignoring sign/unit conventions.",
            "implemented",
            "Keep sign conventions explicit.",
        ),
        _method(
            "robust optimization",
            "Portfolio Optimization",
            "Robust optimization needs explicit uncertainty sets.",
            "Institutional robustness checks when uncertainty is modeled.",
            "Not justified without validated uncertainty assumptions.",
            "Robust utility, OOS stability.",
            "Adding robust label without uncertainty set.",
            "not_implemented",
            "Future work only.",
        ),
        _method(
            "convex optimization",
            "Portfolio Optimization",
            "Convex objectives/constraints can improve solvability and auditability.",
            "Policy constraints and feasible long-only allocation.",
            "Not every objective in the system is convex.",
            "Solver status, constraint audit.",
            "Hiding infeasibility.",
            "partially_implemented",
            "Report optimizer status and constraints.",
        ),
        _method(
            "random portfolio benchmarking",
            "Portfolio Optimization",
            "Random portfolios provide a distributional comparator.",
            "Benchmarking candidate rank against feasible alternatives.",
            "Not proof of future superiority.",
            "Percentile vs random Sharpe/CAGR/drawdown.",
            "Calling random percentile a guarantee.",
            "implemented",
            "Keep benchmark language conservative.",
        ),
        _method(
            "VaR",
            "financial risk management references",
            "VaR estimates a loss quantile.",
            "Risk reporting with clear horizon/confidence.",
            "Does not measure average tail loss.",
            "Exception tests, VaR sign and units.",
            "Positive/negative sign confusion.",
            "implemented",
            "Audit signs and captions.",
        ),
        _method(
            "CVaR",
            "financial risk management references",
            "CVaR estimates expected loss conditional on exceeding VaR.",
            "Tail-risk reporting.",
            "Sensitive to limited tail samples.",
            "CVaR, stress tests.",
            "Treating CVaR as normal-only metric.",
            "implemented",
            "Use historical/tail-aware interpretation.",
        ),
        _method(
            "stress testing",
            "risk-management references",
            "Stress tests apply adverse scenarios to exposures.",
            "Scenario communication and risk governance.",
            "Stylized scenarios are not forecasts.",
            "Scenario impact and sensitivity.",
            "Treating stress as prediction.",
            "implemented",
            "Caption as stylized.",
        ),
        _method(
            "scenario analysis",
            "risk-management references",
            "Scenario analysis compares portfolio response under defined shocks.",
            "Explaining plausible adverse states.",
            "Scenario calibration can be subjective.",
            "Scenario impact, sensitivity.",
            "No source/caption for scenario.",
            "implemented",
            "Add source and assumptions.",
        ),
        _method(
            "drawdown",
            "Portfolio Optimization",
            "Drawdown measures peak-to-trough loss path.",
            "Investor risk and crisis behavior.",
            "Depends on sample path.",
            "Max drawdown, Calmar.",
            "Ignoring drawdown penalty.",
            "implemented",
            "Show alongside CAGR.",
        ),
        _method(
            "volatility estimation",
            "Introduction to Statistical Methods for Financial Models",
            "Volatility must match return frequency and annualization convention.",
            "Risk scaling and covariance diagnostics.",
            "High volatility can expose data issues.",
            "Annualized volatility, condition number.",
            "Mixing daily/monthly units.",
            "implemented; suspicious values flagged",
            "Flag volatility above 100%.",
        ),
        _method(
            "GARCH",
            "time-series econometrics references",
            "GARCH models conditional volatility, not direct portfolio weights.",
            "Volatility/risk forecasting when fitted and validated.",
            "Not run in this sprint.",
            "AIC/BIC, forecast error, volatility backtest.",
            "Using GARCH label without fitting.",
            "optional_not_run",
            "Future diagnostic.",
        ),
        _method(
            "bootstrap robustness",
            "statistical learning references",
            "Bootstrap estimates sampling uncertainty.",
            "Robustness around return/risk differences.",
            "Global stock layer does not yet have full bootstrap gate.",
            "CI for CAGR/Sharpe differences.",
            "Overclaiming point estimates.",
            "partially_implemented",
            "Add global bootstrap.",
        ),
        _method(
            "Monte Carlo simulation",
            "Quantitative Economics with Python; Portfolio Optimization",
            "Simulation propagates assumptions to a distribution of outcomes.",
            "Projection uncertainty communication.",
            "Assumption-sensitive and not a guarantee.",
            "Loss probability, percentile bands.",
            "Presenting simulated mean as forecast certainty.",
            "implemented",
            "Show 5th/95th bands.",
        ),
        _method(
            "simple returns vs log returns",
            "Introduction to Statistical Methods for Financial Models",
            "Simple returns aggregate linearly across portfolio weights; log returns add over time.",
            "Simple for portfolio aggregation, log for statistical diagnostics.",
            "Wrong use causes unit errors.",
            "Return policy audit.",
            "Using log returns for cross-sectional weighted portfolio aggregation.",
            "implemented",
            "Keep policy in reports.",
        ),
        _method(
            "stationarity",
            "time-series econometrics references",
            "Stationarity affects time-series model validity.",
            "ADF diagnostics for returns.",
            "Rejecting/accepting unit-root tests does not prove predictability.",
            "ADF p-value, sample length.",
            "Running ARIMA blindly on nonstationary levels.",
            "implemented",
            "Interpret conservatively.",
        ),
        _method(
            "normality testing",
            "Introduction to Statistical Methods for Financial Models",
            "Financial returns often reject normality.",
            "Trigger robust/tail-aware interpretation.",
            "Normality tests are sample-size sensitive.",
            "Jarque-Bera, skew, kurtosis.",
            "Forcing normal methods after rejection.",
            "implemented",
            "Flag non-normality.",
        ),
        _method(
            "ARMA",
            "time-series references",
            "ARMA models stationary serial dependence.",
            "Univariate diagnostic when stationarity is plausible.",
            "Not a default allocation engine.",
            "AIC/BIC, test error.",
            "Using without fitted likelihood model.",
            "optional_not_run",
            "Future model only.",
        ),
        _method(
            "ARIMA",
            "time-series references",
            "ARIMA handles integration/differencing.",
            "Univariate forecast benchmark when fitted.",
            "Not run in current global output.",
            "AIC/BIC, forecast error.",
            "Reporting AIC/BIC without fit.",
            "optional_not_run",
            "Keep placeholders explicit.",
        ),
        _method(
            "SARIMA",
            "time-series references",
            "SARIMA adds seasonality.",
            "Seasonal series with evidence of seasonality.",
            "Usually not first-line for daily asset returns.",
            "AIC/BIC, forecast error.",
            "Assuming seasonality without evidence.",
            "not_scientifically_appropriate_by_default",
            "Do not run blindly.",
        ),
        _method(
            "AIC/BIC",
            "statistical modeling references",
            "AIC/BIC apply to fitted likelihood-based statistical models.",
            "ARIMA/GARCH-like model comparison.",
            "Not meaningful for random walk placeholder rows.",
            "AIC/BIC only when fitted.",
            "Showing NaN AIC/BIC as model performance.",
            "guarded",
            "Explain NaN as not run.",
        ),
        _method(
            "rolling window",
            "Machine Learning for Algorithmic Trading",
            "Rolling windows avoid using future data in time-series features.",
            "Forecast diagnostics and backtesting.",
            "Window length must be justified.",
            "Rolling OOS error.",
            "Using full sample for signals.",
            "partially_implemented",
            "Expand global walk-forward.",
        ),
        _method(
            "walk-forward validation",
            "Machine Learning for Algorithmic Trading; ISLR",
            "Walk-forward evaluates decisions chronologically.",
            "Out-of-sample model promotion.",
            "Global stock layer lacks point-in-time history.",
            "OOS return/risk/cost robustness.",
            "Tuning on test period.",
            "partially_implemented",
            "Add point-in-time backtest.",
        ),
        _method(
            "random walk benchmark",
            "time-series forecasting references",
            "Random walk is a hard baseline for asset returns.",
            "Forecast benchmark.",
            "Does not allocate weights.",
            "Forecast error vs baseline.",
            "Calling weak forecast alpha.",
            "implemented",
            "Keep as baseline.",
        ),
        _method(
            "linear regression",
            "ISLR",
            "Linear regression estimates conditional mean under assumptions.",
            "Transparent diagnostic baseline.",
            "Weak for noisy daily returns.",
            "RMSE, MAE, R2.",
            "Using R2 as trading proof.",
            "implemented_diagnostic",
            "Do not promote directly.",
        ),
        _method(
            "ridge",
            "ISLR",
            "Ridge regularizes linear regression.",
            "Collinear features and shrinkage.",
            "Still needs train/test validation.",
            "RMSE, MAE, R2.",
            "Promoting without OOS edge.",
            "implemented_diagnostic",
            "Keep diagnostic.",
        ),
        _method(
            "lasso",
            "ISLR",
            "Lasso performs sparse linear selection.",
            "Feature selection with validation.",
            "Can be unstable across samples.",
            "RMSE, MAE, R2, stability.",
            "Data snooping feature selection.",
            "optional",
            "Future only.",
        ),
        _method(
            "logistic regression",
            "ISLR",
            "Logistic regression models class probabilities.",
            "Downside classification.",
            "Not a direct allocation engine.",
            "AUC, F1, confusion matrix, Brier.",
            "Using classification probability as buy signal without validation.",
            "implemented_diagnostic",
            "Keep diagnostic.",
        ),
        _method(
            "decision tree",
            "ISLR",
            "Trees can model nonlinear splits but overfit easily.",
            "Diagnostic nonlinear baseline.",
            "Needs pruning/validation.",
            "RMSE/AUC depending task.",
            "Unvalidated tree allocation.",
            "implemented_diagnostic",
            "Keep warning.",
        ),
        _method(
            "random forest",
            "ISLR; Machine Learning for Algorithmic Trading",
            "Random forests reduce tree variance by bagging.",
            "Nonlinear diagnostic benchmark.",
            "Can still overfit finance features.",
            "OOS error/AUC.",
            "Black-box promotion without governance.",
            "implemented_diagnostic",
            "No direct promotion.",
        ),
        _method(
            "gradient boosting",
            "ISLR; Machine Learning for Algorithmic Trading",
            "Boosting sequentially fits weak learners.",
            "Diagnostic supervised benchmark.",
            "High overfit risk.",
            "OOS error/AUC.",
            "Tuning until outperformance.",
            "implemented_diagnostic",
            "Nested validation needed.",
        ),
        _method(
            "XGBoost if available",
            "package/provider documentation and ML texts",
            "XGBoost is optional high-capacity boosting.",
            "Only if dependency and validation exist.",
            "Not required, not a production allocation engine.",
            "OOS error/AUC, calibration.",
            "Mandatory heavy dependency or overclaim.",
            "optional",
            "Keep optional.",
        ),
        _method(
            "LSTM/RNN limitations",
            "Machine Learning in Finance; ML for Algorithmic Trading",
            "Deep sequential models require large data and strict validation.",
            "Research diagnostics with enough data.",
            "Not justified as first-line portfolio engine here.",
            "OOS error, stability, costs.",
            "Adding LSTM to look advanced.",
            "not_production",
            "Do not implement now.",
        ),
        _method(
            "classification metrics",
            "ISLR",
            "AUC/confusion matrix apply to classification labels.",
            "Downside event diagnostics.",
            "Not for regression.",
            "AUC, F1, confusion matrix.",
            "Reporting AUC for continuous returns.",
            "implemented",
            "Audit task type.",
        ),
        _method(
            "regression metrics",
            "ISLR",
            "RMSE/MAE/R2 apply to continuous targets.",
            "Return forecast diagnostics.",
            "Low/negative R2 is common and must be disclosed.",
            "RMSE, MAE, R2.",
            "Reporting R2 for classification.",
            "implemented",
            "Audit task type.",
        ),
        _method(
            "train/test split",
            "ISLR; ML for Algorithmic Trading",
            "Training and testing must be separated chronologically for time series.",
            "Forecast and model validation.",
            "Current global allocation is not fully walk-forward.",
            "Chronological OOS metrics.",
            "Leakage from random split.",
            "partially_implemented",
            "Add explicit split artifacts.",
        ),
        _method(
            "leakage prevention",
            "ML for Algorithmic Trading",
            "Signals must use only information available before the trade date.",
            "All model promotion work.",
            "Requires point-in-time data.",
            "Look-ahead audit.",
            "Using future prices/memberships.",
            "partially_implemented",
            "Add point-in-time history.",
        ),
        _method(
            "survivorship bias",
            "ML for Algorithmic Trading; portfolio texts",
            "Current constituents can bias historical tests.",
            "Universe construction audit.",
            "Current proxy lists cannot support historical outperformance.",
            "Point-in-time membership coverage.",
            "Backtesting current winners historically.",
            "blocked_by_data",
            "Add historical constituents/delistings.",
        ),
        _method(
            "look-ahead bias",
            "ML for Algorithmic Trading",
            "Future information must not influence past decisions.",
            "Backtests and signals.",
            "Global current universe is not historical walk-forward.",
            "Signal/trade time audit.",
            "Using full-sample ranks for OOS decisions.",
            "partially_implemented",
            "Add timestamped universe snapshots.",
        ),
        _method(
            "point-in-time constituents",
            "index/provider documentation",
            "Historical membership must be dated.",
            "Institutional backtests.",
            "Missing for current proxy files.",
            "Constituent date coverage.",
            "Calling current lists historical.",
            "blocked_by_data",
            "Source dated files.",
        ),
        _method(
            "corporate actions",
            "market-data documentation",
            "Adjusted prices must handle splits/dividends.",
            "Return construction.",
            "yfinance adjusted data is not institutional reconciliation.",
            "Adjusted-price/source audit.",
            "Using raw close with splits.",
            "partially_implemented",
            "Vendor reconciliation.",
        ),
        _method(
            "adjusted prices",
            "market-data documentation",
            "Adjusted closes are preferred for total-return-like historical analysis.",
            "Return calculation when available.",
            "Provider quality varies.",
            "Coverage and price audit.",
            "Ignoring adjustment assumption.",
            "implemented_with_public_data",
            "Document provider limits.",
        ),
        _method(
            "delistings",
            "survivorship-bias references",
            "Delisted assets matter in historical stock tests.",
            "Institutional backtests.",
            "Missing in current data.",
            "Delisting coverage.",
            "Survivorship-biased performance.",
            "blocked_by_data",
            "Add delisting source.",
        ),
        _method(
            "FX normalization",
            "market-data and portfolio accounting practice",
            "Non-USD local returns must be converted for a USD portfolio.",
            "Global USD portfolio promotion.",
            "Not implemented for 475 local-currency rows.",
            "FX status, converted return audit.",
            "Mixing local returns as USD.",
            "blocked_by_data",
            "Implement FX series conversion.",
        ),
        _method(
            "local-currency vs USD returns",
            "portfolio accounting practice",
            "Local returns and base-currency returns answer different questions.",
            "Clear report labeling.",
            "Current global candidate is local-currency mixed.",
            "FX normalization report.",
            "Promoting USD result from mixed returns.",
            "blocked_by_data",
            "Block promotion.",
        ),
        _method(
            "market-cap ranking",
            "index/exchange data-source practice",
            "Exact top-100 requires source date, market cap or rank evidence.",
            "Universe claims.",
            "Most equity sleeves lack cap/rank.",
            "Market-cap coverage report.",
            "Calling proxy exact top-100.",
            "blocked_by_data",
            "Add sourced ranks.",
        ),
        _method(
            "index proxy vs exact top-100 distinction",
            "source validation policy",
            "Index constituents can be valid proxies but not exact rank evidence.",
            "Transparent reporting.",
            "Proxy status still visually underexplained.",
            "Source method coverage.",
            "Hiding proxy label.",
            "partially_implemented",
            "Make visual reports explicit.",
        ),
    ]
    return pd.DataFrame(rows)


def write_outputs(
    inventory: pd.DataFrame,
    source_check: pd.DataFrame,
    output_dir: str | Path = OUTPUT_DIR,
    audit_dir: str | Path = AUDIT_DIR,
) -> None:
    out = Path(output_dir)
    audit = Path(audit_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(out / "methodology_source_inventory.csv", index=False)
    source_check.to_csv(out / "methodology_source_check.csv", index=False)
    (audit / "methodology_source_inventory.md").write_text(
        _inventory_markdown(inventory), encoding="utf-8"
    )
    (audit / "methodology_source_check.md").write_text(
        _source_check_markdown(source_check), encoding="utf-8"
    )


def _book_row(path: Path) -> dict[str, object]:
    try:
        reader = PdfReader(str(path))
        metadata = reader.metadata or {}
        page_count = len(reader.pages)
        title = str(metadata.get("/Title") or "").strip()
        if not title:
            sample = ""
            for idx in range(min(2, page_count)):
                sample += (reader.pages[idx].extract_text() or "")[:500] + " "
            title = _infer_title(path.name, sample)
    except Exception as exc:
        return {
            "filename": path.name,
            "page_count": "",
            "detected_title": "",
            "broad_topic": "unreadable_pdf",
            "usable_for_sprint": False,
            "relevant_sections": "",
            "notes": f"Could not inspect PDF: {exc}",
        }
    topic = _topic_from_name(path.name, title)
    return {
        "filename": path.name,
        "page_count": int(page_count),
        "detected_title": title,
        "broad_topic": topic,
        "usable_for_sprint": True,
        "relevant_sections": _relevant_sections(topic),
        "notes": "Used for methodology principles only; no long copyrighted excerpts copied.",
    }


def _infer_title(filename: str, sample: str) -> str:
    lowered = filename.lower()
    if "islr" in lowered:
        return "An Introduction to Statistical Learning"
    if "algorithmic_trading" in lowered:
        return "Machine Learning for Algorithmic Trading"
    if "machine-learning-in-finance" in lowered:
        return "Machine Learning in Finance"
    if "quantitative_economics" in lowered:
        return "Quantitative Economics with Python"
    if "statistical_quantitative" in lowered:
        return "Statistical Quantitative Methods in Finance"
    return " ".join(sample.split()[:12]) or filename


def _topic_from_name(filename: str, title: str) -> str:
    text = f"{filename} {title}".lower()
    if "portfolio" in text:
        return "portfolio_optimization"
    if "statistical" in text and "financial" in text:
        return "financial_statistics"
    if "economics" in text:
        return "econometrics_and_economic_modeling"
    if "algorithmic" in text:
        return "financial_machine_learning_and_trading"
    if "machine learning" in text or "islr" in text:
        return "machine_learning_validation"
    return "quantitative_finance"


def _relevant_sections(topic: str) -> str:
    mapping = {
        "portfolio_optimization": "mean-variance, constraints, CVaR, robust optimization, risk parity, Black-Litterman",
        "financial_statistics": "returns, normality, stationarity, volatility, estimation, risk metrics",
        "econometrics_and_economic_modeling": "time-series modeling, simulation, stationarity, Monte Carlo",
        "financial_machine_learning_and_trading": "walk-forward validation, leakage, survivorship bias, ML metrics",
        "machine_learning_validation": "train/test split, regression/classification metrics, regularization, tree models",
        "quantitative_finance": "portfolio management, risk, model validation",
    }
    return mapping.get(topic, "general methodology")


def _method(
    area: str,
    trusted_source: str,
    practical_rule: str,
    appropriate_when: str,
    not_appropriate_when: str,
    validation_metric: str,
    misuse: str,
    quantverse_status: str,
    required_fix: str,
) -> dict[str, str]:
    return {
        "methodology_area": area,
        "trusted_source_used": trusted_source,
        "practical_rule": practical_rule,
        "appropriate_when": appropriate_when,
        "not_appropriate_when": not_appropriate_when,
        "validation_metric": validation_metric,
        "misuse_in_quantverse": misuse,
        "current_quantverse_status": quantverse_status,
        "required_fix_if_weak": required_fix,
    }


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    rows = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for record in frame[columns].fillna("").astype(str).itertuples(index=False):
        rows.append(
            "| " + " | ".join(str(value).replace("|", "\\|") for value in record) + " |"
        )
    return "\n".join(rows)


def _inventory_markdown(inventory: pd.DataFrame) -> str:
    return (
        "# Methodology Source Inventory\n\n"
        "This inventory records local PDF books discovered for the sprint. "
        "Books were used only to extract methodology principles and validation rules; "
        "no long copyrighted passages are copied.\n\n"
        + _markdown_table(
            inventory,
            [
                "filename",
                "page_count",
                "detected_title",
                "broad_topic",
                "usable_for_sprint",
                "relevant_sections",
            ],
        )
        + "\n"
    )


def _source_check_markdown(source_check: pd.DataFrame) -> str:
    return (
        "# Methodology Source Check\n\n"
        "This check converts trusted methodology sources into practical validation "
        "rules for QuantVerse. It is intentionally conservative: a method is not "
        "treated as scientifically valid unless the data, assumptions and validation "
        "metric fit the task.\n\n"
        + _markdown_table(
            source_check,
            [
                "methodology_area",
                "trusted_source_used",
                "practical_rule",
                "current_quantverse_status",
                "required_fix_if_weak",
            ],
        )
        + "\n"
    )


def main() -> int:
    args = parse_args()
    inventory = build_source_inventory(args.book_dir)
    source_check = build_methodology_source_check()
    write_outputs(inventory, source_check, args.output_dir, args.audit_dir)
    print(f"Methodology books discovered: {len(inventory)}")
    print(f"Methodology checks written: {len(source_check)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
