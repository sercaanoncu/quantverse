"""Audit global QuantVerse outputs for scientific and reporting sanity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROCESSED = Path("data/processed")
UNIVERSE = Path("data/universe/current_global_equity_universe.csv")
TOL = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROCESSED))
    parser.add_argument("--universe-path", default=str(UNIVERSE))
    return parser.parse_args()


def run_audit(
    processed_dir: str | Path = PROCESSED,
    universe_path: str | Path = UNIVERSE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run global scientific sanity checks and return summary, issues, dashboard."""
    processed = Path(processed_dir)
    universe = Path(universe_path)
    issues: list[dict[str, Any]] = []
    issues.extend(_metric_sanity(processed))
    issues.extend(_source_data_sanity(processed, universe))
    issues.extend(_portfolio_sanity(processed))
    issues.extend(_model_sanity(processed))
    issues.extend(_reporting_sanity())
    issue_frame = pd.DataFrame(
        issues,
        columns=[
            "severity",
            "category",
            "evidence_file",
            "evidence_column",
            "what_is_wrong",
            "issue",
            "why_it_matters",
            "promotion_blocker",
            "next_required_fix",
            "recommended_fix",
            "blocks_promotion",
        ],
    )
    summary = _summary(issue_frame)
    dashboard = _dashboard(issue_frame)
    return summary, issue_frame, dashboard


