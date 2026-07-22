import pandas as pd

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
)


def _league() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "effective_holdings": 4,
                "concentration_warning": "none",
                "cagr": 0.08,
                "annualized_return": 0.08,
                "volatility": 0.15,
                "sharpe": 0.53,
                "sortino": 0.70,
                "max_drawdown": -0.12,
                "cvar_95": -0.015,
                "turnover": 0.0,
            },
            {
                "model_name": "Risky Active",
                "actual_status": "actually_run",
                "constraints_pass": True,
                "effective_holdings": 3,
                "concentration_warning": "none",
                "cagr": 0.20,
                "annualized_return": 0.20,
                "volatility": 0.45,
                "sharpe": 0.44,
                "sortino": 0.50,
                "max_drawdown": -0.35,
                "cvar_95": -0.050,
                "turnover": 1.8,
            },
            {
                "model_name": "Diagnostic Forecast",
                "actual_status": "diagnostic_only",
                "constraints_pass": True,
                "effective_holdings": 3,
                "concentration_warning": "none",
                "cagr": 0.50,
                "annualized_return": 0.50,
                "volatility": 0.20,
                "sharpe": 2.50,
                "sortino": 3.00,
                "max_drawdown": -0.10,
                "cvar_95": -0.010,
                "turnover": 0.0,
            },
            {
                "model_name": "Random Portfolios",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "effective_holdings": 4,
                "concentration_warning": "benchmark_distribution",
                "cagr": 0.30,
                "annualized_return": 0.30,
                "volatility": 0.10,
                "sharpe": 3.00,
                "sortino": 3.50,
                "max_drawdown": -0.05,
                "cvar_95": -0.010,
                "turnover": 0.0,
            },
        ]
    )


def _walk_forward() -> pd.DataFrame:
    league = _league()
    return pd.DataFrame(
        {
            "model_name": league["model_name"],
            "oos_annualized_return": league["annualized_return"],
            "oos_volatility": league["volatility"],
            "oos_sharpe": league["sharpe"],
            "oos_sortino": league["sortino"],
            "oos_max_drawdown": league["max_drawdown"],
            "oos_cvar_95": league["cvar_95"],
            "avg_turnover": league["turnover"],
        }
    )


def _leakage_evidence() -> dict[str, object]:
    identity = {
        "run_id": "unit-run",
        "config_hash": "config-unit",
        "input_fingerprint": "input-unit",
        "universe_snapshot_id": "universe-unit",
        "data_snapshot_id": "data-unit",
    }
    audit = pd.DataFrame(
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
        "walk_forward_leakage_audit": audit,
        "expected_run_identity": identity,
    }


def test_final_model_cannot_be_blocked_or_diagnostic_only():
    report = build_model_selection_report(
        _league(), _walk_forward(), **_leakage_evidence()
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] != "Diagnostic Forecast"
    diagnostic = report.loc[report["model_name"].eq("Diagnostic Forecast")].iloc[0]
    assert not bool(diagnostic["eligible_final_model"])
    assert "diagnostic_only" in diagnostic["rejection_reason"]
    random_row = report.loc[report["model_name"].eq("Random Portfolios")].iloc[0]
    assert not bool(random_row["eligible_final_model"])
    assert "benchmark distribution" in random_row["rejection_reason"]


def test_equal_weight_wins_when_active_fails_risk_and_cost_gates():
    report = build_model_selection_report(
        _league(), _walk_forward(), **_leakage_evidence()
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    assert (
        "Equal Weight remains the defensible benchmark"
        in decision["final_decision_reason"]
    )


def test_selection_penalizes_drawdown_and_turnover():
    report = build_model_selection_report(
        _league(), _walk_forward(), **_leakage_evidence()
    )
    equal_weight_score = float(
        report.loc[report["model_name"].eq("Equal Weight"), "selection_score"].iloc[0]
    )
    risky_score = float(
        report.loc[report["model_name"].eq("Risky Active"), "selection_score"].iloc[0]
    )

    assert risky_score < equal_weight_score
    risky = report.loc[report["model_name"].eq("Risky Active")].iloc[0]
    assert "drawdown" in risky["rejection_reason"]
    assert "walk-forward Sharpe improvement" in risky["rejection_reason"]


def test_model_decision_json_schema_fields_are_present():
    decision = build_final_model_decision(
        build_model_selection_report(_league(), _walk_forward(), **_leakage_evidence())
    )

    assert {
        "final_selected_model",
        "final_model_selection_method",
        "final_model_selection_score",
        "final_decision",
        "final_decision_reason",
        "equal_weight_comparison",
        "random_portfolio_percentile",
        "publish_readiness_status",
    }.issubset(decision)


def test_missing_walk_forward_evidence_cannot_fall_back_to_full_sample_league():
    report = build_model_selection_report(_league(), **_leakage_evidence())
    decision = build_final_model_decision(report)

    assert not report["walk_forward_supported"].astype(bool).any()
    assert not report["eligible_final_model"].astype(bool).any()
    assert report["walk_forward_sharpe"].isna().all()
    assert decision["final_selected_model"] == "not_available"
    assert "No eligible Equal Weight" in decision["final_decision_reason"]


def test_missing_failed_and_stale_leakage_evidence_fail_closed():
    identity = _leakage_evidence()["expected_run_identity"]

    missing = build_model_selection_report(
        _league(),
        _walk_forward(),
        expected_run_identity=identity,
    )
    assert not missing["eligible_final_model"].astype(bool).any()
    assert set(missing["leakage_evidence_status"]) == {"missing"}

    failed_evidence = _leakage_evidence()
    failed_audit = failed_evidence["walk_forward_leakage_audit"].copy()
    failed_audit.loc[0, "passed"] = False
    failed = build_model_selection_report(
        _league(),
        _walk_forward(),
        walk_forward_leakage_audit=failed_audit,
        expected_run_identity=identity,
    )
    assert not failed["eligible_final_model"].astype(bool).any()
    assert set(failed["leakage_evidence_status"]) == {"failed_leakage_checks"}

    stale_evidence = _leakage_evidence()
    stale_audit = stale_evidence["walk_forward_leakage_audit"].copy()
    stale_audit["run_id"] = "stale-run"
    stale = build_model_selection_report(
        _league(),
        _walk_forward(),
        walk_forward_leakage_audit=stale_audit,
        expected_run_identity=identity,
    )
    assert not stale["eligible_final_model"].astype(bool).any()
    assert set(stale["leakage_evidence_status"]) == {"stale_or_mismatched_run_identity"}
