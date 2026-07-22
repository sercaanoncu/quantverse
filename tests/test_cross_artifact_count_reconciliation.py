import json
from pathlib import Path

import pandas as pd

from project.research.security_history_reconciliation import (
    build_cross_artifact_count_reconciliation,
)

CORE_ARTIFACTS = [
    "data/processed/global_security_identity_audit.csv",
    "data/processed/global_feature_history_eligibility.csv",
    "data/processed/global_stock_scores.csv",
    "data/processed/global_stock_return_forecasts.csv",
    "data/processed/global_portfolio_league_weights.csv",
    "data/processed/global_portfolio_risk_report.csv",
    "data/processed/global_final_model_decision.json",
    "data/processed/global_robustness_sensitivity.csv",
    "data/processed/global_exposure_metadata_quality.csv",
    "data/processed/global_walk_forward_window_summary.csv",
]


def _fixture(
    processed: Path,
    *,
    forecast_eligible_count: int,
    forecast_output_count: int = 25,
) -> str:
    processed.mkdir(parents=True)
    run_id = "qv2-2026-07-16-unit"
    metadata = {
        "run_id": run_id,
        "data_as_of_date": "2026-07-16",
        "generated_at": "2026-07-17T00:00:00+00:00",
        "universe_snapshot_id": "universe-unit",
    }
    (processed / "quantverse_v2_run_manifest.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    tickers = [f"S{index:02d}" for index in range(26)]
    pd.DataFrame(
        {
            "ticker": tickers,
            "selection_flag": [True] * 26,
            "standard_composite_score_eligible": [True] * 26,
            **{key: [value] * 26 for key, value in metadata.items()},
        }
    ).to_csv(processed / "global_stock_scores.csv", index=False)
    pd.DataFrame({"ticker": tickers}).to_csv(
        processed / "global_selected_stocks_report_view.csv", index=False
    )
    pd.DataFrame(
        {
            "ticker": tickers,
            "standard_composite_score_eligible": [True] * 26,
            "eligibility_status": ["eligible"] * 26,
            **{key: [value] * 26 for key, value in metadata.items()},
        }
    ).to_csv(processed / "global_feature_history_eligibility.csv", index=False)
    pd.DataFrame(
        {
            "ticker": tickers,
            "forecast_eligible": [
                index < forecast_eligible_count for index in range(26)
            ],
            **{key: [value] * 26 for key, value in metadata.items()},
        }
    ).to_csv(processed / "global_security_identity_audit.csv", index=False)
    pd.DataFrame(
        {
            "ticker": tickers[:forecast_output_count],
            "horizon": ["12M"] * forecast_output_count,
            **{key: [value] * forecast_output_count for key, value in metadata.items()},
        }
    ).to_csv(processed / "global_stock_return_forecasts.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["HRP"] * 26,
            "ticker": tickers,
            "weight": [1.0 / 25.0] * 25 + [0.0],
            **{key: [value] * 26 for key, value in metadata.items()},
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    pd.DataFrame(
        {
            "selected_count": [20],
            **{key: [value] for key, value in metadata.items()},
        }
    ).to_csv(processed / "global_walk_forward_window_summary.csv", index=False)
    (processed / "global_final_model_decision.json").write_text(
        json.dumps({"final_selected_model": "HRP", **metadata}),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {"artifact": artifact, **metadata, "file_size": 1, "sha256": "unit"}
            for artifact in CORE_ARTIFACTS
        ]
    ).to_csv(processed / "quantverse_v2_artifact_run_registry.csv", index=False)
    return run_id


def _row(frame: pd.DataFrame, artifact: str) -> pd.Series:
    return frame.loc[frame["artifact"].eq(artifact)].iloc[0]


def test_selected_26_and_final_25_pass_when_zero_weight_explains_difference(
    tmp_path,
):
    processed = tmp_path / "data" / "processed"
    _fixture(processed, forecast_eligible_count=25)

    result = build_cross_artifact_count_reconciliation(processed)

    assert _row(result, "stocks_selection_flag_true")["status"] == "passed"
    assert int(_row(result, "final_model_holding_count")["count"]) == 25
    assert _row(result, "final_model_holding_count")["status"] == "passed"
    assert result["status"].eq("passed").all()


def test_selected_26_and_forecast_25_fails_without_explicit_ineligibility(
    tmp_path,
):
    processed = tmp_path / "data" / "processed"
    _fixture(processed, forecast_eligible_count=26)

    result = build_cross_artifact_count_reconciliation(processed)

    assert int(_row(result, "forecast_input_count")["count"]) == 26
    assert int(_row(result, "forecast_output_ticker_count")["count"]) == 25
    assert _row(result, "forecast_output_ticker_count")["status"] == "failed"


def test_selected_26_and_forecast_25_pass_with_explicit_ineligibility(tmp_path):
    processed = tmp_path / "data" / "processed"
    _fixture(processed, forecast_eligible_count=25)

    result = build_cross_artifact_count_reconciliation(processed)

    assert int(_row(result, "forecast_input_count")["count"]) == 25
    assert _row(result, "forecast_output_ticker_count")["status"] == "passed"


def test_run_id_mismatch_fails_reconciliation(tmp_path):
    processed = tmp_path / "data" / "processed"
    _fixture(processed, forecast_eligible_count=25)
    registry_path = processed / "quantverse_v2_artifact_run_registry.csv"
    registry = pd.read_csv(registry_path)
    registry.loc[registry["artifact"].eq(CORE_ARTIFACTS[-1]), "run_id"] = (
        "qv2-other-run"
    )
    registry.to_csv(registry_path, index=False)

    result = build_cross_artifact_count_reconciliation(processed)

    row = _row(result, "core_generated_artifact_run_ids")
    assert row["status"] == "failed"
    assert "qv2-other-run" in row["observed_relationship"]
