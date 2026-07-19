"""Audit global QuantVerse outputs for scientific and reporting sanity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.data_pipeline.security_universe import (
    REQUIRED_UNIVERSE_COLUMNS,
    stablecoin_like_mask,
    unverified_crypto_price_mapping_mask,
    validate_investable_vs_signal_flags,
)

PROCESSED = Path("data/processed")
UNIVERSE = Path("data/universe/current_global_equity_universe.csv")
TOL = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROCESSED))
    parser.add_argument("--output-dir", dest="processed_dir")
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
    issues.extend(_selection_evidence_sanity(processed))
    issues.extend(_source_data_sanity(processed, universe))
    issues.extend(_portfolio_sanity(processed))
    issues.extend(_model_sanity(processed))
    issues.extend(_reporting_sanity())
    issues.extend(_governance_readiness_sanity(processed, universe))
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
            "evidence_scope",
            "decision_scope",
            "blocks_v2_public_data_model",
            "blocks_institutional_global_master",
            "blocks_active_challenger_promotion",
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
            estimator = str(getattr(row, "estimator", "estimator"))
            estimator_is_used = "ledoit" in estimator.lower()
            issues.append(
                _issue(
                    "high" if estimator_is_used else "medium",
                    "return_risk_scale",
                    "data/processed/global_covariance_estimator_comparison.csv",
                    "condition_number",
                    f"{estimator}: covariance_condition_number_high",
                    "Ill-conditioned covariance can make optimization unstable.",
                    (
                        "Repair the covariance input before allocation."
                        if estimator_is_used
                        else "Keep this estimator diagnostic; allocation uses the "
                        "labelled shrinkage estimator."
                    ),
                    estimator_is_used,
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
    exact_proxy = _read_csv(processed / "global_exact_proxy_classification_report.csv")
    if not exact_proxy.empty and "classification" in exact_proxy:
        unsupported = exact_proxy.loc[
            ~exact_proxy["classification"]
            .astype(str)
            .eq("exact_market_cap_rank_supported")
        ]
        for row in unsupported.itertuples(index=False):
            sleeve = str(getattr(row, "sleeve", ""))
            reason = str(getattr(row, "reason", "Exact support is incomplete."))
            issues.append(
                _issue(
                    "critical" if sleeve.startswith("global_equity") else "high",
                    "exact_proxy",
                    "data/processed/global_exact_proxy_classification_report.csv",
                    "classification",
                    "unsupported_exact_top100_claim",
                    f"{sleeve}: {reason}",
                    "Keep sleeve as proxy/manual-review until market-cap/rank/source/provider/as-of evidence is complete.",
                    True,
                )
            )
    elif exact_proxy.empty:
        issues.append(
            _issue(
                "high",
                "exact_proxy",
                "data/processed/global_exact_proxy_classification_report.csv",
                "file",
                "exact_proxy_classification_report_missing",
                "Reports cannot prove whether sleeves are exact top-100 or proxy-only.",
                "Run scripts/validate_real_global_universe.py before promotion.",
                True,
            )
        )
    market_cap_blockers = _read_csv(processed / "global_market_cap_rank_blockers.csv")
    if not market_cap_blockers.empty and "issue" in market_cap_blockers:
        blocking_count = int(len(market_cap_blockers))
        issues.append(
            _issue(
                "critical",
                "exact_proxy",
                "data/processed/global_market_cap_rank_blockers.csv",
                "issue",
                f"market_cap_rank_blockers_present: {blocking_count}",
                "Exact top-100 and Black-Litterman claims remain blocked while market-cap/rank evidence issues exist.",
                "Populate sourced evidence fields or keep the affected sleeves blocked/proxy-only.",
                True,
            )
        )
    bl_report = _read_csv(processed / "global_black_litterman_prerequisite_report.csv")
    if (
        not bl_report.empty
        and "black_litterman_prior_valid" in bl_report
        and not bl_report["black_litterman_prior_valid"]
        .fillna(False)
        .astype(bool)
        .all()
    ):
        issues.append(
            _issue(
                "critical",
                "black_litterman",
                "data/processed/global_black_litterman_prerequisite_report.csv",
                "black_litterman_prior_valid",
                "black_litterman_priors_blocked",
                "Black-Litterman requires valid sourced market-cap priors for every required asset.",
                "Do not run Black-Litterman as allocation evidence until valid priors exist.",
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
        missing_schema = [
            column for column in REQUIRED_UNIVERSE_COLUMNS if column not in universe
        ]
        if missing_schema:
            issues.append(
                _issue(
                    "critical",
                    "source_data",
                    str(universe_path),
                    "schema",
                    "universe_schema_incomplete: " + ", ".join(missing_schema),
                    "Eligibility, source and security-identity gates cannot be audited against an incomplete universe schema.",
                    "Regenerate the canonical universe with the required schema.",
                    True,
                )
            )
        else:
            eligibility_issues = validate_investable_vs_signal_flags(universe)
            if not eligibility_issues.empty:
                issues.append(
                    _issue(
                        "critical",
                        "source_data",
                        str(universe_path),
                        "investable/include/signal_only/price_ticker_verified",
                        f"invalid_universe_eligibility_flags: {len(eligibility_issues)} rows",
                        "Invalid eligibility combinations can admit stable-value or unverified-identity assets into portfolio research.",
                        "Rebuild the canonical universe and require explicit provider-symbol evidence.",
                        True,
                    )
                )
        unverified_crypto = universe.loc[unverified_crypto_price_mapping_mask(universe)]
        if not unverified_crypto.empty:
            issues.append(
                _issue(
                    "high",
                    "source_data",
                    str(universe_path),
                    "price_ticker_verified",
                    f"unverified_crypto_price_mappings: {len(unverified_crypto)} rows",
                    "CoinGecko market-cap metadata does not prove cross-provider price identity.",
                    "Keep these rows diagnostic-only until a reviewed CoinGecko-ID-to-price-provider crosswalk exists.",
                    True,
                )
            )
        duplicate_scope_available = {
            "investable",
            "include",
            "signal_only",
        }.issubset(universe.columns)
        if "ticker" not in universe:
            dupes = pd.DataFrame()
        elif duplicate_scope_available:
            active = (
                _truthy_series(universe["investable"])
                & _truthy_series(universe["include"])
                & ~_truthy_series(universe["signal_only"])
            )
            active_universe = universe.loc[active]
            dupes = active_universe.loc[
                active_universe["ticker"].astype(str).duplicated(keep=False)
            ]
        else:
            dupes = universe.loc[universe["ticker"].astype(str).duplicated(keep=False)]
        if not dupes.empty:
            issue_name = (
                "duplicate_investable_tickers"
                if duplicate_scope_available
                else "duplicate_tickers_in_universe"
            )
            issues.append(
                _issue(
                    "critical" if duplicate_scope_available else "medium",
                    "source_data",
                    str(universe_path),
                    "ticker",
                    f"{issue_name}: {dupes['ticker'].nunique()}",
                    (
                        "Duplicate included investable rows can double count a "
                        "security and distort selection or weights."
                        if duplicate_scope_available
                        else "Duplicates cannot be classified safely without "
                        "complete eligibility flags."
                    ),
                    "Deduplicate active investable rows or separate share classes explicitly.",
                    duplicate_scope_available,
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
            final_metadata = (
                meta.reindex(final_weights["Ticker"].astype(str))
                .reset_index(drop=False)
                .rename(columns={"index": "ticker"})
            )
            stable_final = stablecoin_like_mask(final_metadata)
            if "notes" in final_metadata:
                stable_final |= (
                    final_metadata["notes"]
                    .fillna("")
                    .astype(str)
                    .str.contains("stable_like=True", case=False, na=False)
                )
            if stable_final.any():
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


def _selection_evidence_sanity(processed: Path) -> list[dict[str, Any]]:
    """Flag economically suspicious OOS metrics and incomplete promotion evidence."""
    issues: list[dict[str, Any]] = []
    comparison = _read_csv(processed / "global_walk_forward_model_comparison.csv")
    for row in comparison.itertuples(index=False):
        model = str(getattr(row, "model_name", "unknown"))
        status = str(getattr(row, "model_status", "unknown"))
        for column, threshold, label in [
            ("oos_cagr", 1.0, "oos_cagr_above_100pct"),
            ("oos_annualized_return", 1.0, "oos_annual_return_above_100pct"),
            ("oos_volatility", 1.0, "oos_volatility_above_100pct"),
            ("oos_sharpe", 3.0, "oos_sharpe_above_3"),
            ("oos_sortino", 5.0, "oos_sortino_above_5"),
        ]:
            value = _num(getattr(row, column, np.nan))
            if pd.notna(value) and value > threshold:
                issues.append(
                    _issue(
                        "high" if status != "diagnostic_only" else "medium",
                        "walk_forward_validation",
                        "data/processed/global_walk_forward_model_comparison.csv",
                        column,
                        f"{model}: {label} ({value:.4f})",
                        "A short current-universe OOS window can produce economically "
                        "extreme estimates even when arithmetic is correct; the result "
                        "is vulnerable to regime and survivorship bias.",
                        "Retain as a warning, show the date range and uncertainty, and "
                        "do not interpret it as expected future performance.",
                        False,
                    )
                )
    if not comparison.empty and "oos_observations" in comparison:
        observation_values = pd.to_numeric(
            comparison["oos_observations"], errors="coerce"
        ).dropna()
        observations = (
            int(observation_values.max()) if not observation_values.empty else 0
        )
        if 0 < observations < 2 * 252:
            issues.append(
                _issue(
                    "medium",
                    "walk_forward_validation",
                    "data/processed/global_walk_forward_model_comparison.csv",
                    "oos_observations",
                    f"short_oos_history_for_model_selection: {observations} observations",
                    "One to two trading years cannot represent a broad set of market "
                    "regimes and gives imprecise risk-adjusted comparisons.",
                    "Extend point-in-time OOS history before making alpha or stability claims.",
                    False,
                )
            )
    robustness = _read_json(processed / "global_parameter_sensitivity_summary.json")
    if "diagnostic" in str(robustness.get("robustness_status", "")).lower():
        issues.append(
            _issue(
                "high",
                "model_selection",
                "data/processed/global_parameter_sensitivity_summary.json",
                "robustness_status",
                "nested_oos_robustness_not_implemented",
                "Current-sample configuration sensitivity cannot establish that an "
                "active model remains superior under nested chronological OOS testing.",
                "Keep active challengers unpromoted until the robustness grid is rerun "
                "inside a leakage-safe nested OOS protocol.",
                True,
            )
        )
    eligible_models = (
        int(comparison["model_name"].astype(str).nunique())
        if "model_name" in comparison
        else 0
    )
    if eligible_models > 1 and not any(
        (processed / filename).exists()
        for filename in [
            "global_white_reality_check.csv",
            "global_spa_test.csv",
            "global_deflated_sharpe.csv",
            "global_pbo_diagnostics.csv",
        ]
    ):
        issues.append(
            _issue(
                "high",
                "model_selection",
                "data/processed/global_walk_forward_model_comparison.csv",
                "model_name",
                f"multiple_testing_control_incomplete: {eligible_models} compared models",
                "Selecting the best result from several models inflates apparent skill "
                "and creates a winner's-curse risk.",
                "Retain conservative language and no active promotion; add a justified "
                "Reality Check, SPA, DSR/PBO method only when sample size supports it.",
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
        for name in ["Black-Litterman", "HRP", "Risk Parity", "Policy Constrained"]:
            row = models.loc[models["Model"].astype(str).eq(name)]
            if (
                not row.empty
                and not row["Status"].astype(str).str.startswith("computed").any()
            ):
                severity = (
                    "high"
                    if name in {"Black-Litterman", "Policy Constrained"}
                    else "medium"
                )
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


def _governance_readiness_sanity(
    processed: Path,
    universe_path: Path,
) -> list[dict[str, Any]]:
    """Flag governance blockers for historical promotion claims."""
    issues = []
    universe = _read_csv(universe_path)
    decision = _decision(processed)
    promoted = str(decision.get("promotion_decision", "")).lower() == "promoted"
    has_equities = (
        not universe.empty
        and "sleeve" in universe
        and universe["sleeve"].astype(str).str.startswith("global_equity").any()
    )
    if not has_equities:
        return issues

    pit_columns = {
        "membership_effective_start",
        "membership_effective_end",
        "point_in_time_source_url",
    }
    if not pit_columns.issubset(universe.columns):
        issues.append(
            _issue(
                "critical" if promoted else "high",
                "backtest_validation",
                str(universe_path),
                "point_in_time_membership",
                "point_in_time_membership_evidence_missing",
                "Current constituent files cannot support historical stock-selection or walk-forward promotion claims.",
                "Add dated membership tables with effective dates, source URLs and no-look-ahead controls before historical promotion.",
                True,
            )
        )

    corporate_action_columns = {
        "delisting_status",
        "corporate_action_source",
        "corporate_action_adjustment_status",
    }
    if not corporate_action_columns.issubset(universe.columns):
        issues.append(
            _issue(
                "high",
                "backtest_validation",
                str(universe_path),
                "delisting_corporate_actions",
                "delisting_and_corporate_action_evidence_missing",
                "Institutional-quality equity backtests need delisting, split, dividend and corporate-action coverage.",
                "Add delisting/corporate-action audit fields or keep the global stock backtest research-only.",
                True,
            )
        )

    walk_forward_files = [
        processed / "global_walk_forward_validation.csv",
        processed / "global_walk_forward_returns.csv",
        processed / "global_walk_forward_weights.csv",
    ]
    if not all(path.exists() for path in walk_forward_files):
        issues.append(
            _issue(
                "high",
                "backtest_validation",
                "data/processed/global_walk_forward_validation.csv",
                "file",
                "global_walk_forward_evidence_missing",
                "A current-only candidate cannot be promoted as a historical or out-of-sample global stock strategy without chronological validation.",
                "Build point-in-time walk-forward returns, weights and validation outputs before historical promotion.",
                True,
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
                    "v2_public_data_model_blockers": 0,
                    "institutional_global_master_blockers": 0,
                    "active_challenger_promotion_blockers": 0,
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
                "v2_public_data_model_blockers": int(
                    issues["blocks_v2_public_data_model"].astype(bool).sum()
                ),
                "institutional_global_master_blockers": int(
                    issues["blocks_institutional_global_master"].astype(bool).sum()
                ),
                "active_challenger_promotion_blockers": int(
                    issues["blocks_active_challenger_promotion"].astype(bool).sum()
                ),
                "status": "red_flags_present",
            }
        ]
    )


def _dashboard(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(
            columns=[
                "decision_scope",
                "category",
                "severity",
                "issue_count",
                "promotion_blockers",
            ]
        )
    return (
        issues.groupby(["decision_scope", "category", "severity"], as_index=False)
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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _decision(processed: Path) -> dict[str, Any]:
    path = processed / "global_master_decision_summary.json"
    return _read_json(path)


def _num(value: Any) -> float:
    return float(pd.to_numeric(value, errors="coerce"))


def _effective_holdings(weights: pd.Series) -> float:
    numeric = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    denom = float((numeric**2).sum())
    return float(1.0 / denom) if denom > 0 else 0.0


def _truthy_series(series: pd.Series) -> pd.Series:
    return series.map(
        lambda value: value is True
        or str(value).strip().lower() in {"1", "true", "yes", "y"}
    ).astype(bool)


def _issue_scope(
    *,
    category: str,
    evidence_file: str,
    issue: str,
    blocks_promotion: bool,
) -> tuple[str, str, bool, bool, bool]:
    evidence = str(evidence_file).replace("\\", "/").lower()
    issue_text = str(issue).lower()
    if "global_master_" in evidence:
        return (
            "legacy_global_master_proxy_research",
            "legacy_global_master_candidate",
            False,
            bool(blocks_promotion),
            False,
        )
    institutional_tokens = {
        "exact_top100",
        "market_cap_coverage",
        "market_cap_rank",
        "black_litterman_priors",
        "point_in_time",
        "delisting_and_corporate_action",
        "unverified_crypto_price",
        "source_url_missing",
    }
    if any(token in issue_text for token in institutional_tokens):
        return (
            "global_universe_governance",
            "institutional_global_master_promotion",
            False,
            bool(blocks_promotion),
            False,
        )
    active_challenger_tokens = {
        "nested_oos_robustness",
        "multiple_testing_control",
    }
    if any(token in issue_text for token in active_challenger_tokens):
        return (
            "v2_public_data_equity_research",
            "active_public_data_challenger_promotion",
            False,
            False,
            bool(blocks_promotion),
        )
    if category == "fx_currency":
        return (
            "usd_return_construction",
            "v2_and_institutional_portfolio_evidence",
            bool(blocks_promotion),
            bool(blocks_promotion),
            bool(blocks_promotion),
        )
    if category == "reporting":
        return (
            "reporting_artifact",
            "reporting_readiness",
            False,
            False,
            False,
        )
    return (
        "v2_public_data_equity_research",
        "v2_public_data_research_model",
        bool(blocks_promotion),
        False,
        bool(blocks_promotion),
    )


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
    (
        evidence_scope,
        decision_scope,
        blocks_v2,
        blocks_institutional,
        blocks_active_challenger,
    ) = _issue_scope(
        category=category,
        evidence_file=evidence_file,
        issue=issue,
        blocks_promotion=blocks_promotion,
    )
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
        "evidence_scope": evidence_scope,
        "decision_scope": decision_scope,
        "blocks_v2_public_data_model": blocks_v2,
        "blocks_institutional_global_master": blocks_institutional,
        "blocks_active_challenger_promotion": blocks_active_challenger,
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
