"""Robust model-selection and random-benchmark utilities for QuantVerse v2.

This layer does not create new allocation models. It reads existing model
league, walk-forward, risk and benchmark evidence, then decides what can be
called a defensible public-data final model. The decision is deliberately
conservative: a diagnostic or blocked model cannot become the final selected
model, and an active model must improve on Equal Weight after risk and cost
checks before it can displace the benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_numerical_integrity import portfolio_return_series
from project.research.global_portfolio_risk import evaluate_return_series

ELIGIBLE_FINAL_STATUSES = {"actually_run", "benchmark_only"}
EXCLUDED_FINAL_STATUSES = {
    "diagnostic_only",
    "blocked_by_data",
    "blocked_by_implementation",
    "future_candidate",
}

MODEL_SELECTION_COLUMNS = [
    "model_name",
    "model_status",
    "eligible_final_model",
    "constraint_pass",
    "walk_forward_supported",
    "walk_forward_annualized_return",
    "walk_forward_volatility",
    "walk_forward_sharpe",
    "walk_forward_sortino",
    "walk_forward_max_drawdown",
    "walk_forward_cvar_95",
    "transaction_cost_adjusted_return",
    "turnover",
    "effective_holdings",
    "concentration_warning",
    "league_cagr",
    "league_annualized_return",
    "league_volatility",
    "league_sharpe",
    "league_max_drawdown",
    "league_cvar_95",
    "random_benchmark_scope",
    "random_return_percentile",
    "random_volatility_percentile",
    "random_sharpe_percentile",
    "random_max_drawdown_percentile",
    "random_cvar_percentile",
    "beats_equal_weight_return_after_costs",
    "beats_equal_weight_sharpe",
    "drawdown_not_materially_worse_than_equal_weight",
    "cvar_not_materially_worse_than_equal_weight",
    "sharpe_improvement_vs_equal_weight",
    "uncertainty_status",
    "uncertainty_method",
    "paired_oos_observations",
    "sharpe_diff_ci_lower",
    "sharpe_diff_ci_upper",
    "probability_sharpe_improvement",
    "uncertainty_gate_pass",
    "turnover_within_limit",
    "random_sharpe_gate_pass",
    "robustness_gate_pass",
    "forecast_validation_gate_pass",
    "uses_forecast",
    "forecast_validation_status",
    "robustness_status",
    "extreme_metric_warning",
    "data_limitation_warning",
    "selection_score",
    "book_grounded_score",
    "book_grounded_rank",
    "selection_label",
    "promotion_gate_failed_reasons",
    "rejection_reason",
]

MODEL_SELECTION_DIAGNOSTIC_COLUMNS = [
    "model_name",
    "model_status",
    "eligible_final_model",
    "in_sample_annualized_return",
    "in_sample_volatility",
    "in_sample_sharpe",
    "walk_forward_annualized_return",
    "walk_forward_volatility",
    "walk_forward_sharpe",
    "walk_forward_sortino",
    "walk_forward_max_drawdown",
    "walk_forward_cvar_95",
    "transaction_cost_adjusted_return",
    "turnover",
    "random_benchmark_scope",
    "random_sharpe_percentile",
    "random_cvar_percentile",
    "equal_weight_return_delta",
    "equal_weight_sharpe_delta",
    "equal_weight_drawdown_delta",
    "equal_weight_cvar_delta",
    "uncertainty_status",
    "sharpe_diff_ci_lower",
    "sharpe_diff_ci_upper",
    "probability_sharpe_improvement",
    "uncertainty_gate_pass",
    "constraint_pass",
    "robustness_status",
    "promotion_gate_failed_reasons",
    "book_grounded_final_score",
    "book_grounded_rank",
]

RANDOM_DISTRIBUTION_COLUMNS = [
    "portfolio_id",
    "sampling_method",
    "benchmark_scope",
    "weight_sum",
    "max_weight_observed",
    "cagr",
    "annualized_return",
    "volatility",
    "sharpe",
    "sortino",
    "max_drawdown",
    "var_95",
    "cvar_95",
    "calmar",
    "total_return",
]

RANDOM_PERCENTILE_COLUMNS = [
    "model_name",
    "return_percentile",
    "volatility_percentile",
    "sharpe_percentile",
    "max_drawdown_percentile",
    "cvar_percentile",
    "better_than_random_median_sharpe",
    "better_than_random_75th_sharpe",
    "better_than_random_90th_sharpe",
    "benchmark_interpretation",
]


def simulate_constrained_random_distribution(
    returns: pd.DataFrame,
    *,
    n_portfolios: int = 1000,
    max_weight: float = 0.10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Simulate capped long-only random portfolios on the same return matrix."""
    clean = _clean_returns(returns)
    if clean.empty:
        return pd.DataFrame(columns=RANDOM_DISTRIBUTION_COLUMNS)
    if float(max_weight) * clean.shape[1] < 1.0 - 1e-12:
        raise ValueError("max_weight is infeasible for the selected universe.")

    rng = np.random.default_rng(int(random_state))
    rows: list[dict[str, float | int]] = []
    for portfolio_id in range(int(n_portfolios)):
        raw = pd.Series(rng.random(clean.shape[1]), index=clean.columns)
        weights = _cap_and_normalize(raw, float(max_weight))
        metrics = evaluate_return_series(portfolio_return_series(clean, weights))
        rows.append(
            {
                "portfolio_id": portfolio_id,
                "sampling_method": (
                    "iid_uniform_raw_scores_projected_to_capped_simplex"
                ),
                "benchmark_scope": "full_sample_static_weights_diagnostic",
                "weight_sum": float(weights.sum()),
                "max_weight_observed": float(weights.max()),
                "cagr": float(metrics["cagr"]),
                "annualized_return": float(metrics["annualized_return"]),
                "volatility": float(metrics["annualized_volatility"]),
                "sharpe": float(metrics["sharpe"]),
                "sortino": float(metrics["sortino"]),
                "max_drawdown": float(metrics["max_drawdown"]),
                "var_95": float(metrics["var_95"]),
                "cvar_95": float(metrics["cvar_95"]),
                "calmar": float(metrics["calmar"]),
                "total_return": float(metrics["total_return"]),
            }
        )
    return pd.DataFrame(rows, columns=RANDOM_DISTRIBUTION_COLUMNS)


