import json
from pathlib import Path

import pandas as pd
from reportlab.pdfgen import canvas

from project.research.global_visual_analytics import build_visual_analytics_outputs
from scripts.validate_quantverse_v2_artifacts import validate_artifacts


def _write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()


def test_artifact_validator_passes_on_minimal_valid_fixture(tmp_path):
    processed = tmp_path / "data" / "processed"
    output = tmp_path / "output"
    processed.mkdir(parents=True)
    (output / "html").mkdir(parents=True)
    (output / "excel").mkdir(parents=True)
    (output / "pdf").mkdir(parents=True)
    (output / "thesis").mkdir(parents=True)

    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "run_status": "completed",
                "final_selected_model": "Equal Weight",
                "final_model_selection_method": "robust_public_data_evidence_gate",
                "final_model_selection_score": 1.0,
                "final_model_selection_decision": "not promoted",
                "promotion_decision": "not promoted",
                "weight_sum": 1.0,
                "final_selected_holdings": 2,
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_final_model_decision.json").write_text(
        json.dumps(
            {
                "final_selected_model": "Equal Weight",
                "final_model_selection_method": "robust_public_data_evidence_gate",
                "final_model_selection_score": 1.0,
                "final_decision": "not promoted",
                "final_decision_reason": "Fixture.",
                "publish_readiness_status": "research_publish_ready_with_limitations",
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "actual_status": ["benchmark_only"],
            "constraints_pass": [True],
            "cagr": [0.20],
            "annualized_return": [0.18],
            "volatility": [0.02],
            "sharpe": [1.2],
            "sortino": [1.4],
            "max_drawdown": [-0.01],
            "var_95": [-0.001],
            "cvar_95": [-0.0015],
        }
    ).to_csv(processed / "global_portfolio_league.csv", index=False)
    pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=80, freq="B"),
            "A": [0.001] * 80,
            "B": [0.002, -0.001] * 40,
        }
    ).to_csv(processed / "global_security_simple_returns_usd.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "weight": [0.5, 0.5],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "cagr": [0.20],
            "annualized_return": [0.18],
            "annualized_volatility": [0.02],
            "sharpe": [1.2],
            "sortino": [1.4],
            "max_drawdown": [-0.01],
            "var_95": [-0.001],
            "cvar_95": [-0.0015],
            "total_return": [0.05],
        }
    ).to_csv(processed / "global_portfolio_risk_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "avg_cagr": [0.10],
            "avg_annualized_return": [0.09],
            "avg_volatility": [0.03],
            "avg_sharpe": [1.0],
            "avg_sortino": [1.1],
            "avg_max_drawdown": [-0.01],
            "avg_cvar_95": [-0.001],
        }
    ).to_csv(processed / "global_walk_forward_model_comparison.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "risk_contribution_pct": [0.5, 0.5],
        }
    ).to_csv(processed / "global_risk_contribution_report.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "selection_flag": [True, True],
        }
    ).to_csv(processed / "global_stock_scores.csv", index=False)
    for filename in [
        "global_model_selection_report.csv",
        "global_model_selection_diagnostics.csv",
        "global_final_model_decision.csv",
        "global_robustness_sensitivity.csv",
        "global_top_holdings_explanation.csv",
    ]:
        pd.DataFrame({"value": [1]}).to_csv(processed / filename, index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Policy Constrained"],
            "return_percentile": [0.6, 0.4],
            "volatility_percentile": [0.5, 0.7],
            "sharpe_percentile": [0.7, 0.3],
            "max_drawdown_percentile": [0.5, 0.6],
            "cvar_percentile": [0.5, 0.6],
        }
    ).to_csv(processed / "global_random_portfolio_percentile_report.csv", index=False)
    pd.DataFrame(
        {
            "horizon": ["12M"],
            "horizon_days": [252],
            "mean_mae": [0.12],
            "mean_rmse": [0.16],
            "mean_random_walk_mae": [0.14],
            "forecast_validation_status": ["validated_diagnostic"],
            "allocation_signal_status": ["diagnostic_only"],
        }
    ).to_csv(processed / "global_forecast_validation_by_horizon.csv", index=False)
    pd.DataFrame(
        {"portfolio_id": range(40), "sharpe": [idx / 40 for idx in range(40)]}
    ).to_csv(processed / "global_random_portfolio_distribution.csv", index=False)
    for filename in [
        "global_region_exposure.csv",
        "global_country_exposure.csv",
        "global_currency_exposure.csv",
        "global_sector_exposure.csv",
        "global_sleeve_exposure.csv",
    ]:
        pd.DataFrame({"bucket": ["A", "B"], "weight": [0.5, 0.5]}).to_csv(
            processed / filename, index=False
        )
    build_visual_analytics_outputs(processed)

    html = " ".join(
        [
            "Executive Summary",
            "Stock Scoring",
            "Portfolio Model League",
            "Robust Model Selection",
            "Walk-Forward",
            "Exposure",
            "Visual Portfolio Analytics",
            "Equity Curve and Drawdown",
            "Model Risk-Return Map",
            "Forecast Error Versus Random Walk",
            "Random Benchmark Distribution",
            "Exposure and Concentration",
            "Limitations",
        ]
    )
    (output / "html" / "quantverse_v2_research_report.html").write_text(
        html, encoding="utf-8"
    )
    with pd.ExcelWriter(
        output / "excel" / "quantverse_v2_research_output.xlsx",
        engine="xlsxwriter",
    ) as writer:
        for sheet in [
            "PORTFOLIO_DASHBOARD",
            "VISUAL_ANALYTICS_DASHBOARD",
            "START_HERE",
            "EXECUTIVE_SUMMARY",
            "SELECTED_STOCKS",
            "STOCK_SCORES",
            "RETURN_FORECASTS",
            "MODEL_LEAGUE",
            "MODEL_SELECTION",
            "MODEL_SELECTION_DIAGNOSTICS",
            "FINAL_MODEL_DECISION",
            "FINAL_WEIGHTS",
            "RISK_METRICS",
            "RISK_CONTRIBUTIONS",
            "WALK_FORWARD",
            "RANDOM_PERCENTILES",
            "ROBUSTNESS",
            "EXPOSURE_REGION",
            "EXPOSURE_COUNTRY",
            "EXPOSURE_CURRENCY",
            "TOP_HOLDINGS_EXPLANATION",
            "FORECAST_VALIDATION",
            "VISUAL_SUMMARY",
            "VISUAL_EQUITY_CURVE",
            "VISUAL_DRAWDOWN",
            "VISUAL_RISK_RETURN",
            "VISUAL_FORECAST_ERROR",
            "VISUAL_RANDOM_BENCH",
            "VISUAL_EXPOSURE",
            "VISUAL_TOP_HOLDINGS",
            "VISUAL_VALIDATION",
            "WARNINGS",
            "CLAIM_CONTROL",
        ]:
            pd.DataFrame({"value": [1]}).to_excel(writer, sheet_name=sheet, index=False)
    _write_pdf(
        output / "pdf" / "quantverse_v2_research_report.pdf", "Executive Summary"
    )
    _write_pdf(
        output / "thesis" / "quantverse_doctoral_dissertation_full.pdf",
        "QuantVerse dissertation",
    )
    _write_pdf(
        output / "thesis" / "quantverse_doctoral_defense_presentation_full.pdf",
        "QuantVerse defense",
    )

    result = validate_artifacts(tmp_path)

    assert result["overall_status"] == "passed"
    assert result["failed_check_count"] == 0


def test_artifact_validator_fails_on_final_model_mismatch(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "run_status": "completed",
                "final_selected_model": "Risk Parity",
                "final_model_selection_method": "robust_public_data_evidence_gate",
                "final_model_selection_score": 1.0,
                "final_model_selection_decision": "not promoted",
                "promotion_decision": "not promoted",
                "weight_sum": 1.0,
                "final_selected_holdings": 2,
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_final_model_decision.json").write_text(
        json.dumps(
            {
                "final_selected_model": "Equal Weight",
                "final_model_selection_method": "robust_public_data_evidence_gate",
                "final_model_selection_score": 1.0,
                "final_decision": "not promoted",
                "final_decision_reason": "Fixture.",
                "publish_readiness_status": "research_publish_ready_with_limitations",
            }
        ),
        encoding="utf-8",
    )

    result = validate_artifacts(tmp_path)

    assert result["overall_status"] == "failed"
    assert any(
        check["check"] == "summary_matches_final_model_decision" and not check["passed"]
        for check in result["checks"]
    )
