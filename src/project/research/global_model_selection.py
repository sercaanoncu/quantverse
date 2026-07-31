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
from typing import Mapping

import numpy as np
import pandas as pd

from project.research.global_numerical_integrity import portfolio_return_series
from project.research.global_portfolio_risk import evaluate_return_series
from project.research.global_stock_selection import apply_max_weight_cap

ELIGIBLE_FINAL_STATUSES = {"actually_run", "benchmark_only"}
EXCLUDED_FINAL_STATUSES = {
    "diagnostic_only",
    "blocked_by_data",
    "blocked_by_implementation",
    "future_candidate",
}
RUN_IDENTITY_FIELDS = (
    "run_id",
    "config_hash",
    "input_fingerprint",
    "universe_snapshot_id",
    "data_snapshot_id",
)
PROMOTION_GRADE_ROBUSTNESS_STATUSES = {
    "promotion_grade_nested_walk_forward_oos",
}
PROMOTION_GRADE_ROBUSTNESS_METHODS = {
    "nested_chronological_walk_forward_oos",
}
VERIFIED_RANDOM_BENCHMARK_STATUS = "verified_same_protocol"

MODEL_SELECTION_COLUMNS = [
    "model_name",
    "model_status",
    "eligible_final_model",
    "constraint_pass",
    "walk_forward_supported",
    "leakage_gate_pass",
    "leakage_evidence_status",
    "leakage_run_id",
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
    "random_benchmark_provenance_status",
    "random_benchmark_protocol_hash",
    "random_benchmark_run_id",
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
    "robustness_evidence_status",
    "robustness_run_id",
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
    "leakage_gate_pass",
    "leakage_evidence_status",
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
    "random_benchmark_provenance_status",
    "random_benchmark_protocol_hash",
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
    "robustness_evidence_status",
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
    rows: list[dict[str, object]] = []
    for portfolio_id in range(int(n_portfolios)):
        raw = pd.Series(rng.random(clean.shape[1]), index=clean.columns)
        weights = apply_max_weight_cap(raw, float(max_weight))
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
                "cagr": _float(metrics["cagr"]),
                "annualized_return": _float(metrics["annualized_return"]),
                "volatility": _float(metrics["annualized_volatility"]),
                "sharpe": _float(metrics["sharpe"]),
                "sortino": _float(metrics["sortino"]),
                "max_drawdown": _float(metrics["max_drawdown"]),
                "var_95": _float(metrics["var_95"]),
                "cvar_95": _float(metrics["cvar_95"]),
                "calmar": _float(metrics["calmar"]),
                "total_return": _float(metrics["total_return"]),
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
    random_distribution: pd.DataFrame | None = None,
    walk_forward_leakage_audit: pd.DataFrame | None = None,
    *,
    drawdown_tolerance: float = 0.05,
    cvar_tolerance: float = 0.005,
    min_sharpe_improvement_vs_equal_weight: float = 0.0,
    min_random_sharpe_percentile: float = 0.60,
    max_turnover: float = 2.0,
    forecast_validation_status: str = "diagnostic_only",
    robustness_evidence: Mapping[str, object] | None = None,
    random_benchmark_provenance: Mapping[str, object] | None = None,
    expected_run_identity: Mapping[str, object] | None = None,
    expected_random_protocol: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Score final model candidates using risk, cost and validation evidence."""
    if league.empty:
        return pd.DataFrame(columns=MODEL_SELECTION_COLUMNS)

    walk_map = _index_by_model(walk_forward)
    risk_map = _index_by_model(risk_report)
    random_map = _index_by_model(random_percentiles)
    turnover_map = _turnover_by_model(turnover)
    robustness_assessment = assess_robustness_evidence(
        robustness_evidence,
        expected_run_identity=expected_run_identity,
    )
    random_assessment = assess_random_benchmark_evidence(
        random_distribution,
        random_benchmark_provenance,
        expected_run_identity=expected_run_identity,
        expected_protocol=expected_random_protocol,
    )
    leakage_assessment = assess_leakage_evidence(
        walk_forward_leakage_audit,
        expected_run_identity=expected_run_identity,
    )
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
        robustness_assessment=robustness_assessment,
        random_assessment=random_assessment,
        leakage_assessment=leakage_assessment,
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
                robustness_assessment=robustness_assessment,
                random_assessment=random_assessment,
                leakage_assessment=leakage_assessment,
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
    """Build balanced, benchmark and defensive decisions from common OOS evidence."""
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

    active = candidates.loc[~candidates["model_name"].eq("Equal Weight")].copy()
    if not active.empty:
        active["active_gate_pass"] = (
            active["uncertainty_status"].astype(str).eq("completed")
            & (pd.to_numeric(active["sharpe_diff_ci_lower"], errors="coerce") > 0.0)
            & active["drawdown_not_materially_worse_than_equal_weight"].astype(bool)
            & active["cvar_not_materially_worse_than_equal_weight"].astype(bool)
            & active["turnover_within_limit"].astype(bool)
            & active["constraint_pass"].astype(bool)
            & active["leakage_gate_pass"].astype(bool)
            & active["random_sharpe_gate_pass"].astype(bool)
            & active["robustness_gate_pass"].astype(bool)
            & active["forecast_validation_gate_pass"].astype(bool)
            & active["extreme_metric_warning"].astype(str).eq("none")
            & active["random_benchmark_provenance_status"]
            .astype(str)
            .eq(VERIFIED_RANDOM_BENCHMARK_STATUS)
            & (
                pd.to_numeric(active["walk_forward_annualized_return"], errors="coerce")
                > 0
            )
        )
    if not active.empty and active["active_gate_pass"].any():
        final = (
            active.loc[active["active_gate_pass"]]
            .sort_values(
                [
                    "walk_forward_sharpe",
                    "walk_forward_max_drawdown",
                    "walk_forward_cvar_95",
                    "turnover",
                    "model_name",
                ],
                ascending=[False, False, False, True, True],
            )
            .iloc[0]
        )
        reason = (
            f"{final['model_name']} replaces Equal Weight as the balanced research "
            "allocation because its paired block-bootstrap Sharpe-difference lower "
            "bound is positive and its drawdown, CVaR, turnover, constraint and "
            "provenance gates pass on common net OOS dates."
        )
    else:
        final = equal_weight.iloc[0]
        reason = (
            "Equal Weight remains the defensible benchmark and is the balanced "
            "research allocation because no active "
            "model proved a positive paired block-bootstrap Sharpe improvement while "
            "also passing drawdown, CVaR, turnover, constraint and provenance gates."
        )

    if active.empty:
        defensive = equal_weight.iloc[0]
    else:
        defensive_pool = candidates.loc[
            (
                pd.to_numeric(
                    candidates["walk_forward_annualized_return"], errors="coerce"
                )
                > 0
            )
            & candidates["constraint_pass"].astype(bool)
            & candidates["leakage_gate_pass"].astype(bool)
        ].copy()
        defensive = (
            defensive_pool.sort_values(
                [
                    "walk_forward_max_drawdown",
                    "walk_forward_cvar_95",
                    "walk_forward_sharpe",
                    "model_name",
                ],
                ascending=[False, False, False, True],
            ).iloc[0]
            if not defensive_pool.empty
            else equal_weight.iloc[0]
        )

    final_model = str(final["model_name"])
    comparison = _final_equal_weight_comparison(final, final_model)
    return {
        "final_selected_model": final_model,
        "final_model_selection_method": ("paired_block_bootstrap_gate_then_oos_sharpe"),
        "final_model_selection_score": float(final["selection_score"]),
        "final_decision": "balanced_research_portfolio",
        "final_decision_reason": reason,
        "evidence_status": "research-grade with stated limitations",
        "balanced_research_portfolio": final_model,
        "transparent_benchmark": "Equal Weight",
        "defensive_alternative": str(defensive["model_name"]),
        "defensive_selection_reason": (
            "Highest common-sample OOS max drawdown, then CVaR, among positive-return "
            "models that pass constraints and leakage evidence."
        ),
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
        "institutional_live_trading_status": "blocked",
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
            "leakage_gate_pass": frame["leakage_gate_pass"],
            "leakage_evidence_status": frame["leakage_evidence_status"],
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
            "random_benchmark_provenance_status": frame[
                "random_benchmark_provenance_status"
            ],
            "random_benchmark_protocol_hash": frame["random_benchmark_protocol_hash"],
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
            "robustness_evidence_status": frame["robustness_evidence_status"],
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
    robustness_assessment: Mapping[str, object],
    random_assessment: Mapping[str, object],
    leakage_assessment: Mapping[str, object],
) -> dict[str, object]:
    league_row = league.loc[league["model_name"].astype(str).eq(model)]
    league_row = league_row.iloc[0] if not league_row.empty else pd.Series(dtype=object)
    walk = walk_map.get(model, pd.Series(dtype=object))
    risk = risk_map.get(model, pd.Series(dtype=object))
    random_row = random_map.get(model, pd.Series(dtype=object))

    status = str(league_row.get("actual_status", "blocked_by_implementation"))
    constraint_pass = _bool(league_row.get("constraints_pass", False))
    wf_return = _coalesce_float(
        walk.get("oos_annualized_return"),
        walk.get("avg_annualized_return"),
    )
    wf_vol = _coalesce_float(
        walk.get("oos_volatility"),
        walk.get("avg_volatility"),
    )
    wf_sharpe = _coalesce_float(
        walk.get("oos_sharpe"),
        walk.get("avg_sharpe"),
    )
    wf_sortino = _coalesce_float(
        walk.get("oos_sortino"),
        walk.get("avg_sortino"),
    )
    wf_drawdown = _coalesce_float(
        walk.get("oos_max_drawdown"),
        walk.get("avg_max_drawdown"),
    )
    wf_cvar = _coalesce_float(
        walk.get("oos_cvar_95"),
        walk.get("avg_cvar_95"),
    )
    wf_supported = bool(
        not walk.empty
        and all(
            np.isfinite(value)
            for value in [
                wf_return,
                wf_vol,
                wf_sharpe,
                wf_sortino,
                wf_drawdown,
                wf_cvar,
            ]
        )
    )
    leakage_ok = bool(leakage_assessment["promotion_gate_pass"])
    eligible = bool(
        status in ELIGIBLE_FINAL_STATUSES
        and constraint_pass
        and wf_supported
        and leakage_ok
        and model != "Random Portfolios"
    )
    model_turnover = _coalesce_float(
        walk.get("avg_turnover"),
        turnover_map.get(model),
        league_row.get("turnover"),
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
    turnover_ok = bool(
        np.isfinite(model_turnover) and model_turnover <= float(max_turnover) + 1e-12
    )
    random_benchmark_scope = str(random_assessment["benchmark_scope"])
    random_scope_valid = bool(random_assessment["promotion_gate_pass"])
    random_ok = bool(
        random_scope_valid
        and random_sharpe >= float(min_random_sharpe_percentile) - 1e-12
    )
    robustness_status = str(robustness_assessment["robustness_status"])
    robust_ok = bool(robustness_assessment["promotion_gate_pass"])
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
        walk_forward_supported=wf_supported,
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
        random_benchmark_provenance_status=str(random_assessment["provenance_status"]),
        leakage_ok=leakage_ok,
        leakage_evidence_status=str(leakage_assessment["evidence_status"]),
    )
    return {
        "model_name": model,
        "model_status": status,
        "eligible_final_model": eligible,
        "constraint_pass": constraint_pass,
        "walk_forward_supported": wf_supported,
        "leakage_gate_pass": leakage_ok,
        "leakage_evidence_status": str(leakage_assessment["evidence_status"]),
        "leakage_run_id": str(leakage_assessment["run_id"]),
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
        "random_benchmark_provenance_status": str(
            random_assessment["provenance_status"]
        ),
        "random_benchmark_protocol_hash": str(random_assessment["protocol_hash"]),
        "random_benchmark_run_id": str(random_assessment["run_id"]),
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
        "robustness_evidence_status": str(robustness_assessment["evidence_status"]),
        "robustness_run_id": str(robustness_assessment["run_id"]),
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
    walk_forward_supported: bool,
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
    random_benchmark_provenance_status: str,
    leakage_ok: bool,
    leakage_evidence_status: str,
) -> str:
    if not walk_forward_supported:
        return (
            "comparable walk-forward OOS net evidence is missing or incomplete; "
            "full-sample league metrics cannot substitute for OOS model selection"
        )
    if not leakage_ok:
        return (
            "walk-forward leakage evidence failed closed "
            f"(status={leakage_evidence_status})"
        )
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
        if (
            str(random_benchmark_scope) != "walk_forward_oos_net"
            or str(random_benchmark_provenance_status)
            != VERIFIED_RANDOM_BENCHMARK_STATUS
        ):
            reasons.append(
                "random benchmark provenance does not prove same-protocol "
                "walk-forward OOS net evidence"
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


def assess_leakage_evidence(
    evidence: pd.DataFrame | None,
    *,
    expected_run_identity: Mapping[str, object] | None,
) -> dict[str, object]:
    """Fail closed unless every current-run chronological leakage check passes."""
    frame = evidence.copy() if evidence is not None else pd.DataFrame()
    required_columns = {
        "fold",
        "check",
        "passed",
        "audit_status",
        "evidence_scope",
        *RUN_IDENTITY_FIELDS,
    }
    required_checks = {
        "train_end_before_test_start",
        "scores_as_of_not_after_train_end",
        "selected_tickers_available_in_train",
        "scores_recomputed_inside_fold",
    }
    if frame.empty:
        return {
            "evidence_status": "missing",
            "promotion_gate_pass": False,
            "run_id": "missing",
        }
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        return {
            "evidence_status": "schema_incomplete",
            "promotion_gate_pass": False,
            "run_id": "missing",
        }

    identity_ok = bool(expected_run_identity)
    for field in RUN_IDENTITY_FIELDS:
        observed = set(frame[field].dropna().astype(str).str.strip())
        expected = str((expected_run_identity or {}).get(field, "")).strip()
        identity_ok = bool(identity_ok and expected and observed == {expected})
    if not identity_ok:
        return {
            "evidence_status": "stale_or_mismatched_run_identity",
            "promotion_gate_pass": False,
            "run_id": _single_text_value(frame["run_id"]),
        }

    duplicate_checks = bool(frame.duplicated(["fold", "check"]).any())
    fold_checks_complete = bool(
        not duplicate_checks
        and all(
            required_checks.issubset(set(group["check"].astype(str)))
            for _, group in frame.groupby("fold", sort=False)
        )
    )
    checks_pass = bool(frame["passed"].map(_bool).all())
    audit_status_pass = bool(
        frame["audit_status"]
        .astype(str)
        .str.startswith("passed_with_current_universe_survivorship_limitation")
        .all()
    )
    scope_valid = bool(
        frame["evidence_scope"]
        .astype(str)
        .eq("current_universe_not_point_in_time")
        .all()
    )
    gate_pass = bool(
        fold_checks_complete and checks_pass and audit_status_pass and scope_valid
    )
    if gate_pass:
        status = "verified_current_no_lookahead_with_survivorship_limitation"
    elif duplicate_checks:
        status = "duplicate_fold_checks"
    elif not fold_checks_complete:
        status = "incomplete_fold_check_set"
    elif not checks_pass:
        status = "failed_leakage_checks"
    elif not audit_status_pass or not scope_valid:
        status = "unrecognized_leakage_scope"
    else:
        status = "failed_or_unrecognized"
    return {
        "evidence_status": status,
        "promotion_gate_pass": gate_pass,
        "run_id": _single_text_value(frame["run_id"]),
    }


def assess_robustness_evidence(
    evidence: Mapping[str, object] | None,
    *,
    expected_run_identity: Mapping[str, object] | None,
) -> dict[str, object]:
    """Fail closed unless nested OOS robustness is current and promotion-grade."""
    payload = dict(evidence or {})
    status = str(payload.get("robustness_status", "missing"))
    method = str(payload.get("robustness_method", "missing"))
    identity_ok, identity_status = _evidence_identity_matches(
        payload,
        expected_run_identity,
    )
    promotion_eligible = _bool(payload.get("promotion_eligible", False))
    promotion_grade = bool(
        status in PROMOTION_GRADE_ROBUSTNESS_STATUSES
        and method in PROMOTION_GRADE_ROBUSTNESS_METHODS
        and promotion_eligible
    )
    gate_pass = bool(promotion_grade and identity_ok)
    if gate_pass:
        evidence_status = "verified_current_promotion_grade"
    elif not payload:
        evidence_status = "missing"
    elif not identity_ok:
        evidence_status = identity_status
    elif "diagnostic" in status or not promotion_eligible:
        evidence_status = "diagnostic_not_promotion_grade"
    elif any(token in status for token in ("fragile", "unstable", "failed")):
        evidence_status = "fragile_or_failed"
    else:
        evidence_status = "unrecognized_not_promotion_grade"
    return {
        "robustness_status": status,
        "robustness_method": method,
        "evidence_status": evidence_status,
        "promotion_gate_pass": gate_pass,
        "run_id": str(payload.get("run_id", "missing")),
    }


def assess_random_benchmark_evidence(
    random_distribution: pd.DataFrame | None,
    provenance: Mapping[str, object] | None,
    *,
    expected_run_identity: Mapping[str, object] | None,
    expected_protocol: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Verify that random-percentile evidence carries its actual OOS protocol."""
    payload = dict(provenance or {})
    frame = (
        random_distribution.copy()
        if random_distribution is not None
        else pd.DataFrame()
    )
    identity_ok, identity_status = _evidence_identity_matches(
        payload,
        expected_run_identity,
    )
    scope = str(payload.get("benchmark_scope", "missing"))
    provenance_status = str(payload.get("provenance_status", "missing"))
    protocol_hash = str(payload.get("protocol_hash", "missing"))
    required_payload = {
        "fold_schedule_hash",
        "selected_universe_by_fold_hash",
        "model_oos_dates_hash",
        "random_oos_dates_hash",
        "constraint_policy",
        "train_window_days",
        "test_window_days",
        "step_days",
        "max_weight",
        "transaction_cost_bps",
        "random_portfolio_count",
    }
    payload_complete = required_payload.issubset(payload)
    date_sets_match = bool(
        payload.get("oos_dates_match", False)
        and payload.get("model_oos_dates_hash") == payload.get("random_oos_dates_hash")
    )
    row_columns = {
        "benchmark_scope",
        "benchmark_provenance_status",
        "protocol_hash",
        "fold_schedule_hash",
        "selected_universe_by_fold_hash",
        "model_oos_dates_hash",
        "random_oos_dates_hash",
        "transaction_cost_bps",
        "max_weight",
        *RUN_IDENTITY_FIELDS,
    }
    rows_match = bool(
        not frame.empty
        and row_columns.issubset(frame.columns)
        and frame["benchmark_scope"].astype(str).eq(scope).all()
        and frame["benchmark_provenance_status"].astype(str).eq(provenance_status).all()
        and frame["protocol_hash"].astype(str).eq(protocol_hash).all()
        and all(
            _series_matches_protocol_value(frame[field], payload.get(field))
            for field in [
                "fold_schedule_hash",
                "selected_universe_by_fold_hash",
                "model_oos_dates_hash",
                "random_oos_dates_hash",
                "transaction_cost_bps",
                "max_weight",
            ]
        )
        and all(
            frame[field].astype(str).eq(str(payload.get(field, "missing"))).all()
            for field in RUN_IDENTITY_FIELDS
        )
    )
    configured_protocol_matches = all(
        _protocol_values_equal(payload.get(field), expected)
        for field, expected in dict(expected_protocol or {}).items()
    )
    gate_pass = bool(
        scope == "walk_forward_oos_net"
        and provenance_status == VERIFIED_RANDOM_BENCHMARK_STATUS
        and protocol_hash not in {"", "missing", "nan"}
        and payload_complete
        and date_sets_match
        and rows_match
        and identity_ok
        and configured_protocol_matches
    )
    if gate_pass:
        assessment_status = VERIFIED_RANDOM_BENCHMARK_STATUS
    elif not payload:
        assessment_status = "missing"
    elif not identity_ok:
        assessment_status = identity_status
    elif not rows_match:
        assessment_status = "artifact_rows_do_not_match_provenance"
    elif not configured_protocol_matches:
        assessment_status = "configured_protocol_mismatch"
    elif not date_sets_match:
        assessment_status = "oos_dates_not_proven_equal"
    elif not payload_complete:
        assessment_status = "protocol_fields_missing"
    else:
        assessment_status = "unverified_protocol"
    return {
        "benchmark_scope": scope,
        "provenance_status": assessment_status,
        "protocol_hash": protocol_hash,
        "promotion_gate_pass": gate_pass,
        "run_id": str(payload.get("run_id", "missing")),
    }


def _series_matches_protocol_value(
    series: pd.Series,
    expected: object,
) -> bool:
    return bool(
        not series.empty
        and series.map(lambda value: _protocol_values_equal(value, expected)).all()
    )


def _protocol_values_equal(left: object, right: object) -> bool:
    try:
        left_number = float(str(left))
        right_number = float(str(right))
    except (TypeError, ValueError):
        return str(left) == str(right)
    if not np.isfinite(left_number) or not np.isfinite(right_number):
        return False
    return bool(np.isclose(left_number, right_number, atol=1e-12, rtol=0.0))


def _evidence_identity_matches(
    evidence: Mapping[str, object],
    expected: Mapping[str, object] | None,
) -> tuple[bool, str]:
    if not evidence:
        return False, "missing"
    if not expected:
        return False, "expected_run_identity_missing"
    missing = [
        field
        for field in RUN_IDENTITY_FIELDS
        if str(evidence.get(field, "")).strip().lower() in {"", "missing", "nan"}
    ]
    if missing:
        return False, "evidence_identity_incomplete"
    mismatched = [
        field
        for field in RUN_IDENTITY_FIELDS
        if str(evidence.get(field)) != str(expected.get(field))
    ]
    if mismatched:
        return False, "stale_or_mismatched_run_identity"
    return True, "current_run_identity"


def _single_text_value(series: pd.Series) -> str:
    values = series.dropna().astype(str).str.strip()
    unique = values.loc[values.ne("")].drop_duplicates()
    return str(unique.iloc[0]) if len(unique) == 1 else "missing_or_mixed"


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
    values = (
        grouped.groupby(grouped["model_name"].astype(str))["turnover"].mean().to_dict()
    )
    return {str(model): _float(value) for model, value in values.items()}


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
    return float("nan")


def _float(value: object) -> float:
    try:
        if value is None or value is pd.NA or value is pd.NaT:
            return float("nan")
        if isinstance(value, (int, float, np.integer, np.floating)):
            return float(value)
        return float(str(value))
    except (TypeError, ValueError):
        return float("nan")


def _none_if_nan(value: object) -> float | None:
    converted = _float(value)
    return None if not np.isfinite(converted) else converted


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}
