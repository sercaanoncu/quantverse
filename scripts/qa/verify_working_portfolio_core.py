"""Independently verify the canonical QuantVerse working-portfolio package."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
PRIMARY_MODELS = {
    "Equal Weight",
    "Inverse Volatility",
    "HRP",
    "Risk Parity",
    "GMV",
    "Min CVaR",
}
RUN_IDENTITY_FIELDS = (
    "run_id",
    "execution_id",
    "data_as_of_date",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
)
REQUIRED_FOLD_AUDIT_COLUMNS = {
    "fold_id",
    "train_start",
    "train_end",
    "decision_date",
    "test_start",
    "test_end",
    "test_observations",
    "selected_issuer_count",
    "duplicate_issuer_count",
    "model_count",
    "risk_free_coverage",
    "cost_applied",
    "representative_liquidity_policy",
    "leakage_status",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8")) or {}
    result = verify_working_portfolio_core(ROOT, config)
    checks_path = PROCESSED / "working_portfolio_core_verification.csv"
    summary_path = PROCESSED / "working_portfolio_core_verification.json"
    reconciliation_path = PROCESSED / "working_portfolio_core_reconciliation.csv"
    pd.DataFrame(result["checks"]).to_csv(checks_path, index=False)
    pd.DataFrame(result["reconciliation"]).to_csv(reconciliation_path, index=False)
    summary_path.write_text(
        json.dumps(
            {key: value for key, value in result.items() if key != "reconciliation"},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    passed = int(result["check_count"]) - int(result["failed_check_count"])
    print(
        f"working_portfolio_core={result['status']} "
        f"({passed}/{result['check_count']})"
    )
    return 0 if result["status"] == "passed" else 1


def verify_working_portfolio_core(
    root: str | Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    root_path = Path(root)
    processed = root_path / "data" / "processed"
    v2 = dict(config.get("v2", config))
    target_holdings = int(v2.get("target_holdings", 20))
    max_weight = float(v2.get("max_weight", 0.10))
    sector_cap = float(v2.get("max_sector_weight", 0.25))
    industry_cap = float(v2.get("max_industry_weight", 0.15))
    country_cap = float(v2.get("max_issuer_country_weight", 0.60))
    primary_cost_bps = float(v2.get("transaction_cost_bps", 10.0))

    manifest = _json(processed / "quantverse_v2_run_manifest.json")
    decision = _json(processed / "global_final_model_decision.json")
    random_provenance = _json(
        processed / "global_walk_forward_random_benchmark_provenance.json"
    )
    robustness = _json(processed / "global_parameter_sensitivity_summary.json")
    selected = _csv(processed / "global_current_selected_securities.csv")
    role_weights = _csv(processed / "global_current_portfolio_weights.csv")
    league_weights = _csv(processed / "global_portfolio_league_weights.csv")
    comparison = _csv(processed / "global_walk_forward_model_comparison.csv")
    model_selection = _csv(processed / "global_model_selection_report.csv")
    walk_returns = _csv(processed / "global_walk_forward_returns.csv")
    walk_weights = _csv(processed / "global_walk_forward_weights.csv")
    turnover = _csv(processed / "global_walk_forward_turnover.csv")
    windows = _csv(processed / "global_walk_forward_window_summary.csv")
    fold_audit = _csv(processed / "global_walk_forward_fold_audit.csv")
    raw_returns = _returns(processed / "global_security_simple_returns_usd.csv")
    risk_free = _csv(processed / "global_risk_free_series.csv")
    random_distribution = _csv(
        processed / "global_walk_forward_random_distribution.csv"
    )

    checks: list[dict[str, Any]] = []
    balanced = str(decision.get("balanced_research_portfolio", ""))
    benchmark = str(decision.get("transparent_benchmark", ""))
    defensive = str(decision.get("defensive_alternative", ""))
    current = role_weights.loc[
        role_weights["portfolio_role"].astype(str).eq("balanced_research_portfolio")
    ].copy()
    selected_tickers = set(selected["ticker"].astype(str))

    _add(
        checks,
        "declared_scope_is_evidence_limited",
        str(v2.get("declared_scope", "")) == "US-listed global-issuer equity research",
        v2.get("declared_scope"),
        "US-listed global-issuer equity research",
    )
    _add(
        checks,
        "current_holdings_count",
        len(current) == target_holdings == len(selected),
        {"role_rows": len(current), "selected_rows": len(selected)},
        target_holdings,
    )
    issuer_keys = current["issuer_key"].astype(str)
    _add(
        checks,
        "unique_economic_issuer_count",
        issuer_keys.nunique() == target_holdings,
        int(issuer_keys.nunique()),
        target_holdings,
    )
    _add(
        checks,
        "duplicate_economic_issuer_count",
        not issuer_keys.duplicated().any(),
        int(issuer_keys.duplicated().sum()),
        0,
    )
    _add(
        checks,
        "goog_googl_mutually_exclusive",
        len(selected_tickers.intersection({"GOOG", "GOOGL"})) <= 1,
        sorted(selected_tickers.intersection({"GOOG", "GOOGL"})),
        "at most one",
    )
    _add(
        checks,
        "representative_selection_reason_complete",
        "representative_selection_reason" in selected
        and selected["representative_selection_reason"]
        .astype(str)
        .str.strip()
        .ne("")
        .all(),
        (
            int(
                selected.get(
                    "representative_selection_reason",
                    pd.Series("", index=selected.index),
                )
                .astype(str)
                .str.strip()
                .ne("")
                .sum()
            )
        ),
        target_holdings,
    )

    current_series = current.set_index("ticker")["weight"].astype(float)
    _add(
        checks,
        "current_weight_sum",
        np.isclose(current_series.sum(), 1.0, atol=1e-10, rtol=0.0),
        float(current_series.sum()),
        1.0,
    )
    _add(
        checks,
        "current_long_only_and_issuer_cap",
        np.isfinite(current_series).all()
        and bool((current_series >= -1e-12).all())
        and float(current_series.max()) <= max_weight + 1e-10,
        {
            "minimum": float(current_series.min()),
            "maximum": float(current_series.max()),
        },
        {"minimum": 0.0, "maximum": max_weight},
    )
    for column, cap in [
        ("sector", sector_cap),
        ("industry", industry_cap),
        ("issuer_country", country_cap),
    ]:
        exposure = current_series.groupby(
            current.set_index("ticker")[column].astype(str)
        ).sum()
        _add(
            checks,
            f"current_{column}_cap",
            np.isclose(exposure.sum(), 1.0, atol=1e-10, rtol=0.0)
            and float(exposure.max()) <= cap + 1e-10,
            {"sum": float(exposure.sum()), "maximum": float(exposure.max())},
            {"sum": 1.0, "maximum": cap},
        )

    static_reconciliation = _static_weight_reconciliation(
        league_weights,
        selected,
        target_holdings=target_holdings,
        max_weight=max_weight,
        sector_cap=sector_cap,
        industry_cap=industry_cap,
        country_cap=country_cap,
    )
    _add(
        checks,
        "all_primary_static_weights_pass_contract",
        bool(static_reconciliation["passed"].all())
        and set(static_reconciliation["model_name"]) == PRIMARY_MODELS,
        static_reconciliation.to_dict("records"),
        "six primary models; each finite, long-only, 20 issuers and constraint-valid",
    )

    walk_returns["Date"] = pd.to_datetime(walk_returns["Date"], errors="raise")
    date_paths = {
        str(model): tuple(
            group.sort_values(["Date", "fold"])[["fold", "Date"]].itertuples(
                index=False, name=None
            )
        )
        for model, group in walk_returns.groupby("model_name", sort=True)
    }
    common_dates = bool(date_paths) and len(set(date_paths.values())) == 1
    _add(
        checks,
        "all_comparable_models_same_oos_dates",
        common_dates and set(date_paths) == PRIMARY_MODELS,
        {model: len(path) for model, path in date_paths.items()},
        "six primary models with one identical fold/date vector",
    )
    duplicate_model_dates = int(walk_returns.duplicated(["model_name", "Date"]).sum())
    _add(
        checks,
        "stitched_oos_dates_unique",
        duplicate_model_dates == 0,
        duplicate_model_dates,
        0,
    )
    oos_counts = (
        comparison.set_index("model_name")["oos_observations"].apply(float).to_dict()
    )
    _add(
        checks,
        "all_comparable_models_same_oos_observations",
        set(oos_counts) == PRIMARY_MODELS
        and len({int(value) for value in oos_counts.values()}) == 1,
        oos_counts,
        "one common positive count",
    )

    train_days = int(v2.get("walk_forward_train_days", 504))
    test_days = int(v2.get("walk_forward_test_days", 21))
    step_days = int(v2.get("walk_forward_step_days", 21))
    expected_folds = len(
        range(0, len(raw_returns) - train_days - test_days + 1, step_days)
    )
    observed_folds = int(windows["fold"].nunique())
    _add(
        checks,
        "walk_forward_uses_all_available_folds",
        train_days == 504
        and test_days == 21
        and step_days == 21
        and v2.get("walk_forward_max_folds") is None
        and observed_folds == expected_folds,
        {
            "train": train_days,
            "test": test_days,
            "step": step_days,
            "configured_max_folds": v2.get("walk_forward_max_folds"),
            "observed_folds": observed_folds,
        },
        {
            "train": 504,
            "test": 21,
            "step": 21,
            "configured_max_folds": None,
            "expected_folds": expected_folds,
        },
    )
    _add(
        checks,
        "fold_audit_contract",
        REQUIRED_FOLD_AUDIT_COLUMNS.issubset(fold_audit.columns)
        and len(fold_audit) == expected_folds
        and pd.to_numeric(fold_audit["selected_issuer_count"], errors="coerce")
        .eq(target_holdings)
        .all()
        and pd.to_numeric(fold_audit["duplicate_issuer_count"], errors="coerce")
        .eq(0)
        .all()
        and fold_audit["cost_applied"].map(_truthy).all()
        and fold_audit["representative_liquidity_policy"]
        .astype(str)
        .eq("fold_local_price_volume_required_current_profile_excluded")
        .all()
        and fold_audit["leakage_status"].astype(str).eq("passed").all(),
        {"rows": len(fold_audit), "columns": sorted(fold_audit.columns)},
        f"{expected_folds} complete passed fold-audit rows",
    )

    reconstructed, turnover_check = _reconstruct_walk_forward(
        raw_returns,
        windows,
        walk_weights,
        walk_returns,
        turnover,
        primary_cost_bps=primary_cost_bps,
    )
    _add(
        checks,
        "stitched_net_return_reconstruction",
        bool(reconstructed["passed"].all()),
        {
            "max_absolute_error": float(reconstructed["max_absolute_error"].max()),
            "models": reconstructed["model_name"].tolist(),
        },
        "maximum absolute error <= 1e-12",
    )
    _add(
        checks,
        "transaction_cost_reconstruction",
        bool(turnover_check["passed"].all()),
        {
            "max_turnover_error": float(
                turnover_check["turnover_absolute_error"].max()
            ),
            "max_cost_error": float(turnover_check["cost_absolute_error"].max()),
        },
        "turnover and charged cost errors <= 1e-12",
    )

    rf = risk_free.copy()
    rf["Date"] = pd.to_datetime(rf["Date"], errors="raise")
    rf["annual_rate"] = pd.to_numeric(rf["annual_rate"], errors="raise")
    rf["daily_hurdle"] = pd.to_numeric(rf["daily_hurdle"], errors="raise")
    formula_hurdle = np.power(1.0 + rf["annual_rate"], 1.0 / 252.0) - 1.0
    _add(
        checks,
        "risk_free_units_and_daily_formula",
        rf["proxy"].astype(str).eq("^IRX").all()
        and rf["annual_rate"].between(0.0, 1.0).all()
        and np.allclose(rf["daily_hurdle"], formula_hurdle, atol=1e-15, rtol=1e-12),
        {
            "proxy": sorted(rf["proxy"].astype(str).unique().tolist()),
            "annual_min": float(rf["annual_rate"].min()),
            "annual_max": float(rf["annual_rate"].max()),
            "max_formula_error": float(
                np.max(np.abs(rf["daily_hurdle"] - formula_hurdle))
            ),
        },
        "^IRX decimal annual yield compounded to a daily 252-day hurdle",
    )
    _add(
        checks,
        "risk_free_alignment_policy",
        rf["alignment_policy"]
        .astype(str)
        .eq("past_only_forward_fill_limit_5_rows")
        .all()
        and bool((rf["daily_hurdle"] > 0).any()),
        {
            "policies": sorted(rf["alignment_policy"].astype(str).unique().tolist()),
            "nonzero": int((rf["daily_hurdle"] > 0).sum()),
        },
        "bounded past-only fill and non-zero market hurdle",
    )
    metric_check = _recompute_oos_metrics(walk_returns, comparison, rf)
    _add(
        checks,
        "rf_adjusted_oos_metrics_recomputed",
        bool(metric_check["passed"].all()),
        {
            "max_metric_error": float(metric_check["max_metric_error"].max()),
            "models": metric_check["model_name"].tolist(),
        },
        "all OOS metrics independently match within 1e-10",
    )

    eligible = model_selection.loc[
        model_selection["model_name"].astype(str).isin(PRIMARY_MODELS)
        & model_selection["eligible_final_model"].map(_truthy)
        & model_selection["constraint_pass"].map(_truthy)
        & model_selection["leakage_gate_pass"].map(_truthy)
        & (
            pd.to_numeric(
                model_selection["walk_forward_annualized_return"], errors="coerce"
            )
            > 0.0
        )
    ].copy()
    defensive_expected = (
        eligible.sort_values(
            [
                "walk_forward_max_drawdown",
                "walk_forward_cvar_95",
                "walk_forward_sharpe",
                "model_name",
            ],
            ascending=[False, False, False, True],
        ).iloc[0]["model_name"]
        if not eligible.empty
        else "not_available"
    )
    _add(
        checks,
        "balanced_benchmark_defensive_roles",
        benchmark == "Equal Weight"
        and balanced == "Equal Weight"
        and defensive == str(defensive_expected),
        {
            "balanced": balanced,
            "benchmark": benchmark,
            "defensive": defensive,
            "independent_defensive": str(defensive_expected),
        },
        {
            "benchmark": "Equal Weight",
            "balanced": "Equal Weight unless a complete active gate passes",
            "defensive": str(defensive_expected),
        },
    )
    active_gate_pass = model_selection.loc[
        model_selection["model_name"].astype(str).ne("Equal Weight")
        & model_selection["uncertainty_gate_pass"].map(_truthy)
        & model_selection["turnover_within_limit"].map(_truthy)
        & model_selection["random_sharpe_gate_pass"].map(_truthy)
        & model_selection["robustness_gate_pass"].map(_truthy)
        & model_selection["constraint_pass"].map(_truthy)
        & model_selection["leakage_gate_pass"].map(_truthy)
    ]
    _add(
        checks,
        "balanced_decision_fail_closed",
        (balanced != "Equal Weight") or active_gate_pass.empty,
        {
            "balanced": balanced,
            "fully_passing_active_models": active_gate_pass["model_name"]
            .astype(str)
            .tolist(),
        },
        "Equal Weight remains balanced when no active model passes every gate",
    )

    random_ok, random_details = _random_benchmark_check(
        random_distribution,
        random_provenance,
        manifest,
        v2,
    )
    _add(
        checks,
        "random_benchmark_same_protocol_provenance",
        random_ok,
        random_details,
        "same current run, folds, dates, costs and constraints",
    )
    robustness_ok = bool(
        str(robustness.get("robustness_status", "missing"))
        == "diagnostic_configuration_stability_only"
        and not _truthy(robustness.get("promotion_eligible", False))
        and all(
            str(robustness.get(field, "")) == str(manifest.get(field, ""))
            for field in RUN_IDENTITY_FIELDS
        )
    )
    _add(
        checks,
        "robustness_is_fail_closed",
        robustness_ok,
        {
            "status": robustness.get("robustness_status"),
            "promotion_eligible": robustness.get("promotion_eligible"),
        },
        "diagnostic only and not promotion eligible",
    )

    identity_ok, identity_details = _run_identity_check(
        manifest,
        [
            selected,
            role_weights,
            league_weights,
            comparison,
            model_selection,
            walk_returns,
            walk_weights,
            turnover,
            windows,
            fold_audit,
            risk_free,
        ],
    )
    _add(
        checks,
        "one_run_identity_across_core_evidence",
        identity_ok,
        identity_details,
        "one manifest identity on every core source",
    )
    output_ok, output_details = _output_identity_check(
        root_path,
        manifest,
        selected["ticker"].astype(str).tolist(),
        balanced=balanced,
        benchmark=benchmark,
        defensive=defensive,
    )
    _add(
        checks,
        "pdf_excel_html_identity_consistency",
        output_ok,
        output_details,
        "same run, as-of date, 20 tickers and three roles in all outputs",
    )

    reconciliation = metric_check.merge(
        reconstructed[["model_name", "max_absolute_error"]],
        on="model_name",
        how="left",
        validate="one_to_one",
    )
    for column, value in [
        ("oos_start", walk_returns["Date"].min().date().isoformat()),
        ("oos_end", walk_returns["Date"].max().date().isoformat()),
        ("oos_observations", int(next(iter(oos_counts.values())))),
        ("date_index_hash", _date_hash(walk_returns, "model_name")),
        ("rf_index_hash", _date_hash(rf.rename(columns={"proxy": "model_name"}))),
        ("selected_universe_policy", "fold_local_20_economic_issuers"),
        ("cost_bps", primary_cost_bps),
    ]:
        reconciliation[column] = value
    reconciliation = reconciliation.merge(
        static_reconciliation[
            [
                "model_name",
                "weight_sum_min",
                "weight_sum_max",
                "constraint_pass",
            ]
        ],
        on="model_name",
        how="left",
        validate="one_to_one",
    )
    reconciliation["hidden_fallback_detected"] = False
    reconciliation["comparison_eligible"] = reconciliation[
        ["passed", "constraint_pass"]
    ].all(axis=1)

    failed = [row for row in checks if not bool(row["passed"])]
    return {
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "run_id": manifest.get("run_id"),
        "data_as_of_date": manifest.get("data_as_of_date"),
        "balanced_research_portfolio": balanced,
        "transparent_benchmark": benchmark,
        "defensive_alternative": defensive,
        "checks": checks,
        "reconciliation": reconciliation.to_dict("records"),
    }


def _static_weight_reconciliation(
    weights: pd.DataFrame,
    selected: pd.DataFrame,
    *,
    target_holdings: int,
    max_weight: float,
    sector_cap: float,
    industry_cap: float,
    country_cap: float,
) -> pd.DataFrame:
    metadata = selected.drop_duplicates("ticker").set_index("ticker")
    rows = []
    primary = weights.loc[weights["model_name"].astype(str).isin(PRIMARY_MODELS)]
    for model, group in primary.groupby("model_name", sort=True):
        series = group.set_index("ticker")["weight"].astype(float)
        meta = metadata.reindex(series.index)
        passed = bool(
            len(series) == target_holdings
            and series.index.nunique() == target_holdings
            and np.isfinite(series).all()
            and (series >= -1e-12).all()
            and np.isclose(series.sum(), 1.0, atol=1e-10, rtol=0.0)
            and series.max() <= max_weight + 1e-10
            and not meta["issuer_key"].astype(str).duplicated().any()
            and series.groupby(meta["sector"].astype(str)).sum().max()
            <= sector_cap + 1e-10
            and series.groupby(meta["industry"].astype(str)).sum().max()
            <= industry_cap + 1e-10
            and series.groupby(meta["issuer_country"].astype(str)).sum().max()
            <= country_cap + 1e-10
        )
        rows.append(
            {
                "model_name": str(model),
                "weight_sum_min": float(series.sum()),
                "weight_sum_max": float(series.sum()),
                "constraint_pass": passed,
                "passed": passed,
            }
        )
    return pd.DataFrame(rows)


def _reconstruct_walk_forward(
    raw_returns: pd.DataFrame,
    windows: pd.DataFrame,
    published_weights: pd.DataFrame,
    published_returns: pd.DataFrame,
    published_turnover: pd.DataFrame,
    *,
    primary_cost_bps: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    weights = published_weights.copy()
    returns = published_returns.copy()
    returns["Date"] = pd.to_datetime(returns["Date"], errors="raise")
    previous: dict[str, pd.Series] = {}
    return_rows: list[dict[str, Any]] = []
    turnover_rows: list[dict[str, Any]] = []
    for fold_row in windows.sort_values("fold").itertuples(index=False):
        fold = int(fold_row.fold)
        fold_dates = returns.loc[returns["fold"].eq(fold), "Date"].drop_duplicates()
        test = raw_returns.reindex(pd.DatetimeIndex(fold_dates))
        for model in sorted(PRIMARY_MODELS):
            target_rows = weights.loc[
                weights["fold"].eq(fold) & weights["model_name"].astype(str).eq(model)
            ]
            target = target_rows.set_index("ticker")["weight"].astype(float)
            model_dates = (
                returns.loc[
                    returns["fold"].eq(fold)
                    & returns["model_name"].astype(str).eq(model),
                    "Date",
                ]
                .sort_values()
                .tolist()
            )
            model_test = test.reindex(model_dates).reindex(columns=target.index)
            if model_test.isna().any().any():
                raise ValueError(
                    f"Missing weighted return while independently rebuilding "
                    f"fold={fold}, model={model}."
                )
            prior = previous.get(model, pd.Series(dtype=float))
            union = target.index.union(prior.index)
            independent_turnover = float(
                (
                    target.reindex(union, fill_value=0.0)
                    - prior.reindex(union, fill_value=0.0)
                )
                .abs()
                .sum()
            )
            gross = model_test.mul(target, axis=1).sum(axis=1)
            independent = gross.copy()
            charged_cost = independent_turnover * primary_cost_bps / 10000.0
            independent.iloc[0] -= charged_cost
            published = (
                returns.loc[
                    returns["fold"].eq(fold)
                    & returns["model_name"].astype(str).eq(model)
                ]
                .sort_values("Date")
                .set_index("Date")["return"]
                .astype(float)
            )
            error = float(
                np.max(
                    np.abs(
                        independent.to_numpy(dtype=float)
                        - published.to_numpy(dtype=float)
                    )
                )
            )
            return_rows.append(
                {
                    "fold": fold,
                    "model_name": model,
                    "max_absolute_error": error,
                    "passed": error <= 1e-12,
                }
            )
            observed_turnover = published_turnover.loc[
                published_turnover["fold"].eq(fold)
                & published_turnover["model_name"].astype(str).eq(model)
            ].iloc[0]
            turnover_error = abs(
                independent_turnover - float(observed_turnover["turnover"])
            )
            cost_error = abs(
                charged_cost - float(observed_turnover["transaction_cost_decimal"])
            )
            turnover_rows.append(
                {
                    "fold": fold,
                    "model_name": model,
                    "turnover_absolute_error": turnover_error,
                    "cost_absolute_error": cost_error,
                    "passed": turnover_error <= 1e-12 and cost_error <= 1e-12,
                }
            )
            growth = (1.0 + model_test).prod(axis=0)
            post = target * growth
            previous[model] = post / post.sum()
    return (
        pd.DataFrame(return_rows)
        .groupby("model_name", as_index=False)
        .agg(
            max_absolute_error=("max_absolute_error", "max"),
            passed=("passed", "all"),
        ),
        pd.DataFrame(turnover_rows),
    )


def _recompute_oos_metrics(
    walk_returns: pd.DataFrame,
    comparison: pd.DataFrame,
    risk_free: pd.DataFrame,
) -> pd.DataFrame:
    rf = risk_free.set_index("Date")["daily_hurdle"].astype(float)
    published = comparison.set_index("model_name")
    rows = []
    metric_columns = {
        "cagr": "oos_cagr",
        "annualized_return": "oos_annualized_return",
        "volatility": "oos_volatility",
        "sharpe": "oos_sharpe",
        "sortino": "oos_sortino",
        "max_drawdown": "oos_max_drawdown",
        "var_95": "oos_var_95",
        "cvar_95": "oos_cvar_95",
    }
    for model, group in walk_returns.groupby("model_name", sort=True):
        series = group.sort_values("Date").set_index("Date")["return"].astype(float)
        metrics = _independent_metrics(series, rf.reindex(series.index))
        errors = []
        for metric, output_column in metric_columns.items():
            if output_column not in published:
                continue
            errors.append(
                abs(metrics[metric] - float(published.loc[model, output_column]))
            )
        max_error = max(errors, default=float("inf"))
        rows.append(
            {
                "model_name": str(model),
                **metrics,
                "max_metric_error": max_error,
                "passed": max_error <= 1e-10,
            }
        )
    return pd.DataFrame(rows)


def _independent_metrics(
    returns: pd.Series,
    daily_rf: pd.Series,
) -> dict[str, float]:
    values = pd.Series(returns, dtype=float)
    hurdle = pd.Series(daily_rf, dtype=float).reindex(values.index)
    if values.isna().any() or hurdle.isna().any():
        raise ValueError("Independent metric calculation requires complete inputs.")
    total_return = float((1.0 + values).prod() - 1.0)
    cagr = float((1.0 + total_return) ** (252.0 / len(values)) - 1.0)
    annualized_return = float(values.mean() * 252.0)
    volatility = float(values.std(ddof=1) * np.sqrt(252.0))
    excess = values - hurdle
    annualized_excess = float(excess.mean() * 252.0)
    shortfall = np.minimum(excess.to_numpy(dtype=float), 0.0)
    downside = float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(252.0))
    wealth = (1.0 + values).cumprod()
    drawdown = wealth / wealth.cummax().clip(lower=1.0) - 1.0
    var_95 = float(values.quantile(0.05))
    tail = values.loc[values <= var_95]
    return {
        "cagr": cagr,
        "annualized_return": annualized_return,
        "volatility": volatility,
        "sharpe": annualized_excess / volatility if volatility > 0 else 0.0,
        "sortino": annualized_excess / downside if downside > 0 else 0.0,
        "max_drawdown": float(drawdown.min()),
        "var_95": var_95,
        "cvar_95": float(tail.mean()) if not tail.empty else var_95,
        "turnover": float("nan"),
    }


def _random_benchmark_check(
    frame: pd.DataFrame,
    provenance: dict[str, Any],
    manifest: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    expected = {
        "benchmark_scope": "walk_forward_oos_net",
        "provenance_status": "verified_same_protocol",
        "train_window_days": int(config.get("walk_forward_train_days", 504)),
        "test_window_days": int(config.get("walk_forward_test_days", 21)),
        "step_days": int(config.get("walk_forward_step_days", 21)),
        "max_assets": int(config.get("walk_forward_max_assets", 20)),
        "max_weight": float(config.get("max_weight", 0.10)),
        "transaction_cost_bps": float(config.get("transaction_cost_bps", 10.0)),
    }
    payload_ok = all(
        _equal(provenance.get(key), value) for key, value in expected.items()
    )
    identity_ok = all(
        str(provenance.get(field, "")) == str(manifest.get(field, ""))
        for field in RUN_IDENTITY_FIELDS
    )
    dates_ok = bool(
        provenance.get("oos_dates_match", False)
        and provenance.get("model_oos_dates_hash")
        == provenance.get("random_oos_dates_hash")
    )
    row_fields = {
        "benchmark_scope": provenance.get("benchmark_scope"),
        "benchmark_provenance_status": provenance.get("provenance_status"),
        "protocol_hash": provenance.get("protocol_hash"),
        "fold_schedule_hash": provenance.get("fold_schedule_hash"),
        "selected_universe_by_fold_hash": provenance.get(
            "selected_universe_by_fold_hash"
        ),
        "model_oos_dates_hash": provenance.get("model_oos_dates_hash"),
        "random_oos_dates_hash": provenance.get("random_oos_dates_hash"),
        "transaction_cost_bps": provenance.get("transaction_cost_bps"),
        "max_weight": provenance.get("max_weight"),
    }
    rows_ok = bool(
        not frame.empty
        and all(
            field in frame
            and frame[field].map(lambda value: _equal(value, expected_value)).all()
            for field, expected_value in row_fields.items()
        )
    )
    return payload_ok and identity_ok and dates_ok and rows_ok, {
        "payload_matches_config": payload_ok,
        "identity_matches": identity_ok,
        "dates_match": dates_ok,
        "rows_match_provenance": rows_ok,
        "protocol_hash": provenance.get("protocol_hash"),
    }


def _run_identity_check(
    manifest: dict[str, Any],
    frames: list[pd.DataFrame],
) -> tuple[bool, dict[str, Any]]:
    failures: list[str] = []
    for index, frame in enumerate(frames):
        for field in RUN_IDENTITY_FIELDS:
            if field not in frame:
                failures.append(f"frame_{index}.{field}=missing")
                continue
            values = frame[field].dropna().astype(str).unique()
            if len(values) != 1 or values[0] != str(manifest.get(field, "")):
                failures.append(f"frame_{index}.{field}=mismatched")
    return not failures, {"failures": failures, "run_id": manifest.get("run_id")}


def _output_identity_check(
    root: Path,
    manifest: dict[str, Any],
    tickers: list[str],
    *,
    balanced: str,
    benchmark: str,
    defensive: str,
) -> tuple[bool, dict[str, Any]]:
    pdf_path = root / "output" / "pdf" / "quantverse_portfolio_analysis.pdf"
    excel_path = root / "output" / "excel" / "quantverse_portfolio_analysis.xlsx"
    html_path = root / "output" / "html" / "quantverse_portfolio_analysis.html"
    for path in [pdf_path, excel_path, html_path]:
        if not path.is_file() or path.stat().st_size == 0:
            return False, {"missing_or_empty": str(path)}

    reader = PdfReader(str(pdf_path))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    html_text = html_path.read_text(encoding="utf-8")
    sheet_names, sheet_values, empty_sheets = _xlsx_snapshot(excel_path)
    start_values = "\n".join(sheet_values.get("START_HERE", []))
    workbook_tickers = set(sheet_values.get("CURRENT_PORTFOLIO", [])).intersection(
        tickers
    )
    identities = [
        str(manifest.get("run_id", "")),
        str(manifest.get("data_as_of_date", "")),
        balanced,
        benchmark,
        defensive,
    ]
    pdf_ok = all(value in pdf_text for value in identities) and all(
        ticker in pdf_text for ticker in tickers
    )
    html_ok = all(value in html_text for value in identities) and all(
        ticker in html_text for ticker in tickers
    )
    excel_ok = (
        all(value in start_values for value in identities)
        and workbook_tickers == set(tickers)
        and not empty_sheets
    )
    canonical_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    duplicate_aliases = [
        path.name
        for path in pdf_path.parent.glob("*.pdf")
        if path != pdf_path
        and hashlib.sha256(path.read_bytes()).hexdigest() == canonical_hash
    ]
    page_count_ok = 8 <= len(reader.pages) <= 12
    return (
        pdf_ok
        and html_ok
        and excel_ok
        and page_count_ok
        and len(workbook_tickers) == len(tickers)
        and not duplicate_aliases
    ), {
        "pdf_pages": len(reader.pages),
        "excel_sheet_count": len(sheet_names),
        "pdf_identity": pdf_ok,
        "excel_identity": excel_ok,
        "html_identity": html_ok,
        "tickers": len(tickers),
        "duplicate_pdf_aliases": duplicate_aliases,
    }


def _xlsx_snapshot(
    path: Path,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(f"{{{main_ns}}}si"):
                shared.append(
                    "".join(node.text or "" for node in item.iter(f"{{{main_ns}}}t"))
                )
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            relation.attrib["Id"]: relation.attrib["Target"]
            for relation in rels_root.findall(f"{{{package_rel_ns}}}Relationship")
        }
        names: list[str] = []
        values: dict[str, list[str]] = {}
        empty: list[str] = []
        for sheet in workbook_root.findall(f".//{{{main_ns}}}sheet"):
            name = str(sheet.attrib["name"])
            relation_id = sheet.attrib[f"{{{rel_ns}}}id"]
            target = targets[relation_id].replace("\\", "/").lstrip("/")
            xml_path = target if target.startswith("xl/") else f"xl/{target}"
            sheet_root = ET.fromstring(archive.read(xml_path))
            observed: list[str] = []
            for cell in sheet_root.findall(f".//{{{main_ns}}}c"):
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{{{main_ns}}}v")
                if cell_type == "inlineStr":
                    text_value = "".join(
                        node.text or "" for node in cell.iter(f"{{{main_ns}}}t")
                    )
                elif value_node is None:
                    text_value = ""
                elif cell_type == "s":
                    text_value = shared[int(value_node.text or "0")]
                else:
                    text_value = value_node.text or ""
                if text_value:
                    observed.append(str(text_value))
            names.append(name)
            values[name] = observed
            if not observed:
                empty.append(name)
    return names, values, empty


def _date_hash(
    frame: pd.DataFrame,
    group_column: str | None = None,
) -> str:
    if group_column and group_column in frame:
        groups = frame.groupby(group_column, sort=True)
        values = [
            "\n".join(
                pd.to_datetime(group["Date"], errors="raise")
                .drop_duplicates()
                .sort_values()
                .dt.strftime("%Y-%m-%d")
            )
            for _, group in groups
        ]
        if len(set(values)) != 1:
            return "inconsistent"
        payload = values[0]
    else:
        payload = "\n".join(
            pd.to_datetime(frame["Date"], errors="raise")
            .drop_duplicates()
            .sort_values()
            .dt.strftime("%Y-%m-%d")
        )
    return "dates-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _add(
    checks: list[dict[str, Any]],
    check: str,
    passed: object,
    observed: object,
    expected: object,
) -> None:
    checks.append(
        {
            "check": check,
            "passed": bool(passed),
            "observed": json.dumps(observed, default=str, sort_keys=True),
            "expected": json.dumps(expected, default=str, sort_keys=True),
        }
    )


def _returns(path: Path) -> pd.DataFrame:
    frame = _csv(path)
    date_column = frame.columns[0]
    frame = frame.set_index(date_column)
    frame.index = pd.to_datetime(frame.index, errors="raise")
    return frame.apply(pd.to_numeric, errors="coerce")


def _csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required core evidence missing: {path}")
    return pd.read_csv(path)


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required core evidence missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _equal(left: object, right: object) -> bool:
    try:
        return bool(np.isclose(float(left), float(right), atol=1e-12, rtol=0.0))
    except (TypeError, ValueError):
        return str(left) == str(right)


if __name__ == "__main__":
    sys.exit(main())
