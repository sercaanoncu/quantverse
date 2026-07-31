from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.build_quantverse_portfolio_analysis as report_builder
import scripts.build_quantverse_portfolio_excel as workbook_builder
from scripts.build_quantverse_portfolio_excel import CANONICAL_SHEET_NAMES
from scripts.validate_quantverse_v2_artifacts import _excel_sheet_names


def test_canonical_workbook_has_thirteen_user_sheets_and_two_raw_sheets():
    assert len(CANONICAL_SHEET_NAMES) == 15
    assert len(set(CANONICAL_SHEET_NAMES)) == 15
    assert CANONICAL_SHEET_NAMES[0] == "START_HERE"
    assert CANONICAL_SHEET_NAMES[-2:] == ("RAW_WEIGHTS", "RAW_OOS_RETURNS")


def test_oos_performance_sheet_compounds_to_compact_calendar_year_summary():
    dates = pd.to_datetime(["2024-12-30", "2024-12-31", "2025-01-02"])
    oos = pd.DataFrame(
        [
            {"Date": date, "model_name": model, "return": daily_return}
            for model, returns in {
                "Equal Weight": [0.10, -0.10, 0.05],
                "GMV": [0.02, 0.01, 0.03],
            }.items()
            for date, daily_return in zip(dates, returns, strict=True)
        ]
    )

    summary = workbook_builder._calendar_year_oos_summary(
        oos,
        ["Equal Weight", "Equal Weight", "GMV"],
    )

    assert summary.columns.tolist() == [
        "calendar_year",
        "observations",
        "Equal Weight net_return",
        "GMV net_return",
    ]
    assert summary["observations"].tolist() == [2, 1]
    assert summary.loc[0, "Equal Weight net_return"] == pytest.approx(-0.01)
    assert summary.loc[0, "GMV net_return"] == pytest.approx(0.0302)
    assert len(summary) == 2


def test_oos_performance_sheet_rejects_non_common_model_dates():
    oos = pd.DataFrame(
        {
            "Date": ["2025-01-02", "2025-01-03", "2025-01-02"],
            "model_name": ["Equal Weight", "Equal Weight", "GMV"],
            "return": [0.01, 0.02, 0.01],
        }
    )

    with pytest.raises(RuntimeError, match="identical dates"):
        workbook_builder._calendar_year_oos_summary(oos, ["Equal Weight", "GMV"])


def test_risk_sheet_is_a_compact_common_oos_summary():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    oos = pd.DataFrame(
        [
            {"Date": date, "model_name": model, "return": daily_return}
            for model, returns in {
                "Equal Weight": [0.01, -0.02, 0.03],
                "GMV": [0.005, -0.01, 0.015],
            }.items()
            for date, daily_return in zip(dates, returns, strict=True)
        ]
    )
    comparison = pd.DataFrame(
        {
            "model_name": ["Equal Weight", "GMV"],
            "oos_observations": [3, 3],
            "oos_volatility": [0.20, 0.10],
            "oos_max_drawdown": [-0.02, -0.01],
            "oos_cvar_95": [-0.02, -0.01],
            "risk_free_policy": ["time_aligned_market_proxy"] * 2,
        }
    )

    summary = workbook_builder._oos_risk_summary(oos, comparison)

    assert len(summary) == 2
    assert summary.columns.tolist() == [
        "model_name",
        "oos_observations",
        "oos_volatility",
        "oos_max_drawdown",
        "oos_var_95",
        "oos_cvar_95",
        "worst_daily_return",
        "risk_free_policy",
        "evidence_sample",
    ]
    assert summary.loc[0, "worst_daily_return"] == pytest.approx(-0.02)
    assert summary["evidence_sample"].eq("stitched net OOS; identical dates").all()


def test_report_and_workbook_derive_common_oos_observation_count():
    comparison = pd.DataFrame({"oos_observations": [315, 315, 315]})

    assert report_builder._common_oos_observations(comparison) == 315
    assert workbook_builder._common_oos_observations(comparison) == 315

    inconsistent = pd.DataFrame({"oos_observations": [315, 294]})
    with pytest.raises(RuntimeError, match="one positive common OOS"):
        report_builder._common_oos_observations(inconsistent)
    with pytest.raises(RuntimeError, match="one positive common OOS"):
        workbook_builder._common_oos_observations(inconsistent)


def test_report_and_workbook_reject_stale_source_identity():
    manifest = {
        field: f"current-{field}" for field in report_builder.OUTPUT_IDENTITY_FIELDS
    }
    current = pd.DataFrame(
        {field: [manifest[field]] for field in report_builder.OUTPUT_IDENTITY_FIELDS}
    )
    stale = current.copy()
    stale["run_id"] = "stale-run"

    report_builder._validate_source_identity(manifest, {"current": current})
    workbook_builder._validate_source_identity(manifest, {"current": current})
    with pytest.raises(RuntimeError, match="one run identity"):
        report_builder._validate_source_identity(manifest, {"stale": stale})
    with pytest.raises(RuntimeError, match="one run identity"):
        workbook_builder._validate_source_identity(manifest, {"stale": stale})


