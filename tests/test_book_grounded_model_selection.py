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


def _identity(run_id: str = "unit-run") -> dict[str, str]:
    return {
        "run_id": run_id,
        "config_hash": "config-unit",
        "input_fingerprint": "input-unit",
        "universe_snapshot_id": "universe-unit",
        "data_snapshot_id": "data-unit",
    }


def _robustness(
    status: str = "promotion_grade_nested_walk_forward_oos",
    *,
    run_id: str = "unit-run",
    promotion_eligible: bool = True,
) -> dict[str, object]:
    return {
        **_identity(run_id),
        "robustness_status": status,
        "robustness_method": "nested_chronological_walk_forward_oos",
        "promotion_eligible": promotion_eligible,
    }


def _random_provenance(
    *,
    scope: str = "walk_forward_oos_net",
    status: str = "verified_same_protocol",
    run_id: str = "unit-run",
) -> dict[str, object]:
    return {
        **_identity(run_id),
        "benchmark_scope": scope,
        "provenance_status": status,
        "protocol_hash": "wf-random-unit",
        "fold_schedule_hash": "frame-folds",
        "selected_universe_by_fold_hash": "frame-universe",
        "model_oos_dates_hash": "dates-unit",
        "random_oos_dates_hash": "dates-unit",
        "oos_dates_match": True,
        "constraint_policy": "long_only_capped_simplex",
        "train_window_days": 252,
        "test_window_days": 21,
        "step_days": 21,
        "max_weight": 0.10,
        "transaction_cost_bps": 10.0,
        "random_portfolio_count": 2,
    }


def _random_distribution(
    provenance: dict[str, object] | None = None,
) -> pd.DataFrame:
    payload = provenance or _random_provenance()
    return pd.DataFrame(
        [
            {
                "portfolio_id": portfolio_id,
                "benchmark_scope": payload["benchmark_scope"],
                "benchmark_provenance_status": payload["provenance_status"],
                "protocol_hash": payload["protocol_hash"],
                **{
                    field: payload[field]
                    for field in [
                        "run_id",
                        "config_hash",
                        "input_fingerprint",
                        "universe_snapshot_id",
                        "data_snapshot_id",
                    ]
                },
            }
            for portfolio_id in range(2)
        ]
    )


def _promotion_evidence() -> dict[str, object]:
    provenance = _random_provenance()
    identity = _identity()
    leakage = pd.DataFrame(
        [
            {
                "fold": 1,
                "check": check,
                "passed": True,
                "audit_status": (
                    "passed_with_current_universe_survivorship_limitation"
                ),
                "evidence_scope": "current_universe_not_point_in_time",
                **identity,
            }
            for check in [
                "train_end_before_test_start",
                "scores_as_of_not_after_train_end",
                "selected_tickers_available_in_train",
                "scores_recomputed_inside_fold",
            ]
        ]
    )
    return {
        "random_distribution": _random_distribution(provenance),
        "robustness_evidence": _robustness(),
        "random_benchmark_provenance": provenance,
        "walk_forward_leakage_audit": leakage,
        "expected_run_identity": identity,
    }


def test_active_model_can_beat_equal_weight_on_risk_adjusted_evidence():
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **_promotion_evidence(),
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
        **_promotion_evidence(),
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert "turnover exceeds" in active["promotion_gate_failed_reasons"]


def test_configuration_only_sensitivity_cannot_pass_robustness_gate():
    evidence = _promotion_evidence()
    evidence["robustness_evidence"] = _robustness(
        "diagnostic_configuration_stability_only",
        promotion_eligible=False,
    )
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **evidence,
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
    evidence = _promotion_evidence()
    provenance = _random_provenance(
        scope="full_sample_static_weights_diagnostic",
        status="diagnostic_full_sample",
    )
    evidence["random_benchmark_provenance"] = provenance
    evidence["random_distribution"] = _random_distribution(provenance)
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **evidence,
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["random_sharpe_gate_pass"])
    assert (
        "random benchmark provenance does not prove same-protocol "
        "walk-forward OOS net evidence" in active["promotion_gate_failed_reasons"]
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
        **_promotion_evidence(),
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
        **_promotion_evidence(),
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
        **_promotion_evidence(),
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
        **_promotion_evidence(),
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
        **_promotion_evidence(),
    )
    diagnostics = build_model_selection_diagnostics(report)

    assert list(diagnostics.columns) == MODEL_SELECTION_DIAGNOSTIC_COLUMNS
    assert "book_grounded_rank" in diagnostics


def test_missing_robustness_fails_closed():
    evidence = _promotion_evidence()
    evidence["robustness_evidence"] = None
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **evidence,
    )

    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["robustness_gate_pass"])
    assert active["robustness_evidence_status"] == "missing"


def test_stale_robustness_fails_closed():
    evidence = _promotion_evidence()
    evidence["robustness_evidence"] = _robustness(run_id="stale-run")
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **evidence,
    )

    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["robustness_gate_pass"])
    assert active["robustness_evidence_status"] == "stale_or_mismatched_run_identity"


def test_mismatched_config_hash_fails_robustness_and_random_gates():
    evidence = _promotion_evidence()
    robustness = _robustness()
    robustness["config_hash"] = "config-from-another-run"
    provenance = _random_provenance()
    provenance["config_hash"] = "config-from-another-run"
    evidence["robustness_evidence"] = robustness
    evidence["random_benchmark_provenance"] = provenance
    evidence["random_distribution"] = _random_distribution(provenance)

    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **evidence,
    )

    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["robustness_gate_pass"])
    assert not bool(active["random_sharpe_gate_pass"])
    assert active["robustness_evidence_status"] == "stale_or_mismatched_run_identity"
    assert active["random_benchmark_provenance_status"] == (
        "stale_or_mismatched_run_identity"
    )


def test_fragile_robustness_fails_closed():
    evidence = _promotion_evidence()
    evidence["robustness_evidence"] = _robustness(
        "fragile_nested_walk_forward_oos",
        promotion_eligible=False,
    )
    report = build_model_selection_report(
        _league(),
        walk_forward=_walk(),
        random_percentiles=_random(),
        **evidence,
    )

    active = report.loc[report["model_name"].eq("Risk Managed Active")].iloc[0]
    assert not bool(active["robustness_gate_pass"])
    assert active["robustness_evidence_status"] in {
        "diagnostic_not_promotion_grade",
        "fragile_or_failed",
    }