def build_random_percentile_report(
    league: pd.DataFrame,
    random_distribution: pd.DataFrame,
) -> pd.DataFrame:
    """Compare each executable model with the random portfolio distribution."""
    if league.empty or random_distribution.empty:
        return pd.DataFrame(columns=RANDOM_PERCENTILE_COLUMNS)
    randoms = random_distribution.copy()
    rows: list[dict[str, object]] = []
    for _, row in league.iterrows():
        model = str(row.get("model_name", ""))
        sharpe = _float(row.get("sharpe"))
        annualized_return = _float(row.get("annualized_return"))
        volatility = _float(row.get("volatility"))
        drawdown = _float(row.get("max_drawdown"))
        cvar = _float(row.get("cvar_95"))
        sharpe_percentile = _higher_is_better_percentile(randoms["sharpe"], sharpe)
        rows.append(
            {
                "model_name": model,
                "return_percentile": _higher_is_better_percentile(
                    randoms["annualized_return"], annualized_return
                ),
                "volatility_percentile": _lower_is_better_percentile(
                    randoms["volatility"], volatility
                ),
                "sharpe_percentile": sharpe_percentile,
                "max_drawdown_percentile": _higher_is_better_percentile(
                    randoms["max_drawdown"], drawdown
                ),
                "cvar_percentile": _higher_is_better_percentile(
                    randoms["cvar_95"], cvar
                ),
                "better_than_random_median_sharpe": bool(sharpe_percentile >= 0.50),
                "better_than_random_75th_sharpe": bool(sharpe_percentile >= 0.75),
                "better_than_random_90th_sharpe": bool(sharpe_percentile >= 0.90),
                "benchmark_interpretation": (
                    "Random percentile is a benchmark context, not proof of future superiority."
                ),
            }
        )
    return pd.DataFrame(rows, columns=RANDOM_PERCENTILE_COLUMNS)


