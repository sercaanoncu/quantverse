"""Build user requirement traceability outputs for the visual audit sprint."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path("data/processed")
AUDIT_DIR = Path("docs/audit")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--audit-dir", default=str(AUDIT_DIR))
    return parser.parse_args()


def build_traceability() -> pd.DataFrame:
    """Return reconstructed user requirement traceability matrix."""
    rows = [
        _row(
            1,
            "Real stocks must enter the analysis.",
            "met",
            "data/processed/current_global_universe_summary.csv",
            "global_equity_* rows",
            "Real current proxy universe has stock rows.",
            "No exact historical point-in-time membership.",
            "Keep source labels visible.",
            True,
        ),
        _row(
            2,
            "NASDAQ and NYSE must be represented separately.",
            "partially_met",
            "data/universe/sources/nasdaq_top100_candidates.csv; data/universe/sources/nyse_top100_candidates.csv",
            "sleeve",
            "Separate sleeves exist.",
            "NYSE file is S&P 100 proxy, not pure NYSE top-100.",
            "Add exchange-filtered market-cap-ranked NYSE source.",
            False,
        ),
        _row(
            3,
            "Europe, Germany, UK, BIST, Japan and China/HK must be represented.",
            "met",
            "data/processed/current_global_universe_summary.csv",
            "sleeve rows",
            "All requested regions have nonzero rows.",
            "Several are index proxies.",
            "Keep proxy warning.",
            True,
        ),
        _row(
            4,
            "Gold, silver, oil, platinum and copper must be represented.",
            "met",
            "data/universe/sources/commodity_candidates.csv",
            "ticker/proxy_type",
            "Commodity proxies are included.",
            "ETF/fund proxies differ from spot/futures.",
            "Explain proxy_type.",
            True,
        ),
        _row(
            5,
            "Crypto top 100 must be represented.",
            "met",
            "data/universe/sources/crypto_top100_candidates.csv",
            "source_method",
            "CoinGecko-enriched crypto rows exist.",
            "Yahoo ticker mapping can fail.",
            "Keep coverage report.",
            True,
        ),
        _row(
            6,
            "Bonds, bills and cash proxies must be represented.",
            "met",
            "data/universe/sources/bond_bill_candidates.csv",
            "ticker/proxy_type",
            "Defensive proxies exist.",
            "ETF proxy risk differs from direct bills/bonds.",
            "Explain duration/proxy risk.",
            True,
        ),
        _row(
            7,
            "Distinguish exact market-cap top-100 from index proxies.",
            "met",
            "source_method columns",
            "source_method",
            "index_proxy/manual_review_required/api_market_cap_enriched are explicit.",
            "Visual report was previously too table-heavy.",
            "Add chart-led source method coverage.",
            True,
        ),
        _row(
            8,
            "Do not claim exact top-100 when cap/rank evidence is missing.",
            "met",
            "data/processed/global_exact_proxy_classification_report.csv",
            "market_cap_rows",
            "Equity cap coverage gap is visible.",
            "Exact top-100 still blocked.",
            "Keep blocker prominent.",
            True,
        ),
        _row(
            9,
            "Region/sleeve clustering must be shown.",
            "partially_met",
            "global_master_asset_class_weights.csv; global_master_region_weights.csv",
            "Weight",
            "Sleeve and region weights are shown.",
            "Exchange-level clustering is not separate.",
            "Add charts.",
            True,
        ),
        _row(
            10,
            "Correlation clustering must be shown.",
            "met",
            "global_cluster_membership.csv",
            "cluster",
            "Correlation clusters exist.",
            "Cluster stability not bootstrapped.",
            "Add cluster count chart.",
            True,
        ),
        _row(
            11,
            "Number of clusters must be justified.",
            "partially_met",
            "global_cluster_diagnostics.csv",
            "silhouette_score",
            "Elbow/silhouette diagnostics exist.",
            "Selection rule is still heuristic.",
            "Chart silhouette and disclose limitation.",
            True,
        ),
        _row(
            12,
            "Holdings per cluster must be reported.",
            "met",
            "global_cluster_membership.csv",
            "cluster counts",
            "Membership counts can be computed.",
            "Full cluster table is dense.",
            "Chart counts.",
            True,
        ),
        _row(
            13,
            "Covariance estimation must be audited.",
            "met",
            "global_covariance_estimator_comparison.csv",
            "condition_number/psd_check",
            "Sample, MLE, Ledoit-Wolf and EWMA are compared.",
            "Some condition numbers are red flags.",
            "Flag condition number.",
            True,
        ),
        _row(
            14,
            "Simple and log return policy must be clear.",
            "met",
            "docs/data/global_returns_fx_policy.md",
            "policy text",
            "Policy is documented.",
            "Needs plain Turkish in report.",
            "Add Turkish explanation.",
            True,
        ),
        _row(
            15,
            "Normality and stationarity diagnostics must be run and interpreted.",
            "met",
            "global_normality_tests.csv; global_stationarity_tests.csv",
            "normality_result/stationarity_result",
            "Diagnostics exist.",
            "Raw counts need interpretation.",
            "Add charts and red flags.",
            True,
        ),
        _row(
            16,
            "Non-normal returns trigger robust/tail-aware interpretation.",
            "met",
            "global_scientific_sanity_issues.csv",
            "issue",
            "Sanity audit flags non-normality and tail-risk need.",
            "No full EVT/GARCH yet.",
            "Keep limitation.",
            True,
        ),
        _row(
            17,
            "Models must be run only where scientifically appropriate.",
            "met",
            "model_applicability_matrix.csv",
            "current_status",
            "Applicability registry exists.",
            "Could be hidden in old report.",
            "Add visual summary.",
            True,
        ),
        _row(
            18,
            "Every full portfolio must have weights summing to 1.",
            "met",
            "portfolio_weight_sum_audit.csv",
            "weight_sum",
            "Audit verifies weight sums.",
            "Generated outputs need re-audit after each run.",
            "Keep sanity script.",
            True,
        ),
        _row(
            19,
            "Negative weights must be blocked unless shorting is explicit.",
            "met",
            "portfolio_logic_audit_issues.csv",
            "negative weight issue",
            "Long-only checks exist.",
            "No shorting module.",
            "Keep long-only.",
            True,
        ),
        _row(
            20,
            "Different portfolios may have different holding counts.",
            "met",
            "global_master_constraint_audit.csv",
            "Holdings_Count",
            "Different counts are reported.",
            "Selected universe shared within run.",
            "Explain.",
            True,
        ),
        _row(
            21,
            "Risk minimization and return seeking must be separated.",
            "partially_met",
            "global_master_model_comparison.csv",
            "Model/Status",
            "Models are labelled, but old report was dense.",
            "Need clearer narrative.",
            "Add chart-led explanation.",
            True,
        ),
        _row(
            22,
            "Forward projections must exist.",
            "met",
            "global_portfolio_projection_*.csv",
            "Horizon_Months",
            "1/3/6/12M outputs exist.",
            "Simulation assumptions are not forecasts.",
            "Caption as scenario estimates.",
            True,
        ),
        _row(
            23,
            "Monte Carlo simulation must exist.",
            "met",
            "global_monte_carlo_projection.csv",
            "N_Simulations",
            "Monte Carlo output exists.",
            "No guarantee.",
            "Add percentile chart.",
            True,
        ),
        _row(
            24,
            "Stress testing must exist.",
            "met",
            "global_stress_test_results.csv",
            "Scenario",
            "Stress output exists.",
            "Stylized shocks.",
            "Caption limitations.",
            True,
        ),
        _row(
            25,
            "Train/test or walk-forward validation must be labelled clearly.",
            "partially_met",
            "model_applicability_matrix.csv",
            "current_status",
            "Forecast diagnostics exist.",
            "Global master is not point-in-time walk-forward.",
            "Prominent warning.",
            True,
        ),
        _row(
            26,
            "Confusion matrix/AUC only for classification.",
            "met",
            "global_forecast_confusion_matrix.csv; global_forecast_roc_auc.csv",
            "Task_Type/status",
            "Classification outputs are downside diagnostics.",
            "Threshold is simple.",
            "Keep warning.",
            True,
        ),
        _row(
            27,
            "R2/RMSE/MAE only for regression.",
            "met",
            "global_forecast_regression_metrics.csv",
            "RMSE/MAE/R2",
            "Regression metrics are separate.",
            "Weak R2 must not be overclaimed.",
            "Flag suspicious/weak metrics.",
            True,
        ),
        _row(
            28,
            "AIC/BIC only for models that support it.",
            "met",
            "global_forecast_time_series_metrics.csv",
            "Status",
            "Optional ARIMA/GARCH row is not run.",
            "NaN may confuse users.",
            "Explain in report.",
            True,
        ),
        _row(
            29,
            "Random portfolios must be compared with candidates.",
            "met",
            "global_master_random_portfolio_benchmark.csv",
            "Sharpe/CAGR",
            "10,000 random portfolios exist.",
            "Random benchmark is not future proof.",
            "Add histogram.",
            True,
        ),
        _row(
            30,
            "PDF/presentation must be understandable with charts, not raw tables.",
            "partially_met",
            "output/pdf/quantverse_visual_scientific_audit_report.pdf",
            "figures",
            "This sprint creates chart-led outputs.",
            "Requires QA.",
            "Generate visual report.",
            True,
        ),
        _row(
            31,
            "Excel workbook must have START_HERE and plain Turkish.",
            "partially_met",
            "output/excel/quantverse_explainable_global_stock_output.xlsx",
            "START_HERE",
            "This sprint creates workbook.",
            "Depends on artifact-tool export.",
            "Generate workbook.",
            True,
        ),
        _row(
            32,
            "Scientific errors, economic nonsense and suspicious metrics must be flagged.",
            "met",
            "global_scientific_sanity_issues.csv",
            "severity/category",
            "Sanity audit flags suspicious metrics.",
            "Not all issues are fixed immediately.",
            "Prioritize blockers.",
            True,
        ),
        _row(
            33,
            "Nothing should be promoted if FX/source/data quality blocks it.",
            "met",
            "global_master_decision_summary.json",
            "promotion_decision",
            "Decision remains not promoted.",
            "FX and market-cap blockers remain.",
            "Do not promote until fixed.",
            True,
        ),
        _row(
            34,
            "NASDAQ top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/nasdaq_top100_candidates.csv",
            "source_method/market_cap_rank",
            "NASDAQ-100 current constituent proxy exists.",
            "Not exchange-wide exact market-cap-ranked NASDAQ top 100.",
            "Add dated exchange-filtered market-cap-ranked NASDAQ source.",
            True,
        ),
        _row(
            35,
            "NYSE top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/nyse_top100_candidates.csv",
            "source_method/market_cap_rank",
            "S&P 100 large-cap proxy exists.",
            "Not pure NYSE market-cap-ranked top 100.",
            "Add dated NYSE market-cap-ranked source.",
            True,
        ),
        _row(
            36,
            "Europe top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/europe_top100_candidates.csv",
            "source_method/market_cap_rank",
            "Europe index proxy exists.",
            "Not broad Europe exact top-100 market-cap ranking.",
            "Add sourced Europe market-cap-ranked universe.",
            True,
        ),
        _row(
            37,
            "Germany top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/germany_top100_candidates.csv",
            "source_method/market_cap_rank",
            "Germany index proxy exists.",
            "DAX-style proxy is not Germany exact top 100.",
            "Add DAX/MDAX or market-cap-ranked Germany source.",
            True,
        ),
        _row(
            38,
            "UK top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/uk_top100_candidates.csv",
            "source_method/market_cap_rank",
            "FTSE 100-style proxy exists.",
            "Current constituents are not point-in-time historical evidence.",
            "Add dated membership and market-cap/rank evidence.",
            True,
        ),
        _row(
            39,
            "BIST top 100 / BIST 100 distinction must be explicit.",
            "met",
            "data/universe/sources/turkey_top100_candidates.csv",
            "source_method/notes",
            "BIST 100 current proxy is labelled.",
            "Not historical point-in-time membership.",
            "Add dated BIST membership history.",
            True,
        ),
        _row(
            40,
            "Japan top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/japan_top100_candidates.csv",
            "source_method/market_cap_rank",
            "Japan index proxy exists.",
            "Not exact market-cap-ranked Japan top 100.",
            "Add sourced Japan market-cap-ranked universe.",
            True,
        ),
        _row(
            41,
            "China/HK top 100 must be labelled as exact or proxy.",
            "partially_met",
            "data/universe/sources/china_hk_top100_candidates.csv",
            "source_method/market_cap_rank",
            "China/HK index proxy exists.",
            "Not exact market-cap-ranked China/HK top 100.",
            "Add sourced China/HK market-cap-ranked universe.",
            True,
        ),
    ]
    return pd.DataFrame(rows)


def write_outputs(
    matrix: pd.DataFrame,
    output_dir: str | Path = OUTPUT_DIR,
    audit_dir: str | Path = AUDIT_DIR,
) -> None:
    out = Path(output_dir)
    audit = Path(audit_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(out / "user_requirement_traceability_matrix.csv", index=False)
    (audit / "user_requirement_traceability_matrix.md").write_text(
        _markdown(matrix), encoding="utf-8"
    )


def _row(
    item: int,
    requirement: str,
    status: str,
    evidence_file: str,
    evidence_column_or_section: str,
    current_evidence: str,
    current_limitation: str,
    required_fix: str,
    sprint_fixes_it: bool,
) -> dict[str, object]:
    return {
        "item": item,
        "requirement": requirement,
        "status": status,
        "evidence_file": evidence_file,
        "evidence_column_or_section": evidence_column_or_section,
        "current_evidence": current_evidence,
        "current_limitation": current_limitation,
        "required_fix": required_fix,
        "this_sprint_fixes_it": bool(sprint_fixes_it),
    }


def _markdown(matrix: pd.DataFrame) -> str:
    lines = [
        "# User Requirement Traceability Matrix",
        "",
        "This matrix reconstructs the user's requirements and maps each one to evidence, limitation and sprint action.",
        "",
        "## Status Summary",
        "",
    ]
    for status, count in matrix["status"].value_counts().sort_index().items():
        lines.append(f"- `{status}`: {int(count)}")
    lines.extend(
        [
            "",
            "## Requirements",
            "",
            "| # | Requirement | Status | Evidence | Limitation | Sprint Fix |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in matrix.itertuples(index=False):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.item),
                    _escape(row.requirement),
                    f"`{row.status}`",
                    _escape(row.evidence_file),
                    _escape(row.current_limitation),
                    str(row.this_sprint_fixes_it),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|")


def main() -> int:
    args = parse_args()
    matrix = build_traceability()
    write_outputs(matrix, args.output_dir, args.audit_dir)
    print(f"Requirement rows: {len(matrix)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
