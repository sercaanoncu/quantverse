import pandas as pd

from project.research.global_model_selection import (
    MODEL_SELECTION_DIAGNOSTIC_COLUMNS,
    build_final_model_decision,
    build_model_selection_diagnostics,
    build_model_selection_report,
)


def _league(active_status: str = "actually_run") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "annualized_return": 0.12,
                "volatility": 0.20,
                "sharpe": 0.60,
                "sortino": 0.80,
                "max_drawdown": -0.12,
                "cvar_95": -0.020,
                "turnover": 0.2,
            },
            {
                "model_name": "Risk Managed Active",
                "actual_status": active_status,
                "constraints_pass": True,
                "annualized_return": 0.11,
                "volatility": 0.12,
                "sharpe": 0.92,
                "sortino": 1.20,
                "max_drawdown": -0.09,
                "cvar_95": -0.014,
                "turnover": 0.3,
            },
        ]
    )


def _walk(active_turnover: float = 0.3, active_sharpe: float = 0.95) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "avg_annualized_return": 0.12,
                "avg_volatility": 0.20,
                "avg_sharpe": 0.60,
                "avg_sortino": 0.80,
                "avg_max_drawdown": -0.12,
                "avg_cvar_95": -0.020,
                "avg_turnover": 0.2,
                "uncertainty_status": "benchmark_self_comparison_not_applicable",
                "uncertainty_method": "paired_circular_block_bootstrap",
                "paired_observations": 252,
                "sharpe_diff_ci_lower": float("nan"),
                "sharpe_diff_ci_upper": float("nan"),
                "probability_sharpe_improvement": float("nan"),
            },
            {
                "model_name": "Risk Managed Active",
                "avg_annualized_return": 0.11,
                "avg_volatility": 0.12,
                "avg_sharpe": active_sharpe,
                "avg_sortino": 1.30,
                "avg_max_drawdown": -0.09,
                "avg_cvar_95": -0.014,
                "avg_turnover": active_turnover,
                "uncertainty_status": "completed",
                "uncertainty_method": "paired_circular_block_bootstrap",
                "paired_observations": 252,
                "sharpe_diff_ci_lower": 0.05,
                "sharpe_diff_ci_upper": 0.60,
                "probability_sharpe_improvement": 0.97,
            },
        ]
    )


def _random() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "sharpe_percentile": 0.55,
                "cvar_percentile": 0.50,
            },
            {
                "model_name": "Risk Managed Active",
                "sharpe_percentile": 0.80,
                "cvar_percentile": 0.75,
            },
        ]
    )


def test_active_model_can_beat_equal_weight_on_risk_adjusted_evidence():
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Risk Managed Active"
    assert (
        decision["equal_weight_comparison"]["comparison_status"]
        == "active_model_vs_equal_weight"
    )
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["beats_equal_weight_return_after_costs"])
    assert bool(active["beats_equal_weight_sharpe"])
    assert bool(active["drawdown_not_materially_worse_than_equal_weight"])
    assert bool(active["cvar_not_materially_worse_than_equal_weight"])


def test_equal_weight_wins_when_active_fails_turnover_gate():
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(active_turnover=3.0),
        random_percentiles=_random(),
        max_turnover=2.0,
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert "turnover exceeds" in active["promotion_gate_failed_reasons"]


def test_configuration_only_sensitivity_cannot_pass_robustness_gate():
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        robustness_status="diagnostic_configuration_stability_only",
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["robustness_gate_pass"])
    assert (
        "robustness evidence is missing, diagnostic, or fragile"
        in active["promotion_gate_failed_reasons"]
    )


def test_full_sample_random_distribution_cannot_pass_oos_random_gate():
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        random_benchmark_scope="full_sample_static_weights_diagnostic",
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["random_sharpe_gate_pass"])
    assert (
        "random benchmark is not same-protocol walk-forward OOS net evidence"
        in active["promotion_gate_failed_reasons"]
    )


def test_sharpe_point_estimate_cannot_pass_when_block_bootstrap_crosses_zero():
    walk = _walk()
    walk.loc[walk["model_name"].eq("Risk Managed Active"), "sharpe_diff_ci_lower"] = (
        -0.05
    )
    report = build_model_selection_report(
        _league(),
        walk_forward=walk,
        random_percentiles=_random(),
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["uncertainty_gate_pass"])
    assert "uncertainty gate failed" in active["promotion_gate_failed_reasons"]


def test_diagnostic_model_cannot_be_final_selected():
    report = build_model_selection_report(
        _league(active_status="diagnostic_only"),
        walk_forward=_walk(),
        random_percentiles=_random(),
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["eligible_final_model"])
    assert "diagnostic_only" in active["promotion_gate_failed_reasons"]


def test_empty_or_missing_benchmark_evidence_cannot_select_a_model():
    empty_decision = build_final_model_decision(pd.DataFrame())
    assert empty_decision["final_selected_model"] == "not_available"
    assert empty_decision["publish_readiness_status"] == "not ready"

    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
    )
    without_benchmark = report.loc[~report["model_name"].eq("Equal Weight")]
    decision = build_final_model_decision(without_benchmark)

    assert decision["final_selected_model"] == "not_available"
    assert "benchmark evidence" in decision["final_decision_reason"]


def test_metric_review_warning_blocks_active_model_selection():
    risk = pd.DataFrame(
        [
            {"model_name": "Equal Weight", "extreme_metric_warning": "none"},
            {
                "model_name": "Risk Managed Active",
                "extreme_metric_warning": (
                    "high_annualized_return_short_sample_review_required"
                ),
            },
        ]
    )
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        risk_report=risk,
        random_percentiles=_random(),
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert "metric warning" in active["promotion_gate_failed_reasons"]


def test_model_selection_diagnostics_schema_is_stable():
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
    )
    diagnostics = build_model_selection_diagnostics(report)

    assert list(diagnostics.columns) == MODEL_SELECTION_DIAGNOSTIC_COLUMNS
    assert "book_grounded_rank" in diagnostics