def build_model_selection_report(
    league: pd.DataFrame,
    walk_forward: pd.DataFrame | None = None,
    risk_report: pd.DataFrame | None = None,
    turnover: pd.DataFrame | None = None,
    random_percentiles: pd.DataFrame | None = None,
    *,
    drawdown_tolerance: float = 0.05,
    cvar_tolerance: float = 0.005,
    min_sharpe_improvement_vs_equal_weight: float = 0.0,
    min_random_sharpe_percentile: float = 0.60,
    max_turnover: float = 2.0,
    forecast_validation_status: str = "diagnostic_only",
    robustness_status: str = "stable",
    random_benchmark_scope: str = "walk_forward_oos_net",
) -> pd.DataFrame:
    """Score final model candidates using risk, cost and validation evidence."""
    if league.empty:
        return pd.DataFrame(columns=MODEL_SELECTION_COLUMNS)

    walk_map = _index_by_model(walk_forward)
    risk_map = _index_by_model(risk_report)
    random_map = _index_by_model(random_percentiles)
    turnover_map = _turnover_by_model(turnover)
    equal_weight = _evidence_row(
        "Equal Weight",
        league,
        walk_map,
        risk_map,
        random_map,
        turnover_map,
        drawdown_tolerance=drawdown_tolerance,
        cvar_tolerance=cvar_tolerance,
        min_sharpe_improvement_vs_equal_weight=min_sharpe_improvement_vs_equal_weight,
        min_random_sharpe_percentile=min_random_sharpe_percentile,
        max_turnover=max_turnover,
        forecast_validation_status=forecast_validation_status,
        robustness_status=robustness_status,
        random_benchmark_scope=random_benchmark_scope,
    )
    rows = []
    for _, _row in league.iterrows():
        model = str(_row.get("model_name", ""))
        rows.append(
            _evidence_row(
                model,
                league,
                walk_map,
                risk_map,
                random_map,
                turnover_map,
                equal_weight=equal_weight,
                drawdown_tolerance=drawdown_tolerance,
                cvar_tolerance=cvar_tolerance,
                min_sharpe_improvement_vs_equal_weight=min_sharpe_improvement_vs_equal_weight,
                min_random_sharpe_percentile=min_random_sharpe_percentile,
                max_turnover=max_turnover,
                forecast_validation_status=forecast_validation_status,
                robustness_status=robustness_status,
                random_benchmark_scope=random_benchmark_scope,
            )
        )
    frame = pd.DataFrame(rows, columns=MODEL_SELECTION_COLUMNS)
    frame = frame.sort_values(
        ["eligible_final_model", "selection_score"], ascending=[False, False]
    ).reset_index(drop=True)
    frame["book_grounded_rank"] = (
        frame["selection_score"].rank(method="first", ascending=False).astype(int)
    )
    frame["book_grounded_score"] = frame["selection_score"]
    return frame.reindex(columns=MODEL_SELECTION_COLUMNS)


def build_final_model_decision(selection_report: pd.DataFrame) -> dict[str, object]:
    """Build a conservative final-model decision from a selection report."""
    if selection_report.empty:
        return _not_available_decision("No model-selection evidence was available.")

    candidates = selection_report.loc[
        selection_report["eligible_final_model"].astype(bool)
    ].copy()
    equal_weight = candidates.loc[candidates["model_name"].eq("Equal Weight")]
    if equal_weight.empty:
        return _not_available_decision(
            "No eligible Equal Weight benchmark evidence was available; active "
            "models cannot be selected without a valid common benchmark."
        )

    if candidates.empty:
        return _not_available_decision(
            "No eligible actually-run or benchmark model passed constraints."
        )
    else:
        active = candidates.loc[~candidates["model_name"].eq("Equal Weight")].copy()
        active["active_gate_pass"] = (
            (active["sharpe_improvement_vs_equal_weight"] >= 0.0)
            & active["beats_equal_weight_sharpe"].astype(bool)
            & active["drawdown_not_materially_worse_than_equal_weight"].astype(bool)
            & active["cvar_not_materially_worse_than_equal_weight"].astype(bool)
            & active["turnover_within_limit"].astype(bool)
            & active["random_sharpe_gate_pass"].astype(bool)
            & active["uncertainty_gate_pass"].astype(bool)
            & active["robustness_gate_pass"].astype(bool)
            & active["forecast_validation_gate_pass"].astype(bool)
            & active["extreme_metric_warning"]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("none")
        )
        if active["active_gate_pass"].any():
            final = (
                active.loc[active["active_gate_pass"]]
                .sort_values(
                    [
                        "walk_forward_sharpe",
                        "walk_forward_annualized_return",
                        "walk_forward_max_drawdown",
                        "walk_forward_cvar_95",
                        "turnover",
                        "model_name",
                    ],
                    ascending=[False, False, False, False, True, True],
                )
                .iloc[0]
            )
            reason = (
                f"{final['model_name']} is selected as the book-grounded public-data "
                "research final model because paired block-bootstrap uncertainty, "
                "walk-forward return per unit risk, drawdown, CVaR, turnover, "
                "robustness, random-benchmark and metric-review gates clear the "
                "policy limits. This is still not investment advice or "
                "institutional PIT evidence."
            )
            promoted = False
        else:
            final = equal_weight.iloc[0]
            reason = (
                "Equal Weight remains the defensible benchmark; no active model is "
                "selected because active candidates did not clear the book-grounded "
                "walk-forward Sharpe, paired uncertainty, drawdown, CVaR, turnover, "
                "robustness, random-benchmark and metric-review gates."
            )
            promoted = False

    final_model = str(final["model_name"])
    comparison = _final_equal_weight_comparison(final, final_model)
    return {
        "final_selected_model": final_model,
        "final_model_selection_method": ("paired_block_bootstrap_gate_then_oos_sharpe"),
        "final_model_selection_score": float(final["selection_score"]),
        "final_decision": "not promoted" if not promoted else "promoted",
        "final_decision_reason": reason,
        "equal_weight_comparison": comparison,
        "random_portfolio_percentile": _none_if_nan(
            final.get("random_sharpe_percentile")
        ),
        "final_model_book_grounded_rank": int(final.get("book_grounded_rank", 0)),
        "final_model_gate_reasons": str(
            final.get(
                "promotion_gate_failed_reasons", final.get("rejection_reason", "")
            )
        ),
        "publish_readiness_status": (
            "research_publish_ready_with_limitations"
            if str(final["model_name"])
            else "not ready"
        ),
        "hard_limitations": [
            "Official exact top-100 support remains unavailable.",
            "Point-in-time historical membership remains unavailable.",
            "Delisting and corporate-action institutional evidence remains unavailable.",
            "Public-data walk-forward is not an institutional PIT backtest.",
        ],
    }


