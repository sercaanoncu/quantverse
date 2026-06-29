"""Build the global quant capability gap matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ALLOWED_STATUS = {
    "implemented",
    "partially_implemented",
    "not_implemented",
    "blocked_by_data",
    "not_scientifically_appropriate",
    "planned_this_sprint",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv-output",
        default="data/processed/global_quant_capability_gap_matrix.csv",
        help="Path for the CSV matrix output.",
    )
    parser.add_argument(
        "--markdown-output",
        default="docs/audit/global_quant_capability_gap_matrix.md",
        help="Path for the Markdown matrix output.",
    )
    return parser.parse_args()


def build_matrix() -> pd.DataFrame:
    """Return the 84-item global quant capability matrix."""
    rows = [
        _row(
            1,
            "Does the project ingest real NASDAQ top 100 by market cap?",
            "partially_implemented",
            "Nasdaq-100 current constituent proxy from sourced public table.",
            "Not exact exchange-wide top-100 market-cap ranking.",
            "Add vendor/sourced market-cap-ranked NASDAQ file.",
        ),
        _row(
            2,
            "Does it ingest real NYSE top 100 by market cap?",
            "partially_implemented",
            "S&P 100 large-cap proxy source is populated.",
            "Mixed-listing proxy, not pure NYSE top-100.",
            "Add exchange-filtered ranked NYSE source.",
        ),
        _row(
            3,
            "Does it ingest real Europe top 100 by market cap or documented index proxy?",
            "partially_implemented",
            "EURO STOXX 50 proxy is populated.",
            "Not Europe top-100 by market cap.",
            "Add STOXX Europe 100/600 rank source.",
        ),
        _row(
            4,
            "Does it ingest real Germany top 100 by market cap or documented index proxy?",
            "partially_implemented",
            "DAX proxy is populated.",
            "DAX has fewer than 100 names and is not top-100 by market cap.",
            "Add DAX+MDAX or ranked Germany source.",
        ),
        _row(
            5,
            "Does it ingest real UK top 100 by market cap or FTSE-style proxy?",
            "implemented",
            "FTSE 100 proxy is populated.",
            "Current constituents are not point-in-time historical constituents.",
            "Add vendor point-in-time FTSE membership.",
        ),
        _row(
            6,
            "Does it ingest real Borsa Istanbul top 100 or BIST 100 proxy?",
            "implemented",
            "KAP BIST 100 constituent proxy is populated.",
            "Current BIST 100 is forward-looking if backtested historically.",
            "Add point-in-time BIST membership.",
        ),
        _row(
            7,
            "Does it ingest real Japan top 100 by market cap or Nikkei/TOPIX proxy?",
            "partially_implemented",
            "Nikkei 225 source subset is populated.",
            "Not a top-100-by-market-cap claim.",
            "Add TOPIX/Core30/market-cap ranked source.",
        ),
        _row(
            8,
            "Does it ingest real China/Hong Kong top 100 by market cap or documented index proxy?",
            "partially_implemented",
            "Hang Seng constituent proxy is populated.",
            "Not broad China/HK top-100 by market cap.",
            "Add CSI/HKEX ranked source.",
        ),
        _row(
            9,
            "Does it ingest gold, silver, oil, platinum and copper proxies?",
            "implemented",
            "Commodity proxy universe includes GLD, SLV, CPER, PPLT, PALL, USO, BNO and UNG.",
            "ETF/fund proxies are not spot commodities.",
            "Add futures/spot series if licensed data is available.",
        ),
        _row(
            10,
            "Does it ingest crypto top 100 by market cap?",
            "implemented",
            "CoinGecko market-cap API source is populated.",
            "Ticker mapping to Yahoo may fail for some assets.",
            "Add exchange/vendor crypto price source.",
        ),
        _row(
            11,
            "Does it flag/exclude stablecoins where appropriate?",
            "implemented",
            "Stable-like crypto rows are flagged as non-investable.",
            "Rule-based detection needs periodic review.",
            "Add stablecoin taxonomy source.",
        ),
        _row(
            12,
            "Does it include bonds, bills, treasury/cash proxies?",
            "implemented",
            "SHY, IEF, TLT, AGG, TIP, BIL and SGOV are included as proxies.",
            "ETF proxies differ from direct bonds/bills.",
            "Add Treasury bill and curve data.",
        ),
        _row(
            13,
            "Does it cluster by exchange/region?",
            "partially_implemented",
            "Region exposures and region caps are audited.",
            "Region is constrained, not clustered by exchange.",
            "Add exchange/region cluster diagnostics.",
        ),
        _row(
            14,
            "Does it cluster by asset class?",
            "partially_implemented",
            "Sleeve exposures and caps are audited.",
            "Asset-class grouping is not a statistical cluster.",
            "Add sleeve-level clustering report.",
        ),
        _row(
            15,
            "Does it cluster by correlation?",
            "implemented",
            "Hierarchical correlation clustering is used for selection and diagnostics.",
            "Cluster stability is not yet bootstrapped.",
            "Add cluster stability analysis.",
        ),
        _row(
            16,
            "Does it determine number of clusters using elbow/silhouette or equivalent?",
            "implemented",
            "Cluster diagnostics include within-cluster distance and silhouette values.",
            "Promotion gate does not yet choose k from silhouette automatically.",
            "Use diagnostics to select k explicitly.",
        ),
        _row(
            17,
            "Does it determine holdings per cluster?",
            "partially_implemented",
            "Selection spreads holdings across correlation clusters.",
            "Holdings-per-cluster target is simple and heuristic.",
            "Add formal cluster budget policy.",
        ),
        _row(
            18,
            "Does it enforce diversification across clusters?",
            "implemented",
            "Max cluster weight is audited and enforced for policy-constrained candidate.",
            "Cluster definitions are return-sample dependent.",
            "Add robustness checks across windows.",
        ),
        _row(
            19,
            "Does it compute log returns where appropriate?",
            "implemented",
            "Global returns builder writes log returns.",
            "Not every downstream model consumes log returns yet.",
            "Use log returns in statistical diagnostics where appropriate.",
        ),
        _row(
            20,
            "Does it compute simple returns where portfolio aggregation requires them?",
            "implemented",
            "Global returns builder writes simple returns and portfolio pipeline uses simple aggregation.",
            "Corporate-action quality depends on yfinance adjusted data.",
            "Add vendor adjusted price reconciliation.",
        ),
        _row(
            21,
            "Does it test normality of returns?",
            "implemented",
            "Jarque-Bera normality tests are written per asset.",
            "Multiple-testing adjustment is not yet added.",
            "Add FDR-adjusted summary.",
        ),
        _row(
            22,
            "If returns are non-normal, does it use robust/tail methods instead of forcing normality?",
            "implemented",
            "Historical CVaR, Min CVaR, drawdown and stress tests are used.",
            "No full EVT/GARCH tail model is promoted.",
            "Add EVT/GARCH as research diagnostics.",
        ),
        _row(
            23,
            "Does it estimate covariance using sample covariance?",
            "implemented",
            "Sample covariance is included in estimator comparison.",
            "Sample covariance is fragile in large universes.",
            "Use as benchmark only.",
        ),
        _row(
            24,
            "Does it estimate covariance using shrinkage/Ledoit-Wolf or equivalent?",
            "implemented",
            "Ledoit-Wolf estimator comparison is included.",
            "Not yet integrated into every optimizer.",
            "Route risk optimizers through estimator config.",
        ),
        _row(
            25,
            "Does it estimate covariance using EWMA?",
            "implemented",
            "EWMA covariance is included in comparison.",
            "EWMA span is fixed, not nested-validated.",
            "Add configurable span validation.",
        ),
        _row(
            26,
            "Does it support MLE-style distribution estimation?",
            "partially_implemented",
            "MLE normal covariance proxy is reported.",
            "Full parametric distribution fitting is not implemented.",
            "Add explicit t/normal MLE diagnostics.",
        ),
        _row(
            27,
            "Does it check correlation matrix validity?",
            "implemented",
            "Correlation matrix diagnostics and diagonal checks are available.",
            "Repair logic is limited.",
            "Add nearest-PSD repair report if needed.",
        ),
        _row(
            28,
            "Does it check covariance matrix stability/PSD?",
            "implemented",
            "Estimator comparison reports eigenvalue and PSD checks.",
            "Condition number thresholds are diagnostic only.",
            "Add gate thresholds.",
        ),
        _row(
            29,
            "Equal Weight",
            "implemented",
            "Portfolio model comparison includes Equal Weight.",
            "Benchmark, not automatic proof of optimality.",
            "Keep as baseline.",
        ),
        _row(
            30,
            "Inverse Volatility",
            "implemented",
            "Global master portfolio computes inverse volatility weights.",
            "Can over-allocate defensive assets.",
            "Use constraint audit.",
        ),
        _row(
            31,
            "Min Variance",
            "implemented",
            "Global master portfolio computes Min Variance.",
            "Sensitive to covariance estimate.",
            "Use shrinkage/EWMA variants later.",
        ),
        _row(
            32,
            "Max Sharpe",
            "implemented",
            "Global master portfolio computes shrinkage Max Sharpe candidate.",
            "Expected-return estimates are noisy.",
            "Treat as diagnostic unless robust.",
        ),
        _row(
            33,
            "HRP",
            "partially_implemented",
            "ETF/research layers support HRP; global run lists it when not available.",
            "Not fully wired into this global stock master run.",
            "Integrate HRP with global constraints.",
        ),
        _row(
            34,
            "Risk Parity",
            "partially_implemented",
            "ETF/research layers support Risk Parity; global run lists it when not available.",
            "Not fully wired into this global stock master run.",
            "Integrate risk parity with global constraints.",
        ),
        _row(
            35,
            "Min CVaR",
            "implemented",
            "Global master portfolio computes Min CVaR.",
            "Can become defensive-heavy without constraints.",
            "Use promotion and constraint gates.",
        ),
        _row(
            36,
            "Black-Litterman",
            "blocked_by_data",
            "Global run computes it only when all selected market caps are available.",
            "Equity market caps are mostly missing in current proxy universe.",
            "Add sourced market caps.",
        ),
        _row(
            37,
            "Robust optimization",
            "not_implemented",
            "Model applicability registry documents it.",
            "No uncertainty set or validation yet.",
            "Implement only after clean constraints/data.",
        ),
        _row(
            38,
            "Convex optimization",
            "partially_implemented",
            "Policy-constrained candidate uses linear programming and other optimizers use scipy.",
            "Not all objectives are formal convex programs.",
            "Add convex objective registry.",
        ),
        _row(
            39,
            "Factor modeling",
            "not_implemented",
            "Model applicability registry marks factor model as not implemented.",
            "No factor data or exposure model.",
            "Add vendor/macro/factor inputs.",
        ),
        _row(
            40,
            "Forecast-enhanced optimization",
            "partially_implemented",
            "Forecast outputs exist; global comparison lists forecast-enhanced variants as unavailable.",
            "Forecasts are not promoted into allocation.",
            "Add strict train/test overlay.",
        ),
        _row(
            41,
            "Cluster-balanced optimization",
            "implemented",
            "Cluster-balanced model is computed.",
            "May overweight weak clusters.",
            "Keep as diversification candidate.",
        ),
        _row(
            42,
            "Random portfolio benchmark",
            "implemented",
            "Random portfolios are simulated with reproducible seed.",
            "Random benchmark is not proof of future superiority.",
            "Add larger sensitivity runs.",
        ),
        _row(
            43,
            "ARMA/ARIMA/SARIMA applicability",
            "partially_implemented",
            "Applicability registry and forecast output document optional status.",
            "No automated ARIMA/SARIMA fit in global run.",
            "Add only where stationarity/data support it.",
        ),
        _row(
            44,
            "GARCH volatility modeling applicability",
            "partially_implemented",
            "Registry marks GARCH optional for volatility.",
            "No GARCH estimation in current run.",
            "Add optional volatility diagnostic.",
        ),
        _row(
            45,
            "Linear regression",
            "implemented",
            "Forecast metrics include a rolling mean/random-walk baseline style regression output.",
            "Feature set is simple.",
            "Add validated features.",
        ),
        _row(
            46,
            "Ridge",
            "implemented",
            "Registry marks Ridge implemented in forecast family.",
            "Not separately reported in current global CSV.",
            "Expose per-model metrics.",
        ),
        _row(
            47,
            "Lasso",
            "partially_implemented",
            "Registry marks Lasso optional.",
            "No current global Lasso output.",
            "Run only after feature validation.",
        ),
        _row(
            48,
            "Logistic regression for downside classification",
            "implemented",
            "Classification metrics and AUC are reported for downside diagnostics.",
            "Not a direct trading signal.",
            "Add calibrated probabilities.",
        ),
        _row(
            49,
            "Decision tree",
            "implemented",
            "Registry marks tree model implemented as diagnostic.",
            "Overfit-prone without nested validation.",
            "Report tree metrics only when run.",
        ),
        _row(
            50,
            "Random forest",
            "implemented",
            "Registry marks random forest implemented as diagnostic.",
            "No direct allocation promotion.",
            "Add feature/validation reports.",
        ),
        _row(
            51,
            "Gradient boosting",
            "implemented",
            "Registry marks gradient boosting implemented as diagnostic.",
            "Overfit risk remains.",
            "Add nested validation.",
        ),
        _row(
            52,
            "XGBoost optional adapter",
            "partially_implemented",
            "Registry detects optional package availability.",
            "Not a required dependency.",
            "Run only if dependency and validation exist.",
        ),
        _row(
            53,
            "GBM / sklearn gradient boosting",
            "implemented",
            "Registry includes sklearn gradient boosting.",
            "Not directly promoted into weights.",
            "Expose metrics in forecast league.",
        ),
        _row(
            54,
            "LSTM/RNN optional adapter",
            "not_scientifically_appropriate",
            "Registry treats LSTM/RNN as optional research only.",
            "Current sample/validation does not justify deep allocation.",
            "Do not add until strict validation exists.",
        ),
        _row(
            55,
            "PCA",
            "implemented",
            "PCA explained variance output is generated.",
            "PCA is diagnostic, not alpha proof.",
            "Add factor interpretation.",
        ),
        _row(
            56,
            "Classification metrics",
            "implemented",
            "Classification metrics CSV is generated.",
            "Class imbalance handling is limited.",
            "Add PR AUC/Brier.",
        ),
        _row(
            57,
            "Confusion matrix",
            "implemented",
            "Confusion matrix CSV is generated.",
            "Threshold is simple median score.",
            "Tune threshold only in training windows.",
        ),
        _row(
            58,
            "AUC/ROC",
            "implemented",
            "ROC AUC CSV is generated.",
            "No confidence interval yet.",
            "Add bootstrap AUC CI.",
        ),
        _row(
            59,
            "R2",
            "implemented",
            "Regression metrics include R2.",
            "Low or negative R2 must not be overclaimed.",
            "Use as diagnostic only.",
        ),
        _row(
            60,
            "AIC/BIC where appropriate",
            "partially_implemented",
            "Time-series metrics include AIC/BIC placeholders for optional models.",
            "No ARIMA/GARCH model selection run.",
            "Compute only when model is fitted.",
        ),
        _row(
            61,
            "Train/test split",
            "partially_implemented",
            "Forecast helpers use shifted/rolling diagnostics.",
            "Global forecast layer is not full walk-forward allocation validation.",
            "Add explicit split artifact.",
        ),
        _row(
            62,
            "Walk-forward validation",
            "partially_implemented",
            "Core ETF/challenger pipeline has walk-forward validation.",
            "Global stock master run is current-universe research, not historical point-in-time walk-forward.",
            "Add point-in-time universe history.",
        ),
        _row(
            63,
            "Rolling window validation",
            "partially_implemented",
            "Rolling scores and diagnostics are used.",
            "No complete rolling global master promotion gate.",
            "Add rolling master backtest.",
        ),
        _row(
            64,
            "Random walk benchmark",
            "implemented",
            "Forecast layer reports random-walk baseline.",
            "Benchmark only.",
            "Keep as required comparator.",
        ),
        _row(
            65,
            "VaR",
            "implemented",
            "Risk reports include VaR-style outputs in core and projection layers.",
            "Global gate still needs full unified VaR table.",
            "Add global VaR summary.",
        ),
        _row(
            66,
            "CVaR",
            "implemented",
            "Min CVaR and risk reports include CVaR.",
            "Historical CVaR depends on sample.",
            "Add tail robustness.",
        ),
        _row(
            67,
            "Stress tests",
            "implemented",
            "Global stress test results are generated.",
            "Scenarios are stylized.",
            "Add macro/vendor scenarios.",
        ),
        _row(
            68,
            "Scenario analysis",
            "implemented",
            "Scenario analysis output is generated.",
            "Scenario calibration is simple.",
            "Add macro scenarios.",
        ),
        _row(
            69,
            "Monte Carlo simulation",
            "implemented",
            "Monte Carlo projection output is generated.",
            "Assumption-sensitive.",
            "Add block bootstrap alternatives.",
        ),
        _row(
            70,
            "1/3/6/12 month projection",
            "implemented",
            "Projection script writes horizon-specific CSVs.",
            "Projection is not a guarantee.",
            "Add uncertainty narrative.",
        ),
        _row(
            71,
            "Probability of loss",
            "implemented",
            "Monte Carlo output includes probability of loss.",
            "Based on simulated distribution.",
            "Add bootstrap comparison.",
        ),
        _row(
            72,
            "Drawdown projection",
            "partially_implemented",
            "Drawdown is in risk metrics; projected drawdown is not fully separated.",
            "No dedicated drawdown projection CSV.",
            "Add drawdown simulation output.",
        ),
        _row(
            73,
            "Transaction-cost sensitivity",
            "partially_implemented",
            "Core ETF pipeline has transaction-cost sensitivity; global gate has simple cost assumptions.",
            "Global stock transaction-cost grid is not complete.",
            "Add global cost sensitivity.",
        ),
        _row(
            74,
            "Bootstrap robustness",
            "partially_implemented",
            "Core challenger pipeline has bootstrap robustness.",
            "Global stock master lacks full bootstrap gate.",
            "Add global bootstrap vs Equal Weight.",
        ),
        _row(
            75,
            "Do all portfolio weights sum to 1?",
            "implemented",
            "Portfolio audit and tests verify full weight sums.",
            "Generated outputs should be re-audited after each run.",
            "Keep audit in validation.",
        ),
        _row(
            76,
            "Are negative weights prevented unless shorting is explicitly enabled?",
            "implemented",
            "Global candidates are long-only and audit checks negatives.",
            "No shorting support is exposed.",
            "Keep long-only by default.",
        ),
        _row(
            77,
            "Are max/min weight constraints enforced?",
            "implemented",
            "Max weight and holding bounds are audited; policy candidate enforces caps.",
            "Minimum per-asset weight is only a practical LP lower bound.",
            "Expose min-weight config if needed.",
        ),
        _row(
            78,
            "Can each portfolio have different numbers of assets?",
            "implemented",
            "Candidate weight vectors can have different effective holdings counts.",
            "Selected universe is shared within a run.",
            "Add model-specific selection stage.",
        ),
        _row(
            79,
            "Are asset-class constraints enforced?",
            "implemented",
            "Policy constrained model enforces global equity, defensive, crypto and commodity caps.",
            "Unconstrained variants can violate caps and are labelled.",
            "Do not promote violating variants.",
        ),
        _row(
            80,
            "Are region/exchange constraints enforced?",
            "partially_implemented",
            "Region caps are enforced; exchange caps are not separate.",
            "Exchange-level cap is not implemented.",
            "Add exchange cap if required.",
        ),
        _row(
            81,
            "Are crypto/commodity/bond caps enforced?",
            "implemented",
            "Crypto, commodity and defensive caps are audited and enforced for policy candidate.",
            "Classification depends on source metadata.",
            "Keep source schema strict.",
        ),
        _row(
            82,
            "Are signal-only tickers excluded from investable weights?",
            "implemented",
            "Universe filter excludes signal-only rows from investable assets.",
            "Requires correct source flags.",
            "Audit flags per run.",
        ),
        _row(
            83,
            "Are all displayed/report weights traceable to CSV outputs?",
            "implemented",
            "Weights, asset-class, region and cluster CSVs are generated.",
            "Manual report excerpts must cite full CSV path.",
            "Keep report linked to artifacts.",
        ),
        _row(
            84,
            "Are top-holdings tables labelled partial if not all holdings are shown?",
            "implemented",
            "Report wording labels condensed tables as excerpts.",
            "Needs review whenever report layout changes.",
            "Keep report QA checklist.",
        ),
    ]
    frame = pd.DataFrame(rows)
    invalid = set(frame["status"]) - ALLOWED_STATUS
    if invalid:
        raise ValueError(f"Invalid status values: {sorted(invalid)}")
    return frame


def write_outputs(
    frame: pd.DataFrame, csv_output: str | Path, markdown_output: str | Path
) -> None:
    csv_path = Path(csv_output)
    markdown_path = Path(markdown_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)
    markdown_path.write_text(_to_markdown(frame), encoding="utf-8")


def _row(
    item: int,
    question: str,
    status: str,
    evidence: str,
    limitation: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "item": item,
        "question": question,
        "status": status,
        "evidence": evidence,
        "limitation": limitation,
        "next_action": next_action,
    }


def _to_markdown(frame: pd.DataFrame) -> str:
    counts = frame["status"].value_counts().sort_index()
    lines = [
        "# Global Quant Capability Gap Matrix",
        "",
        "This matrix is intentionally conservative. A capability is marked",
        "`implemented` only when the current repository has code, configuration,",
        "outputs or tests supporting the claim. Proxy-based universes are not",
        "reported as exact market-cap-ranked top-100 universes.",
        "",
        "## Status Summary",
        "",
    ]
    for status, count in counts.items():
        lines.append(f"- `{status}`: {int(count)}")
    lines.extend(
        [
            "",
            "## Matrix",
            "",
            "| # | Question | Status | Evidence | Limitation | Next Action |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in frame.itertuples(index=False):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.item),
                    _escape(row.question),
                    f"`{row.status}`",
                    _escape(row.evidence),
                    _escape(row.limitation),
                    _escape(row.next_action),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|")


def main() -> int:
    args = parse_args()
    matrix = build_matrix()
    write_outputs(matrix, args.csv_output, args.markdown_output)
    print(f"Capability matrix rows: {len(matrix)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