def write_outputs(
    summary: pd.DataFrame,
    issues: pd.DataFrame,
    dashboard: pd.DataFrame,
    processed_dir: str | Path = PROCESSED,
) -> None:
    processed = Path(processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    summary.to_csv(processed / "global_scientific_sanity_summary.csv", index=False)
    issues.to_csv(processed / "global_scientific_sanity_issues.csv", index=False)
    dashboard.to_csv(processed / "global_red_flag_dashboard.csv", index=False)


def _metric_sanity(processed: Path) -> list[dict[str, Any]]:
    issues = []
    models = _read_csv(processed / "global_master_model_comparison.csv")
    for row in models.itertuples(index=False):
        model = str(getattr(row, "Model", "unknown"))
        status = str(getattr(row, "Status", ""))
        if status != "computed":
            continue
        for column, threshold, issue_name in [
            ("CAGR", 1.0, "cagr_above_100pct"),
            ("Annual_Return", 1.0, "annual_return_above_100pct"),
            ("Volatility", 1.0, "volatility_above_100pct"),
        ]:
            value = _num(getattr(row, column, np.nan))
            if pd.notna(value) and abs(value) > threshold:
                issues.append(
                    _issue(
                        "high",
                        "return_risk_scale",
                        "data/processed/global_master_model_comparison.csv",
                        column,
                        f"{model}: {issue_name} ({value:.4f})",
                        "Extreme annualized metrics can indicate leverage-like behavior, local-currency mixing, outliers or unstable return aggregation.",
                        "Keep as red-flagged diagnostic until data, FX and robustness checks support it.",
                        True,
                    )
                )
        total_return = _num(getattr(row, "Total_Return", np.nan))
        if pd.notna(total_return) and abs(total_return) > 100:
            issues.append(
                _issue(
                    "high",
                    "return_risk_scale",
                    "data/processed/global_master_model_comparison.csv",
                    "Total_Return",
                    f"{model}: total_return_above_100x ({total_return:.2f})",
                    "Very large cumulative return is suspicious in a broad global portfolio and must not be presented without caveats.",
                    "Show as suspicious and require point-in-time, FX-normalized robustness before promotion.",
                    True,
                )
            )
        sharpe = _num(getattr(row, "Sharpe", np.nan))
        if pd.notna(sharpe) and sharpe > 3:
            issues.append(
                _issue(
                    "medium",
                    "return_risk_scale",
                    "data/processed/global_master_model_comparison.csv",
                    "Sharpe",
                    f"{model}: sharpe_above_3 ({sharpe:.2f})",
                    "Sharpe above 3 is rare and needs strong validation.",
                    "Explain as suspicious unless independently validated.",
                    False,
                )
            )
        sortino = _num(getattr(row, "Sortino", np.nan))
        if pd.notna(sortino) and sortino > 5:
            issues.append(
                _issue(
                    "medium",
                    "return_risk_scale",
                    "data/processed/global_master_model_comparison.csv",
                    "Sortino",
                    f"{model}: sortino_above_5 ({sortino:.2f})",
                    "Extremely high Sortino can be caused by small downside deviation or outliers.",
                    "Flag and avoid overclaiming.",
                    False,
                )
            )
    normality = _read_csv(processed / "global_normality_tests.csv")
    if (
        "normality_result" in normality
        and normality["normality_result"].astype(str).str.contains("reject").any()
    ):
        issues.append(
            _issue(
                "medium",
                "return_risk_scale",
                "data/processed/global_normality_tests.csv",
                "normality_result",
                "returns_reject_normality",
                "Normality rejection means normal-only interpretation is weak.",
                "Use historical CVaR, stress tests, bootstrap and robust covariance language.",
                False,
            )
        )
    covariance = _read_csv(processed / "global_covariance_estimator_comparison.csv")
    if "condition_number" in covariance:
        unstable = covariance.loc[
            pd.to_numeric(covariance["condition_number"], errors="coerce") > 1e8
        ]
        for row in unstable.itertuples(index=False):
            issues.append(
                _issue(
                    "high",
                    "return_risk_scale",
                    "data/processed/global_covariance_estimator_comparison.csv",
                    "condition_number",
                    f"{getattr(row, 'estimator', 'estimator')}: covariance_condition_number_high",
                    "Ill-conditioned covariance can make optimization unstable.",
                    "Prefer shrinkage/robust covariance and keep optimizer outputs diagnostic.",
                    True,
                )
            )
    return issues


def _source_data_sanity(processed: Path, universe_path: Path) -> list[dict[str, Any]]:
    issues = []
    market_caps = _read_csv(processed / "real_global_universe_market_cap_coverage.csv")
    for row in market_caps.itertuples(index=False):
        sleeve = str(getattr(row, "sleeve", ""))
        rows = int(_num(getattr(row, "rows", 0)) or 0)
        cap_rows = int(_num(getattr(row, "market_cap_rows", 0)) or 0)
        if sleeve.startswith("global_equity") and rows > 0 and cap_rows == 0:
            issues.append(
                _issue(
                    "critical",
                    "source_data",
                    "data/processed/real_global_universe_market_cap_coverage.csv",
                    "market_cap_rows",
                    f"{sleeve}: equity_market_cap_coverage_missing",
                    "Exact market-cap top-100 and Black-Litterman market-cap prior claims are blocked.",
                    "Add dated, sourced market-cap/rank fields.",
                    True,
                )
            )
    fx = _read_csv(processed / "global_fx_normalization_report.csv")
    fx_blocking_statuses = {"not_implemented", "fx_missing", "blocked"}
    if (
        "fx_normalization_status" in fx
        and fx["fx_normalization_status"].astype(str).isin(fx_blocking_statuses).any()
    ):
        issues.append(
            _issue(
                "critical",
                "fx_currency",
                "data/processed/global_fx_normalization_report.csv",
                "fx_normalization_status",
                "fx_normalization_incomplete",
                "Non-USD local returns cannot be treated as USD portfolio returns.",
                "Implement FX conversion or keep global USD promotion blocked.",
                True,
            )
        )
    required_fx_columns = {
        "currency",
        "fx_ticker",
        "quote_direction",
        "inversion_required",
        "fx_normalization_status",
    }
    if not fx.empty and not required_fx_columns.issubset(fx.columns):
        issues.append(
            _issue(
                "high",
                "fx_currency",
                "data/processed/global_fx_normalization_report.csv",
                "columns",
                "fx_report_schema_incomplete",
                "FX audit evidence needs currency, ticker, quote direction and status fields.",
                "Regenerate FX report with explicit source and conversion metadata.",
                True,
            )
        )
    if not (processed / "global_security_simple_returns_usd.csv").exists():
        issues.append(
            _issue(
                "critical",
                "fx_currency",
                "data/processed/global_security_simple_returns_usd.csv",
                "file",
                "usd_return_matrix_missing",
                "A promoted global USD portfolio requires an explicitly USD-normalized return matrix.",
                "Build global_security_simple_returns_usd.csv before promotion.",
                True,
            )
        )
    coverage = _read_csv(processed / "global_returns_coverage_report.csv")
    if "included_in_returns" in coverage:
        missing = coverage.loc[~coverage["included_in_returns"].astype(bool)]
        if not missing.empty:
            issues.append(
                _issue(
                    "medium",
                    "source_data",
                    "data/processed/global_returns_coverage_report.csv",
                    "included_in_returns",
                    f"price_coverage_gaps: {len(missing)} assets excluded",
                    "Coverage gaps can bias selected universe and comparisons.",
                    "Review ticker mapping/provider coverage.",
                    False,
                )
            )
    outliers = _read_csv(processed / "global_return_outlier_report.csv")
    if not outliers.empty:
        issues.append(
            _issue(
                "medium",
                "source_data",
                "data/processed/global_return_outlier_report.csv",
                "return",
                f"large_return_outliers_detected: {len(outliers)} rows",
                "Large daily returns can dominate annualized metrics and optimizers.",
                "Show outlier warning and inspect affected tickers.",
                False,
            )
        )
    source_coverage = _read_csv(processed / "real_global_universe_source_coverage.csv")
    if "source_urls" in source_coverage and "rows" in source_coverage:
        missing_url = source_coverage.loc[
            pd.to_numeric(source_coverage["source_urls"], errors="coerce")
            < pd.to_numeric(source_coverage["rows"], errors="coerce")
        ]
        for row in missing_url.itertuples(index=False):
            issues.append(
                _issue(
                    "high",
                    "source_data",
                    "data/processed/real_global_universe_source_coverage.csv",
                    "source_urls",
                    f"{getattr(row, 'sleeve', 'sleeve')}: source_url_missing",
                    "Unsourced rows are not audit-ready.",
                    "Add source URL or manual-review flag.",
                    True,
                )
            )
    universe = _read_csv(universe_path)
    if not universe.empty:
        dupes = (
            universe.loc[universe["ticker"].astype(str).duplicated(keep=False)]
            if "ticker" in universe
            else pd.DataFrame()
        )
        if not dupes.empty:
            issues.append(
                _issue(
                    "medium",
                    "source_data",
                    str(universe_path),
                    "ticker",
                    f"duplicate_tickers_in_universe: {dupes['ticker'].nunique()}",
                    "Duplicates can distort weights and source counts.",
                    "Deduplicate or separate share classes explicitly.",
                    False,
                )
            )
    weights = _read_csv(processed / "global_master_candidate_weights.csv")
    if not weights.empty and not universe.empty:
        final_model = _decision(processed).get("final_model", "")
        final_weights = weights.loc[weights["Model"].astype(str).eq(str(final_model))]
        meta = (
            universe.drop_duplicates("ticker", keep="first").set_index("ticker")
            if "ticker" in universe
            else pd.DataFrame()
        )
        if not final_weights.empty and not meta.empty:
            stable = (
                meta.reindex(final_weights["Ticker"].astype(str))["notes"]
                .fillna("")
                .astype(str)
                .str.contains("stable_like=True", case=False, na=False)
            )
            if stable.any():
                issues.append(
                    _issue(
                        "critical",
                        "source_data",
                        str(universe_path),
                        "notes",
                        "stablecoin_like_asset_in_final_risk_allocation",
                        "Stablecoins should not enter risk-asset allocation unless explicitly configured.",
                        "Exclude or separately label stablecoin/cash assets.",
                        True,
                    )
                )
    return issues


def _portfolio_sanity(processed: Path) -> list[dict[str, Any]]:
    issues = []
    weights = _read_csv(processed / "global_master_candidate_weights.csv")
    if not weights.empty:
        for model, frame in weights.groupby("Model"):
            numeric = pd.to_numeric(frame["Weight"], errors="coerce")
            total = float(numeric.sum())
            if abs(total - 1.0) > TOL:
                issues.append(
                    _issue(
                        "critical",
                        "portfolio_construction",
                        "data/processed/global_master_candidate_weights.csv",
                        "Weight",
                        f"{model}: weight_sum_not_one ({total:.8f})",
                        "Long-only full weight vectors must sum to 1.",
                        "Fix optimizer/output normalization.",
                        True,
                    )
                )
            if numeric.isna().any() or np.isinf(numeric.fillna(0.0).to_numpy()).any():
                issues.append(
                    _issue(
                        "critical",
                        "portfolio_construction",
                        "data/processed/global_master_candidate_weights.csv",
                        "Weight",
                        f"{model}: non_finite_weight",
                        "Non-finite weights invalidate portfolio math.",
                        "Fix weight generation.",
                        True,
                    )
                )
            if (numeric < -TOL).any():
                issues.append(
                    _issue(
                        "critical",
                        "portfolio_construction",
                        "data/processed/global_master_candidate_weights.csv",
                        "Weight",
                        f"{model}: negative_weight_without_shorting",
                        "Shorting is not enabled for this portfolio.",
                        "Clip or explicitly configure shorting.",
                        True,
                    )
                )
            dust = int(((numeric > 0) & (numeric < 0.001)).sum())
            if dust > max(20, len(frame) * 0.25):
                issues.append(
                    _issue(
                        "medium",
                        "portfolio_construction",
                        "data/processed/global_master_candidate_weights.csv",
                        "Weight",
                        f"{model}: excessive_dust_weights ({dust})",
                        "Many tiny weights can make a portfolio operationally noisy and economically hard to interpret.",
                        "Add min-weight or sparse selection policy.",
                        False,
                    )
                )
            near_cap = int((numeric >= 0.099).sum())
            if near_cap >= 5:
                issues.append(
                    _issue(
                        "medium",
                        "portfolio_construction",
                        "data/processed/global_master_candidate_weights.csv",
                        "Weight",
                        f"{model}: many_weights_at_max_cap ({near_cap})",
                        "Many max-cap positions indicate constraints are binding and should be explained.",
                        "Show max-cap warning in report.",
                        False,
                    )
                )
            effective_n = _effective_holdings(numeric)
            if effective_n < 10:
                issues.append(
                    _issue(
                        "medium",
                        "portfolio_construction",
                        "data/processed/global_master_candidate_weights.csv",
                        "Weight",
                        f"{model}: low_effective_holdings ({effective_n:.2f})",
                        "Formal holdings count can hide concentration.",
                        "Report effective number of holdings.",
                        False,
                    )
                )
    for filename, label in [
        ("global_master_asset_class_weights.csv", "asset_class_weights"),
        ("global_master_region_weights.csv", "region_weights"),
        ("global_master_cluster_weights.csv", "cluster_weights"),
    ]:
        frame = _read_csv(processed / filename)
        if not frame.empty and "Weight" in frame:
            total = float(pd.to_numeric(frame["Weight"], errors="coerce").sum())
            if abs(total - 1.0) > TOL:
                issues.append(
                    _issue(
                        "high",
                        "portfolio_construction",
                        f"data/processed/{filename}",
                        "Weight",
                        f"{label}_sum_not_one ({total:.8f})",
                        "Exposure breakdowns must reconcile to final weights.",
                        "Fix exposure table generation.",
                        True,
                    )
                )
            max_weight = float(pd.to_numeric(frame["Weight"], errors="coerce").max())
            if max_weight > 0.35 + TOL:
                issues.append(
                    _issue(
                        "medium",
                        "portfolio_construction",
                        f"data/processed/{filename}",
                        "Weight",
                        f"{label}_dominance ({max_weight:.2%})",
                        "Dominant sleeve/region/cluster can be economically concentrated.",
                        "Explain or tighten constraint.",
                        False,
                    )
                )
    constraint = _read_csv(processed / "global_master_constraint_audit.csv")
    if not constraint.empty:
        final_model = _decision(processed).get("final_model", "")
        final = constraint.loc[constraint["Model"].astype(str).eq(str(final_model))]
        if not final.empty and not bool(final["All_Constraints_Pass"].iloc[0]):
            issues.append(
                _issue(
                    "critical",
                    "portfolio_construction",
                    "data/processed/global_master_constraint_audit.csv",
                    "All_Constraints_Pass",
                    "final_model_constraint_failure",
                    "A final user-facing candidate cannot violate hard constraints.",
                    "Use a constrained candidate or keep not promoted.",
                    True,
                )
            )
    return issues


def _model_sanity(processed: Path) -> list[dict[str, Any]]:
    issues = []
    models = _read_csv(processed / "global_master_model_comparison.csv")
    if not models.empty:
        for name in ["Black-Litterman", "HRP", "Risk Parity"]:
            row = models.loc[models["Model"].astype(str).eq(name)]
            if not row.empty and not row["Status"].astype(str).eq("computed").any():
                severity = "high" if name == "Black-Litterman" else "medium"
                issues.append(
                    _issue(
                        severity,
                        "model_validity",
                        "data/processed/global_master_model_comparison.csv",
                        "Status",
                        f"{name}: not_computed_in_global_run",
                        "Unavailable model rows must not be described as executed portfolio evidence.",
                        "Explain skipped/blocked status in the report.",
                        name == "Black-Litterman",
                    )
                )
    time_series = _read_csv(processed / "global_forecast_time_series_metrics.csv")
    if not time_series.empty and "Status" in time_series:
        placeholder = (
            time_series["Status"]
            .astype(str)
            .str.contains("not_run|no_aic", case=False, na=False)
        )
        if placeholder.any():
            issues.append(
                _issue(
                    "low",
                    "model_validity",
                    "data/processed/global_forecast_time_series_metrics.csv",
                    "AIC/BIC",
                    "aic_bic_not_real_model_selection",
                    "AIC/BIC are meaningful only for fitted likelihood-based models.",
                    "Keep optional ARIMA/GARCH rows clearly labelled as not run.",
                    False,
                )
            )
    applicability = _read_csv(processed / "model_applicability_matrix.csv")
    if not applicability.empty:
        deep_or_rl = applicability.loc[
            applicability["model"]
            .astype(str)
            .str.contains("LSTM|Reinforcement", case=False, na=False)
        ]
        bad = deep_or_rl.loc[
            ~deep_or_rl["current_status"]
            .astype(str)
            .str.contains("not_appropriate|optional", case=False, na=False)
        ]
        if not bad.empty:
            issues.append(
                _issue(
                    "high",
                    "model_validity",
                    "data/processed/model_applicability_matrix.csv",
                    "current_status",
                    "deep_or_rl_model_overclaimed",
                    "Deep/RL allocation engines need strict validation and are not production-ready here.",
                    "Mark as optional/not appropriate.",
                    True,
                )
            )
    regression = _read_csv(processed / "global_forecast_regression_metrics.csv")
    if "R2" in regression:
        low_r2 = regression.loc[pd.to_numeric(regression["R2"], errors="coerce") < 0]
        if not low_r2.empty:
            issues.append(
                _issue(
                    "medium",
                    "model_validity",
                    "data/processed/global_forecast_regression_metrics.csv",
                    "R2",
                    "negative_regression_r2",
                    "Negative R2 means the regression diagnostic is weak relative to a baseline.",
                    "Do not use forecast model as allocation signal.",
                    False,
                )
            )
    classification = _read_csv(processed / "global_forecast_classification_metrics.csv")
    if "ROC_AUC" in classification:
        weak_auc = classification.loc[
            pd.to_numeric(classification["ROC_AUC"], errors="coerce").between(
                0.45, 0.55
            )
        ]
        if not weak_auc.empty:
            issues.append(
                _issue(
                    "medium",
                    "model_validity",
                    "data/processed/global_forecast_classification_metrics.csv",
                    "ROC_AUC",
                    "classification_auc_near_random",
                    "AUC near 0.5 has little discriminative power.",
                    "Keep classification model diagnostic only.",
                    False,
                )
            )
    return issues


def _reporting_sanity() -> list[dict[str, Any]]:
    issues = []
    old_report = Path(
        "output/reports/quantverse_real_global_stock_master_presentation.md"
    )
    if old_report.exists():
        text = old_report.read_text(encoding="utf-8", errors="ignore")
        if "Unnamed: 0" in text:
            issues.append(
                _issue(
                    "medium",
                    "reporting",
                    str(old_report),
                    "markdown",
                    "old_presentation_shows_unnamed_columns",
                    "Internal dataframe index columns confuse users.",
                    "Drop index columns from visual report and Excel.",
                    False,
                )
            )
        if " / " in text:
            issues.append(
                _issue(
                    "medium",
                    "reporting",
                    str(old_report),
                    "markdown",
                    "old_presentation_contains_one_line_dataframe_dumps",
                    "One-line dataframe dumps are hard to understand.",
                    "Replace with charts and short Turkish explanations.",
                    False,
                )
            )
    return issues


def _summary(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(
            [
                {
                    "total_issues": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "promotion_blockers": 0,
                    "status": "passed",
                }
            ]
        )
    counts = issues["severity"].value_counts()
    return pd.DataFrame(
        [
            {
                "total_issues": int(len(issues)),
                "critical": int(counts.get("critical", 0)),
                "high": int(counts.get("high", 0)),
                "medium": int(counts.get("medium", 0)),
                "low": int(counts.get("low", 0)),
                "promotion_blockers": int(
                    issues["blocks_promotion"].astype(bool).sum()
                ),
                "status": "red_flags_present",
            }
        ]
    )


def _dashboard(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(
            columns=["category", "severity", "issue_count", "promotion_blockers"]
        )
    return (
        issues.groupby(["category", "severity"], as_index=False)
        .agg(
            issue_count=("issue", "count"),
            promotion_blockers=("blocks_promotion", "sum"),
        )
        .sort_values(["category", "severity"])
    )


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).drop(columns=["Unnamed: 0"], errors="ignore")


def _decision(processed: Path) -> dict[str, Any]:
    path = processed / "global_master_decision_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: Any) -> float:
    return float(pd.to_numeric(value, errors="coerce"))


def _effective_holdings(weights: pd.Series) -> float:
    numeric = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    denom = float((numeric**2).sum())
    return float(1.0 / denom) if denom > 0 else 0.0


def _issue(
    severity: str,
    category: str,
    evidence_file: str,
    evidence_column: str,
    issue: str,
    why_it_matters: str,
    recommended_fix: str,
    blocks_promotion: bool,
) -> dict[str, object]:
    return {
        "severity": severity,
        "category": category,
        "evidence_file": evidence_file,
        "evidence_column": evidence_column,
        "what_is_wrong": issue,
        "issue": issue,
        "why_it_matters": why_it_matters,
        "promotion_blocker": bool(blocks_promotion),
        "next_required_fix": recommended_fix,
        "recommended_fix": recommended_fix,
        "blocks_promotion": bool(blocks_promotion),
    }


def main() -> int:
    args = parse_args()
    summary, issues, dashboard = run_audit(args.processed_dir, args.universe_path)
    write_outputs(summary, issues, dashboard, args.processed_dir)
    print(
        "Scientific sanity issues: "
        f"{int(summary['total_issues'].iloc[0])}; "
        f"promotion blockers: {int(summary['promotion_blockers'].iloc[0])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