def _not_available_decision(reason: str) -> dict[str, object]:
    return {
        "final_selected_model": "not_available",
        "final_model_selection_method": "paired_block_bootstrap_gate_then_oos_sharpe",
        "final_model_selection_score": None,
        "final_decision": "not promoted",
        "final_decision_reason": str(reason),
        "equal_weight_comparison": {
            "comparison_status": "not_available",
            "beats_equal_weight_return_after_costs": None,
            "beats_equal_weight_sharpe": None,
            "drawdown_not_materially_worse_than_equal_weight": None,
            "cvar_not_materially_worse_than_equal_weight": None,
        },
        "random_portfolio_percentile": None,
        "final_model_book_grounded_rank": 0,
        "final_model_gate_reasons": str(reason),
        "publish_readiness_status": "not ready",
        "hard_limitations": [
            "A valid Equal Weight benchmark and comparable model evidence are required."
        ],
    }


def _final_equal_weight_comparison(
    final: pd.Series, final_model: str
) -> dict[str, object]:
    """Describe a genuine challenger comparison without treating EW as its own win."""
    if final_model == "Equal Weight":
        return {
            "comparison_status": "benchmark_self_comparison_not_applicable",
            "beats_equal_weight_return_after_costs": None,
            "beats_equal_weight_sharpe": None,
            "drawdown_not_materially_worse_than_equal_weight": None,
            "cvar_not_materially_worse_than_equal_weight": None,
        }
    return {
        "comparison_status": "active_model_vs_equal_weight",
        "beats_equal_weight_return_after_costs": bool(
            final.get("beats_equal_weight_return_after_costs", False)
        ),
        "beats_equal_weight_sharpe": bool(
            final.get("beats_equal_weight_sharpe", False)
        ),
        "drawdown_not_materially_worse_than_equal_weight": bool(
            final.get("drawdown_not_materially_worse_than_equal_weight", False)
        ),
        "cvar_not_materially_worse_than_equal_weight": bool(
            final.get("cvar_not_materially_worse_than_equal_weight", False)
        ),
    }