@pytest.mark.parametrize(
    "invalid_values",
    [
        [315, None],
        [315, "not-a-number"],
        [315, 0],
        [315, 315.5],
    ],
)
def test_report_and_workbook_reject_invalid_oos_counts(invalid_values):
    comparison = pd.DataFrame({"oos_observations": invalid_values})

    with pytest.raises(RuntimeError, match="positive integer OOS count"):
        report_builder._common_oos_observations(comparison)
    with pytest.raises(RuntimeError, match="positive integer OOS count"):
        workbook_builder._common_oos_observations(comparison)


def test_pdf_font_registration_has_portable_builtin_fallback(monkeypatch):
    def fail_font_discovery(*args, **kwargs):
        del args, kwargs
        raise OSError("font discovery unavailable")

    monkeypatch.setattr(report_builder.font_manager, "findfont", fail_font_discovery)
    report_builder._register_fonts()

    assert report_builder.PDF_FONT == "Helvetica"
    assert report_builder.PDF_FONT_BOLD == "Helvetica-Bold"


def test_portable_workbook_writer_needs_no_codex_runtime(tmp_path: Path):
    sheets = []
    for name in CANONICAL_SHEET_NAMES:
        rows = [["field", "value"], ["status", "ok"]]
        if name == "MODEL_COMPARISON":
            rows = [
                ["model_name", "oos_annualized_return", "oos_volatility"],
                ["Equal Weight", 0.10, 0.20],
                ["GMV", 0.08, 0.15],
            ]
        elif name == "EXPOSURE":
            rows = [
                ["exposure_type", "bucket", "weight"],
                ["sector", "Industrials", 1.0],
            ]
        elif name == "TURNOVER_COSTS":
            rows = [
                ["model_name", "transaction_cost_bps", "sharpe"],
                ["Equal Weight", 5, 0.50],
                ["Equal Weight", 10, 0.49],
                ["Equal Weight", 25, 0.47],
                ["GMV", 5, 0.45],
                ["GMV", 10, 0.44],
                ["GMV", 25, 0.42],
            ]
        sheets.append({"name": name, "rows": rows, "explanation": "Portable test"})

    output = tmp_path / "portfolio.xlsx"
    workbook_builder._write_workbook({"sheets": sheets}, output)

    assert output.exists()
    assert _excel_sheet_names(output) == list(CANONICAL_SHEET_NAMES)


def test_html_report_publishes_three_explicit_roles_without_not_promoted_headline(
    tmp_path: Path,
    monkeypatch,
):
    current = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "issuer_name": ["Issuer A"],
            "weight": [1.0],
            "sector": ["Industrials"],
            "issuer_country": ["United States"],
            "risk_contribution_pct": [1.0],
        }
    )
    comparison = pd.DataFrame(
        {
            "model_name": ["Equal Weight", "GMV"],
            "oos_cagr": [0.1, 0.08],
            "oos_annualized_return": [0.1, 0.08],
            "oos_volatility": [0.2, 0.15],
            "oos_sharpe": [0.4, 0.35],
            "oos_sortino": [0.6, 0.55],
            "oos_max_drawdown": [-0.2, -0.1],
            "oos_cvar_95": [-0.03, -0.02],
            "avg_turnover": [0.2, 0.3],
        }
    )
    rejected = pd.DataFrame(
        {
            "ticker": ["BBB"],
            "composite_quant_score": [0.5],
            "selection_reason": ["lower_score_after_feasible_selection"],
        }
    )
    chart_path = tmp_path / "chart.png"
    chart_path.write_bytes(b"chart-evidence")
    output = tmp_path / "portfolio.html"
    monkeypatch.setattr(report_builder, "HTML_PATH", output)
    report_builder._build_html(
        {
            "current": current,
            "comparison": comparison,
            "rejected": rejected,
            "decision": {"final_decision_reason": "Paired OOS evidence rule."},
            "config": {"declared_scope": "US-listed global-issuer equity research"},
            "run": {
                "run_id": "qv2-unit-run",
                "data_as_of_date": "2026-07-21",
            },
            "windows": pd.DataFrame({"fold": [0, 1]}),
            "balanced": "Equal Weight",
            "benchmark": "Equal Weight",
            "defensive": "GMV",
        },
        {
            key: chart_path
            for key in [
                "risk_return",
                "cumulative",
                "drawdown",
                "rolling",
                "exposure",
                "uncertainty",
                "cost",
            ]
        },
    )
    text = output.read_text(encoding="utf-8")
    assert "balanced_research_portfolio" in text
    assert "transparent_benchmark" in text
    assert "defensive_alternative" in text
    assert "US-listed global-issuer equity research" in text
    assert "qv2-unit-run" in text
    assert "2026-07-21" in text
    assert text.count("<figure>") == 7
    assert "NOT PROMOTED" not in text
