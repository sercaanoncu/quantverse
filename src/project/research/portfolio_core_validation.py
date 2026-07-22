"""Fail-closed acceptance checks for the canonical working portfolio."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR
from project.research.global_portfolio_core import (
    policy_from_mapping,
    validate_portfolio_constraints,
)

PRIMARY_MODELS = {
    "Equal Weight",
    "Inverse Volatility",
    "HRP",
    "Risk Parity",
    "GMV",
    "Min CVaR",
}


def validate_working_portfolio_core(
    root: str | Path,
    config: dict[str, object],
) -> dict[str, object]:
    """Validate all core gates before user-facing reports may be generated."""
    root_path = Path(root)
    processed = root_path / "data" / "processed"
    v2 = config.get("v2", config)
    policy = policy_from_mapping(v2 if isinstance(v2, dict) else {})
    selected = _read_csv(processed / "global_current_selected_securities.csv")
    metadata = _read_csv(processed / "global_canonical_security_metadata.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    league = _read_csv(processed / "global_portfolio_league.csv")
    walk_weights = _read_csv(processed / "global_walk_forward_weights.csv")
    walk_returns = _read_csv(processed / "global_walk_forward_returns.csv")
    windows = _read_csv(processed / "global_walk_forward_window_summary.csv")
    comparison = _read_csv(processed / "global_walk_forward_model_comparison.csv")
    risk = _read_csv(processed / "global_portfolio_risk_report.csv")
    rf = _read_csv(processed / "global_risk_free_series.csv")
    role_weights = _read_csv(processed / "global_current_portfolio_weights.csv")
    returns = _read_returns(processed / "global_security_simple_returns_usd.csv")
    decision = _read_json(processed / "global_final_model_decision.json")
    checks: list[dict[str, object]] = []

    _add(
        checks,
        "canonical_target_holdings",
        len(selected) == policy.target_holdings,
        len(selected),
        policy.target_holdings,
    )
    _add(
        checks,
        "requested_five_percent_cap_degeneracy_disclosed",
        policy.requested_cap_is_model_degenerate,
        policy.target_holdings * policy.requested_max_issuer_weight,
        "1.0 singleton Equal Weight capacity",
    )
    duplicate_count = int(
        selected.get("issuer_key", pd.Series(dtype=str)).duplicated().sum()
    )
    _add(
        checks,
        "duplicate_economic_issuer_count",
        duplicate_count == 0,
        duplicate_count,
        0,
    )
    goog = set(selected.get("ticker", pd.Series(dtype=str)).astype(str)).intersection(
        {"GOOG", "GOOGL"}
    )
    _add(
        checks,
        "goog_googl_mutually_exclusive",
        len(goog) <= 1,
        sorted(goog),
        "at most one",
    )

    active_weights = weights.loc[
        weights["model_name"].astype(str).isin(PRIMARY_MODELS)
    ].copy()
    observed_models = set(active_weights["model_name"].astype(str))
    _add(
        checks,
        "primary_model_set_complete",
        observed_models == PRIMARY_MODELS,
        sorted(observed_models),
        sorted(PRIMARY_MODELS),
    )
    for model, group in active_weights.groupby("model_name", sort=True):
        series = group.set_index("ticker")["weight"].astype(float)
        model_meta = selected.loc[selected["ticker"].astype(str).isin(series.index)]
        try:
            result = validate_portfolio_constraints(series, model_meta, policy)
            passed = bool(result["all_constraints_pass"])
            observed: object = result
        except ValueError as exc:
            passed = False
            observed = str(exc)
        _add(
            checks, f"current_constraints_{_slug(model)}", passed, observed, "all pass"
        )

    grouped_walk = walk_weights.groupby(["fold", "model_name"], sort=True).agg(
        holdings=("ticker", "nunique"), weight_sum=("weight", "sum")
    )
    _add(
        checks,
        "walk_forward_target_holdings",
        not grouped_walk.empty
        and grouped_walk["holdings"].eq(policy.target_holdings).all(),
        sorted(grouped_walk["holdings"].unique().tolist()),
        [policy.target_holdings],
    )
    _add(
        checks,
        "walk_forward_weight_sums",
        not grouped_walk.empty
        and np.allclose(grouped_walk["weight_sum"], 1.0, atol=1e-8),
        [
            float(grouped_walk["weight_sum"].min()),
            float(grouped_walk["weight_sum"].max()),
        ],
        [1.0, 1.0],
    )

    walk_returns["Date"] = pd.to_datetime(walk_returns["Date"], errors="coerce")
    date_sets = {
        model: tuple(group["Date"].sort_values().astype(str))
        for model, group in walk_returns.groupby("model_name")
    }
    same_dates = bool(date_sets) and len(set(date_sets.values())) == 1
    _add(
        checks,
        "all_comparable_models_same_oos_dates",
        same_dates,
        {k: len(v) for k, v in date_sets.items()},
        "identical date vectors",
    )
    obs = (
        comparison.set_index("model_name")["oos_observations"].to_dict()
        if not comparison.empty
        else {}
    )
    _add(
        checks,
        "all_comparable_models_same_oos_observation_count",
        bool(obs) and len(set(obs.values())) == 1,
        obs,
        "one shared count",
    )

    active_league = league.loc[league["model_name"].astype(str).isin(PRIMARY_MODELS)]
    full_dates = active_league[
        ["metric_start_date", "metric_end_date", "metric_observations"]
    ].drop_duplicates()
    _add(
        checks,
        "all_comparable_models_same_full_sample_dates",
        len(full_dates) == 1,
        full_dates.to_dict("records"),
        "one shared start/end/count",
    )

    train_days = int(v2.get("walk_forward_train_days", 504))
    test_days = int(v2.get("walk_forward_test_days", 21))
    step_days = int(v2.get("walk_forward_step_days", 21))
    expected_folds = len(range(0, len(returns) - train_days - test_days + 1, step_days))
    observed_folds = int(windows["fold"].nunique()) if not windows.empty else 0
    _add(
        checks,
        "all_available_walk_forward_folds_used",
        observed_folds == expected_folds,
        observed_folds,
        expected_folds,
    )

    _add(
        checks,
        "primary_risk_free_series_nonzero",
        not rf.empty and pd.to_numeric(rf["annual_rate"], errors="coerce").gt(0).any(),
        float(pd.to_numeric(rf.get("annual_rate"), errors="coerce").mean()),
        "positive ^IRX evidence",
    )
    rf_dates = set(pd.to_datetime(rf.get("Date"), errors="coerce"))
    oos_dates = set(walk_returns["Date"])
    _add(
        checks,
        "risk_free_covers_all_oos_dates",
        oos_dates.issubset(rf_dates),
        len(oos_dates - rf_dates),
        0,
    )

    independent_ok, independent_details = _independent_oos_metrics(
        walk_returns, comparison, rf
    )
    _add(
        checks,
        "every_oos_metric_independently_recomputed",
        independent_ok,
        independent_details,
        "within 1e-10",
    )

    balanced = str(decision.get("balanced_research_portfolio", ""))
    role_balanced = (
        role_weights.loc[
            role_weights["portfolio_role"].astype(str).eq("balanced_research_portfolio")
        ]
        if not role_weights.empty
        else pd.DataFrame()
    )
    _add(
        checks,
        "balanced_role_weights_match_decision",
        not role_balanced.empty
        and role_balanced["model_name"].astype(str).eq(balanced).all()
        and role_balanced["ticker"].nunique() == policy.target_holdings,
        {"decision": balanced, "rows": len(role_balanced)},
        "same model and 20 holdings",
    )
    static_ok, static_details = _independent_static_risk(
        role_balanced, returns, risk, rf
    )
    _add(
        checks,
        "published_risk_matches_exact_current_weights",
        static_ok,
        static_details,
        "within 1e-10",
    )

    primary_status = (
        active_league.set_index("model_name")["actual_status"].astype(str).to_dict()
    )
    allowed_status = {
        "Equal Weight": "benchmark_only",
        **{model: "actually_run" for model in PRIMARY_MODELS - {"Equal Weight"}},
    }
    _add(
        checks,
        "no_optimizer_silent_fallback",
        primary_status == allowed_status,
        primary_status,
        allowed_status,
    )
    selected_matrix = returns.reindex(columns=selected["ticker"].astype(str)).dropna(
        how="any"
    )
    _add(
        checks,
        "no_missing_return_treated_as_zero",
        len(selected_matrix) == len(returns),
        {"common_rows": len(selected_matrix), "all_rows": len(returns)},
        "equal rows; no imputation",
    )
    _add(
        checks,
        "final_selection_uses_stitched_oos_evidence",
        str(decision.get("final_model_selection_method", "")).startswith(
            "paired_block_bootstrap"
        ),
        decision.get("final_model_selection_method"),
        "paired bootstrap and stitched OOS",
    )

    run_ids = _single_run_ids(
        [selected, weights, walk_weights, walk_returns, comparison, risk, rf]
    )
    _add(
        checks,
        "no_stale_or_mixed_run_artifacts",
        len(run_ids) == 1,
        sorted(run_ids),
        "one run_id",
    )
    role_names = set(
        role_weights.get("portfolio_role", pd.Series(dtype=str)).astype(str)
    )
    _add(
        checks,
        "three_part_decision_complete",
        role_names
        == {
            "balanced_research_portfolio",
            "transparent_benchmark",
            "defensive_alternative",
        },
        sorted(role_names),
        "three canonical roles",
    )

    failed = [row for row in checks if not bool(row["passed"])]
    return {
        "overall_status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "checks": checks,
        "summary": {
            "declared_scope": v2.get("declared_scope"),
            "target_holdings": policy.target_holdings,
            "balanced_research_portfolio": balanced,
            "transparent_benchmark": decision.get("transparent_benchmark"),
            "defensive_alternative": decision.get("defensive_alternative"),
            "oos_folds": observed_folds,
            "oos_observations": next(iter(obs.values()), 0),
        },
    }


def _independent_oos_metrics(
    returns_long: pd.DataFrame,
    comparison: pd.DataFrame,
    risk_free: pd.DataFrame,
) -> tuple[bool, dict[str, object]]:
    hurdle = risk_free.copy()
    hurdle["Date"] = pd.to_datetime(hurdle["Date"], errors="coerce")
    hurdle_map = hurdle.set_index("Date")["daily_hurdle"].astype(float)
    reported = comparison.set_index("model_name")
    details: dict[str, object] = {}
    passed = True
    mapping = {
        "oos_cagr": "cagr",
        "oos_annualized_return": "annualized_return",
        "oos_volatility": "volatility",
        "oos_sharpe": "sharpe",
        "oos_sortino": "sortino",
        "oos_max_drawdown": "max_drawdown",
        "oos_cvar_95": "cvar_95",
    }
    for model, group in returns_long.groupby("model_name"):
        series = group.sort_values("Date").set_index("Date")["return"].astype(float)
        metrics = _metrics(series, hurdle_map.reindex(series.index))
        deltas = {
            source: abs(float(reported.loc[model, source]) - metrics[target])
            for source, target in mapping.items()
        }
        details[str(model)] = max(deltas.values())
        passed = passed and max(deltas.values()) <= 1e-10
    return bool(passed), details


def _independent_static_risk(
    role_weights: pd.DataFrame,
    returns: pd.DataFrame,
    risk: pd.DataFrame,
    risk_free: pd.DataFrame,
) -> tuple[bool, dict[str, object]]:
    if role_weights.empty:
        return False, {"reason": "missing balanced weights"}
    model = str(role_weights["model_name"].iloc[0])
    weights = role_weights.set_index("ticker")["weight"].astype(float)
    matrix = returns.reindex(columns=weights.index).dropna(how="any")
    series = matrix.mul(weights, axis=1).sum(axis=1)
    hurdle = risk_free.copy()
    hurdle["Date"] = pd.to_datetime(hurdle["Date"], errors="coerce")
    metrics = _metrics(
        series, hurdle.set_index("Date")["daily_hurdle"].reindex(series.index)
    )
    row = risk.loc[risk["model_name"].astype(str).eq(model)]
    if row.empty:
        return False, {"reason": f"missing risk row for {model}"}
    reported = row.iloc[0]
    mapping = {
        "cagr": "cagr",
        "annualized_return": "annualized_return",
        "annualized_volatility": "volatility",
        "sharpe": "sharpe",
        "sortino": "sortino",
        "max_drawdown": "max_drawdown",
        "var_95": "var_95",
        "cvar_95": "cvar_95",
    }
    deltas = {
        column: abs(float(reported[column]) - metrics[target])
        for column, target in mapping.items()
    }
    return max(deltas.values()) <= 1e-10, deltas


def _metrics(series: pd.Series, daily_hurdle: pd.Series) -> dict[str, float]:
    values = series.astype(float)
    hurdle = daily_hurdle.astype(float)
    if values.isna().any() or hurdle.isna().any():
        raise ValueError("Independent metrics require complete return and RF dates.")
    wealth = (1.0 + values).cumprod()
    total = float(wealth.iloc[-1] - 1.0)
    cagr = float((1.0 + total) ** (TRADING_DAYS_PER_YEAR / len(values)) - 1.0)
    volatility = float(values.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    excess = values - hurdle
    annual_excess = float(excess.mean() * TRADING_DAYS_PER_YEAR)
    downside = excess.clip(upper=0.0)
    downside_vol = float(
        np.sqrt(np.mean(np.square(downside))) * np.sqrt(TRADING_DAYS_PER_YEAR)
    )
    drawdown = wealth / wealth.cummax() - 1.0
    var = float(values.quantile(0.05))
    tail = values.loc[values <= var]
    return {
        "cagr": cagr,
        "annualized_return": float(values.mean() * TRADING_DAYS_PER_YEAR),
        "volatility": volatility,
        "sharpe": annual_excess / volatility if volatility > 0 else 0.0,
        "sortino": annual_excess / downside_vol if downside_vol > 0 else 0.0,
        "max_drawdown": float(drawdown.min()),
        "var_95": var,
        "cvar_95": float(tail.mean()),
    }


def _single_run_ids(frames: list[pd.DataFrame]) -> set[str]:
    values: set[str] = set()
    for frame in frames:
        if not frame.empty and "run_id" in frame:
            values.update(frame["run_id"].dropna().astype(str).unique())
    return values


def _add(
    rows: list[dict[str, object]],
    check: str,
    passed: bool,
    observed: object,
    expected: object,
) -> None:
    rows.append(
        {
            "check": check,
            "passed": bool(passed),
            "observed": json.dumps(observed, default=str, sort_keys=True),
            "expected": json.dumps(expected, default=str, sort_keys=True),
        }
    )


def _slug(value: object) -> str:
    return "_".join(str(value).lower().replace("-", " ").split())


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_returns(path: Path) -> pd.DataFrame:
    frame = _read_csv(path)
    if frame.empty:
        return frame
    first = frame.columns[0]
    frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame.apply(pd.to_numeric, errors="coerce")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