def write_model_selection_outputs(
    selection_report: pd.DataFrame,
    decision: dict[str, object],
    random_distribution: pd.DataFrame,
    random_percentiles: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    """Write model-selection and random-benchmark outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    selection_report.to_csv(path / "global_model_selection_report.csv", index=False)
    random_distribution.to_csv(
        path / "global_random_portfolio_distribution.csv", index=False
    )
    random_percentiles.to_csv(
        path / "global_random_portfolio_percentile_report.csv", index=False
    )
    diagnostics = build_model_selection_diagnostics(selection_report)
    diagnostics.to_csv(path / "global_model_selection_diagnostics.csv", index=False)
    pd.DataFrame(
        [{"field": key, "value": value} for key, value in decision.items()]
    ).to_csv(path / "global_final_model_decision.csv", index=False)
    (path / "global_final_model_decision.json").write_text(
        json.dumps(decision, indent=2, default=str), encoding="utf-8"
    )


def build_model_selection_diagnostics(selection_report: pd.DataFrame) -> pd.DataFrame:
    """Build a transparent book-grounded model selection diagnostic table."""
    if selection_report.empty:
        return pd.DataFrame(columns=MODEL_SELECTION_DIAGNOSTIC_COLUMNS)
    frame = selection_report.copy()
    ew = _equal_weight_or_first(frame)
    diagnostics = pd.DataFrame(
        {
            "model_name": frame["model_name"],
            "model_status": frame["model_status"],
            "eligible_final_model": frame["eligible_final_model"],
            "in_sample_annualized_return": frame["league_annualized_return"],
            "in_sample_volatility": frame.get("league_volatility", np.nan),
            "in_sample_sharpe": frame["league_sharpe"],
            "walk_forward_annualized_return": frame["walk_forward_annualized_return"],
            "walk_forward_volatility": frame["walk_forward_volatility"],
            "walk_forward_sharpe": frame["walk_forward_sharpe"],
            "walk_forward_sortino": frame["walk_forward_sortino"],
            "walk_forward_max_drawdown": frame["walk_forward_max_drawdown"],
            "walk_forward_cvar_95": frame["walk_forward_cvar_95"],
            "transaction_cost_adjusted_return": frame[
                "transaction_cost_adjusted_return"
            ],
            "turnover": frame["turnover"],
            "random_benchmark_scope": frame["random_benchmark_scope"],
            "random_sharpe_percentile": frame["random_sharpe_percentile"],
            "random_cvar_percentile": frame["random_cvar_percentile"],
            "equal_weight_return_delta": frame["walk_forward_annualized_return"]
            - float(ew["walk_forward_annualized_return"]),
            "equal_weight_sharpe_delta": frame["walk_forward_sharpe"]
            - float(ew["walk_forward_sharpe"]),
            "equal_weight_drawdown_delta": frame["walk_forward_max_drawdown"]
            - float(ew["walk_forward_max_drawdown"]),
            "equal_weight_cvar_delta": frame["walk_forward_cvar_95"]
            - float(ew["walk_forward_cvar_95"]),
            "uncertainty_status": frame["uncertainty_status"],
            "sharpe_diff_ci_lower": frame["sharpe_diff_ci_lower"],
            "sharpe_diff_ci_upper": frame["sharpe_diff_ci_upper"],
            "probability_sharpe_improvement": frame["probability_sharpe_improvement"],
            "uncertainty_gate_pass": frame["uncertainty_gate_pass"],
            "constraint_pass": frame["constraint_pass"],
            "robustness_status": frame["robustness_status"],
            "promotion_gate_failed_reasons": frame["promotion_gate_failed_reasons"],
            "book_grounded_final_score": frame["book_grounded_score"],
            "book_grounded_rank": frame["book_grounded_rank"],
        }
    )
    return diagnostics.reindex(columns=MODEL_SELECTION_DIAGNOSTIC_COLUMNS)


def _evidence_row(
    model: str,
    league: pd.DataFrame,
    walk_map: dict[str, pd.Series],
    risk_map: dict[str, pd.Series],
    random_map: dict[str, pd.Series],
    turnover_map: dict[str, float],
    *,
    equal_weight: dict[str, object] | None = None,
    drawdown_tolerance: float,
    cvar_tolerance: float,
    min_sharpe_improvement_vs_equal_weight: float,
    min_random_sharpe_percentile: float,
    max_turnover: float,
    forecast_validation_status: str,
    robustness_status: str,
    random_benchmark_scope: str,
) -> dict[str, object]:
    league_row = league.loc[league["model_name"].astype(str).eq(model)]
    league_row = league_row.iloc[0] if not league_row.empty else pd.Series(dtype=object)
    walk = walk_map.get(model, pd.Series(dtype=object))
    risk = risk_map.get(model, pd.Series(dtype=object))
    random_row = random_map.get(model, pd.Series(dtype=object))

    status = str(league_row.get("actual_status", "blocked_by_implementation"))
    constraint_pass = _bool(league_row.get("constraints_pass", False))
    eligible = bool(
        status in ELIGIBLE_FINAL_STATUSES
        and constraint_pass
        and model != "Random Portfolios"
    )
    wf_supported = not walk.empty
    wf_return = _coalesce_float(
        walk.get("oos_annualized_return"),
        walk.get("avg_annualized_return"),
        league_row.get("annualized_return"),
    )
    wf_vol = _coalesce_float(
        walk.get("oos_volatility"),
        walk.get("avg_volatility"),
        league_row.get("volatility"),
    )
    wf_sharpe = _coalesce_float(
        walk.get("oos_sharpe"),
        walk.get("avg_sharpe"),
        league_row.get("sharpe"),
    )
    wf_sortino = _coalesce_float(
        walk.get("oos_sortino"),
        walk.get("avg_sortino"),
        league_row.get("sortino"),
    )
    wf_drawdown = _coalesce_float(
        walk.get("oos_max_drawdown"),
        walk.get("avg_max_drawdown"),
        league_row.get("max_drawdown"),
    )
    wf_cvar = _coalesce_float(
        walk.get("oos_cvar_95"),
        walk.get("avg_cvar_95"),
        league_row.get("cvar_95"),
    )
    model_turnover = _coalesce_float(
        walk.get("avg_turnover"),
        turnover_map.get(model),
        league_row.get("turnover"),
        0.0,
    )
    random_sharpe = _float(random_row.get("sharpe_percentile"))
    if np.isnan(random_sharpe):
        random_sharpe = _float(random_row.get("random_sharpe_percentile"))

    if equal_weight is None:
        ew_return = wf_return
        ew_sharpe = wf_sharpe
        ew_drawdown = wf_drawdown
        ew_cvar = wf_cvar
    else:
        ew_return = _float(equal_weight["transaction_cost_adjusted_return"])
        ew_sharpe = _float(equal_weight["walk_forward_sharpe"])
        ew_drawdown = _float(equal_weight["walk_forward_max_drawdown"])
        ew_cvar = _float(equal_weight["walk_forward_cvar_95"])

    sharpe_improvement = wf_sharpe - ew_sharpe
    is_equal_weight = model == "Equal Weight"
    beats_return = bool(wf_return > ew_return + 1e-12) if not is_equal_weight else False
    beats_sharpe = (
        bool(
            sharpe_improvement >= float(min_sharpe_improvement_vs_equal_weight) - 1e-12
        )
        if not is_equal_weight
        else False
    )
    drawdown_ok = (
        bool(wf_drawdown >= ew_drawdown - float(drawdown_tolerance))
        if model != "Equal Weight"
        else True
    )
    cvar_ok = (
        bool(wf_cvar >= ew_cvar - float(cvar_tolerance))
        if model != "Equal Weight"
        else True
    )
    turnover_ok = bool(model_turnover <= float(max_turnover) + 1e-12)
    random_scope_valid = str(random_benchmark_scope) == "walk_forward_oos_net"
    random_ok = bool(
        random_scope_valid
        and random_sharpe >= float(min_random_sharpe_percentile) - 1e-12
    )
    robust_ok = not _fragile_robustness(robustness_status)
    uncertainty_status = str(walk.get("uncertainty_status", "missing"))
    uncertainty_method = str(walk.get("uncertainty_method", "not_available"))
    paired_observations = _float(walk.get("paired_observations"))
    sharpe_ci_lower = _float(walk.get("sharpe_diff_ci_lower"))
    sharpe_ci_upper = _float(walk.get("sharpe_diff_ci_upper"))
    probability_sharpe_improvement = _float(walk.get("probability_sharpe_improvement"))
    uncertainty_ok = bool(
        is_equal_weight
        or (
            uncertainty_status == "completed"
            and np.isfinite(sharpe_ci_lower)
            and sharpe_ci_lower > 0.0
        )
    )
    uses_forecast = _uses_forecast_model(model)
    forecast_ok = not (
        uses_forecast
        and str(forecast_validation_status).lower()
        in {"failed_scale_sanity", "missing", "not_run"}
    )
    warning = _warning_from_risk(risk)
    data_warning = (
        "public_data_current_universe_not_institutional_pit; "
        "official_exact_top100_and_delisting_evidence_missing"
    )
    score = _selection_score(
        eligible=eligible,
        wf_sharpe=wf_sharpe,
    )
    rejection = _rejection_reason(
        model=model,
        status=status,
        eligible=eligible,
        constraint_pass=constraint_pass,
        beats_return=beats_return,
        beats_sharpe=beats_sharpe,
        drawdown_ok=drawdown_ok,
        cvar_ok=cvar_ok,
        random_sharpe=random_sharpe,
        min_random_sharpe_percentile=min_random_sharpe_percentile,
        turnover_ok=turnover_ok,
        max_turnover=max_turnover,
        robust_ok=robust_ok,
        uncertainty_ok=uncertainty_ok,
        uncertainty_status=uncertainty_status,
        sharpe_ci_lower=sharpe_ci_lower,
        sharpe_ci_upper=sharpe_ci_upper,
        forecast_ok=forecast_ok,
        min_sharpe_improvement_vs_equal_weight=min_sharpe_improvement_vs_equal_weight,
        sharpe_improvement=sharpe_improvement,
        warning=warning,
        random_benchmark_scope=random_benchmark_scope,
    )
    return {
        "model_name": model,
        "model_status": status,
        "eligible_final_model": eligible,
        "constraint_pass": constraint_pass,
        "walk_forward_supported": wf_supported,
        "walk_forward_annualized_return": wf_return,
        "walk_forward_volatility": wf_vol,
        "walk_forward_sharpe": wf_sharpe,
        "walk_forward_sortino": wf_sortino,
        "walk_forward_max_drawdown": wf_drawdown,
        "walk_forward_cvar_95": wf_cvar,
        "transaction_cost_adjusted_return": wf_return,
        "turnover": model_turnover,
        "effective_holdings": _float(league_row.get("effective_holdings")),
        "concentration_warning": str(league_row.get("concentration_warning", "none")),
        "league_cagr": _float(league_row.get("cagr")),
        "league_annualized_return": _float(league_row.get("annualized_return")),
        "league_volatility": _float(league_row.get("volatility")),
        "league_sharpe": _float(league_row.get("sharpe")),
        "league_max_drawdown": _float(league_row.get("max_drawdown")),
        "league_cvar_95": _float(league_row.get("cvar_95")),
        "random_benchmark_scope": str(random_benchmark_scope),
        "random_return_percentile": _float(random_row.get("return_percentile")),
        "random_volatility_percentile": _float(random_row.get("volatility_percentile")),
        "random_sharpe_percentile": random_sharpe,
        "random_max_drawdown_percentile": _float(
            random_row.get("max_drawdown_percentile")
        ),
        "random_cvar_percentile": _float(random_row.get("cvar_percentile")),
        "beats_equal_weight_return_after_costs": beats_return,
        "beats_equal_weight_sharpe": beats_sharpe,
        "drawdown_not_materially_worse_than_equal_weight": drawdown_ok,
        "cvar_not_materially_worse_than_equal_weight": cvar_ok,
        "sharpe_improvement_vs_equal_weight": sharpe_improvement,
        "uncertainty_status": uncertainty_status,
        "uncertainty_method": uncertainty_method,
        "paired_oos_observations": paired_observations,
        "sharpe_diff_ci_lower": sharpe_ci_lower,
        "sharpe_diff_ci_upper": sharpe_ci_upper,
        "probability_sharpe_improvement": probability_sharpe_improvement,
        "uncertainty_gate_pass": uncertainty_ok,
        "turnover_within_limit": turnover_ok,
        "random_sharpe_gate_pass": random_ok,
        "robustness_gate_pass": robust_ok,
        "forecast_validation_gate_pass": forecast_ok,
        "uses_forecast": uses_forecast,
        "forecast_validation_status": forecast_validation_status,
        "robustness_status": robustness_status,
        "extreme_metric_warning": warning,
        "data_limitation_warning": data_warning,
        "selection_score": score,
        "book_grounded_score": score,
        "book_grounded_rank": 0,
        "selection_label": _selection_label(model, eligible, status),
        "promotion_gate_failed_reasons": rejection,
        "rejection_reason": rejection,
    }


def _selection_score(
    *,
    eligible: bool,
    wf_sharpe: float,
) -> float:
    """Use OOS Sharpe as a transparent rank after all separate evidence gates."""
    if not eligible:
        return -1_000_000.0
    return float(wf_sharpe) if np.isfinite(wf_sharpe) else -1_000_000.0


def _rejection_reason(
    *,
    model: str,
    status: str,
    eligible: bool,
    constraint_pass: bool,
    beats_return: bool,
    beats_sharpe: bool,
    drawdown_ok: bool,
    cvar_ok: bool,
    random_sharpe: float,
    min_random_sharpe_percentile: float,
    turnover_ok: bool,
    max_turnover: float,
    robust_ok: bool,
    uncertainty_ok: bool,
    uncertainty_status: str,
    sharpe_ci_lower: float,
    sharpe_ci_upper: float,
    forecast_ok: bool,
    min_sharpe_improvement_vs_equal_weight: float,
    sharpe_improvement: float,
    warning: str,
    random_benchmark_scope: str,
) -> str:
    if model == "Equal Weight":
        return (
            "benchmark self-comparison is not applicable; Equal Weight remains "
            "eligible when active challengers fail the promotion gates"
        )
    reasons: list[str] = []
    if not eligible:
        if model == "Random Portfolios":
            reasons.append(
                "excluded from final selection because it is a benchmark distribution"
            )
        if status in EXCLUDED_FINAL_STATUSES:
            reasons.append(f"excluded from final selection because status is {status}")
        if not constraint_pass:
            reasons.append("constraints did not pass")
    if model != "Equal Weight":
        if str(random_benchmark_scope) != "walk_forward_oos_net":
            reasons.append(
                "random benchmark is not same-protocol walk-forward OOS net evidence"
            )
        if not beats_sharpe:
            reasons.append(
                "walk-forward Sharpe improvement "
                f"{sharpe_improvement:.4f} is below configured threshold "
                f"{float(min_sharpe_improvement_vs_equal_weight):.4f}"
            )
        if not drawdown_ok:
            reasons.append("drawdown is materially worse than Equal Weight")
        if not cvar_ok:
            reasons.append("CVaR is materially worse than Equal Weight")
        if not turnover_ok:
            reasons.append(f"turnover exceeds configured maximum {float(max_turnover)}")
        if random_sharpe < float(min_random_sharpe_percentile):
            reasons.append(
                "Sharpe random percentile is below configured threshold "
                f"{float(min_random_sharpe_percentile):.2f}"
            )
        if not robust_ok:
            reasons.append("robustness evidence is missing, diagnostic, or fragile")
        if not uncertainty_ok:
            reasons.append(
                "paired block-bootstrap Sharpe-difference uncertainty gate failed "
                f"(status={uncertainty_status}; "
                f"ci=[{sharpe_ci_lower}, {sharpe_ci_upper}])"
            )
        if not forecast_ok:
            reasons.append("forecast validation blocks forecast-driven model promotion")
    if warning and warning != "none":
        reasons.append(f"metric warning: {warning}")
    return "; ".join(reasons) if reasons else "passes conservative selection checks"


def _selection_label(model: str, eligible: bool, status: str) -> str:
    if not eligible:
        return "excluded_from_final_selection"
    if model == "Equal Weight":
        return "defensible_benchmark"
    if status == "benchmark_only":
        return "benchmark"
    return "active_candidate"


def return_per_unit_risk(return_value: float, risk_value: float) -> float:
    """Return per unit risk; higher is better."""
    if not np.isfinite(return_value) or not np.isfinite(risk_value) or risk_value <= 0:
        return float("nan")
    return float(return_value / risk_value)


def risk_per_unit_return(risk_value: float, return_value: float) -> float:
    """Risk per unit return; lower is better when return is positive."""
    if (
        not np.isfinite(return_value)
        or return_value <= 0
        or not np.isfinite(risk_value)
    ):
        return float("nan")
    return float(risk_value / return_value)


def _equal_weight_or_first(frame: pd.DataFrame) -> pd.Series:
    """Return the benchmark for diagnostics, or the top row when it is absent."""
    ew = frame.loc[frame["model_name"].eq("Equal Weight")]
    if not ew.empty:
        return ew.iloc[0]
    return frame.sort_values("selection_score", ascending=False).iloc[0]


def _uses_forecast_model(model: str) -> bool:
    return "forecast" in str(model).lower() or str(model) in {
        "ML Forecast",
        "Ensemble Forecast",
    }


def _fragile_robustness(status: str) -> bool:
    text = str(status).lower()
    return any(
        token in text
        for token in [
            "fragile",
            "unstable",
            "failed",
            "missing",
            "not_run",
            "diagnostic",
            "configuration_stability_only",
            "insufficient",
        ]
    )


def _warning_from_risk(risk: pd.Series) -> str:
    warning = str(risk.get("extreme_metric_warning", "none"))
    if warning.lower() in {"", "nan", "none"}:
        return "none"
    return warning


def _index_by_model(frame: pd.DataFrame | None) -> dict[str, pd.Series]:
    if frame is None or frame.empty or "model_name" not in frame:
        return {}
    return {
        str(model): group.iloc[0]
        for model, group in frame.groupby(frame["model_name"].astype(str), sort=False)
    }


def _turnover_by_model(frame: pd.DataFrame | None) -> dict[str, float]:
    if (
        frame is None
        or frame.empty
        or "model_name" not in frame
        or "turnover" not in frame
    ):
        return {}
    grouped = frame.copy()
    grouped["turnover"] = pd.to_numeric(grouped["turnover"], errors="coerce")
    return (
        grouped.groupby(grouped["model_name"].astype(str))["turnover"].mean().to_dict()
    )


def _higher_is_better_percentile(series: pd.Series, value: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or not np.isfinite(value):
        return float("nan")
    return float((clean <= value).mean())


def _lower_is_better_percentile(series: pd.Series, value: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or not np.isfinite(value):
        return float("nan")
    return float((clean >= value).mean())


def _cap_and_normalize(weights: pd.Series, max_weight: float) -> pd.Series:
    raw = pd.Series(weights, dtype=float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    raw = raw.clip(lower=0.0)
    if raw.sum() <= 0:
        raw = pd.Series(1.0, index=raw.index)
    remaining = list(raw.index)
    capped = pd.Series(0.0, index=raw.index, dtype=float)
    remaining_total = 1.0
    while remaining:
        base = raw.loc[remaining]
        provisional = base / base.sum() * remaining_total
        over = provisional[provisional > max_weight + 1e-12]
        if over.empty:
            capped.loc[remaining] = provisional
            break
        capped.loc[over.index] = max_weight
        remaining_total -= max_weight * len(over)
        remaining = [ticker for ticker in remaining if ticker not in set(over.index)]
    return capped / capped.sum()


def _clean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(clean.columns[0])
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.dropna(axis=1, how="all").dropna(how="all")


def _coalesce_float(*values: object) -> float:
    for value in values:
        converted = _float(value)
        if np.isfinite(converted):
            return converted
    return 0.0


def _float(value: object) -> float:
    try:
        if value is None or pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _none_if_nan(value: object) -> float | None:
    converted = _float(value)
    return None if not np.isfinite(converted) else converted


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}
