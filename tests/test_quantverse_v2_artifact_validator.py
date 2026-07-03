import json
from pathlib import Path

import pandas as pd
from reportlab.pdfgen import canvas

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
    pd.DataFrame({"model_name": ["Equal Weight"]}).to_csv(
        processed / "global_portfolio_league.csv", index=False
    )
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "weight": [0.5, 0.5],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    for filename in [
        "global_model_selection_report.csv",
        "global_random_portfolio_percentile_report.csv",
        "global_robustness_sensitivity.csv",
        "global_top_holdings_explanation.csv",
        "global_forecast_validation_by_horizon.csv",
    ]:
        pd.DataFrame({"value": [1]}).to_csv(processed / filename, index=False)

    html = " ".join(
        [
            "Executive Summary",
            "Stock Scoring",
            "Portfolio Model League",
            "Robust Model Selection",
            "Walk-Forward",
            "Exposure",
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
            "START_HERE",
            "EXECUTIVE_SUMMARY",
            "SELECTED_STOCKS",
            "STOCK_SCORES",
            "RETURN_FORECASTS",
            "MODEL_LEAGUE",
            "MODEL_SELECTION",
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
