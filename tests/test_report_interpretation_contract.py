from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_report_builder_labels_extreme_return_as_realized_annualized_estimate():
    script = (ROOT / "scripts" / "build_quantverse_v2_research_report.py").read_text(
        encoding="utf-8"
    )

    assert "Annualized realized return estimate" in script
    assert "Return warning" in script
    assert "Leakage audit passed" in script
    assert "not an institutional PIT backtest" in script


def test_excel_builder_contains_required_interpretation_sheets():
    script = (ROOT / "scripts" / "build_quantverse_v2_excel_output.py").read_text(
        encoding="utf-8"
    )

    for sheet in [
        "START_HERE",
        "SELECTED_STOCKS",
        "STOCK_SCORES",
        "RETURN_FORECASTS",
        "MODEL_LEAGUE",
        "FINAL_WEIGHTS",
        "RISK_METRICS",
        "RISK_CONTRIBUTIONS",
        "WALK_FORWARD",
        "BENCHMARK_COMPARISON",
        "RANDOM_PORTFOLIOS",
        "WARNINGS",
        "CLAIM_CONTROL",
        "APPENDIX_FORMULAS",
    ]:
        assert sheet in script


def test_claim_language_guards_cover_public_data_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    showcase = (
        (ROOT / "docs" / "showcase" / "README_GITHUB_SHOWCASE.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "public-data" in readme
    assert "not investment advice" in readme
    assert "official exact top-100" in readme
    assert "point-in-time" in readme
    assert "live trading system" not in showcase
