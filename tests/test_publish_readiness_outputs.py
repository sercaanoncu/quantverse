from pathlib import Path

import scripts.build_global_exposure_report as exposure_report

ROOT = Path(__file__).resolve().parents[1]


def test_publish_readiness_audit_and_new_scripts_exist():
    for path in [
        "docs/audit/QUANTVERSE_V2_PUBLISH_READINESS_AUDIT.md",
        "scripts/build_global_model_selection_report.py",
        "scripts/run_global_robustness_analysis.py",
        "scripts/build_global_exposure_report.py",
        "scripts/validate_global_forecasts.py",
    ]:
        assert (ROOT / path).exists()


def test_report_and_excel_builders_reference_new_publish_readiness_outputs():
    report = (ROOT / "scripts" / "build_quantverse_v2_research_report.py").read_text(
        encoding="utf-8"
    )
    excel = (ROOT / "scripts" / "build_quantverse_v2_excel_output.py").read_text(
        encoding="utf-8"
    )

    for text in [
        "Robust Model Selection Rationale",
        "Benchmark and Random Portfolio Context",
        "Robustness and Sensitivity",
        "Forecast Validation",
        "Economic Exposure Interpretation",
    ]:
        assert text in report
    for sheet in [
        "MODEL_SELECTION",
        "ROBUSTNESS",
        "RANDOM_DISTRIBUTION",
        "RANDOM_PERCENTILES",
        "EXPOSURE_REGION",
        "EXPOSURE_COUNTRY",
        "EXPOSURE_CURRENCY",
        "EXPOSURE_SECTOR",
        "TOP_HOLDINGS_EXPLANATION",
        "FORECAST_VALIDATION",
        "PUBLISH_READINESS",
    ]:
        assert sheet in excel


def test_claim_guards_prevent_overclaim_language():
    texts = [
        (ROOT / "README.md").read_text(encoding="utf-8").lower(),
        (ROOT / "docs" / "showcase" / "BANK_INTERVIEW_TALK_TRACK.md")
        .read_text(encoding="utf-8")
        .lower(),
        (ROOT / "docs" / "audit" / "QUANTVERSE_V2_PUBLISH_READINESS_AUDIT.md")
        .read_text(encoding="utf-8")
        .lower(),
    ]
    joined = "\n".join(texts)

    assert "not investment advice" in joined
    assert "official exact top-100" in joined
    assert "institutional point-in-time" in joined
    assert "guaranteed outperformance" not in joined
    assert "guaranteed alpha" not in joined


def test_exposure_report_does_not_fabricate_equal_weight(tmp_path, monkeypatch):
    monkeypatch.setattr(exposure_report, "PROCESSED", tmp_path)

    assert exposure_report._final_model() == "not_available"


def test_current_release_docs_do_not_preserve_stale_model_decisions():
    root = Path(__file__).resolve().parents[1]
    visual_audit = (
        root / "docs" / "audit" / "QUANTVERSE_V2_VISUAL_OUTPUT_AUDIT.md"
    ).read_text(encoding="utf-8")
    release_notes = (root / "docs" / "release" / "RELEASE_NOTES_V2.md").read_text(
        encoding="utf-8"
    )

    assert "public-data research model: **Equal Weight**" in visual_audit
    assert "Final public-data research model | Equal Weight" in release_notes
    assert "Final selected model: `Policy Constrained`" not in release_notes
