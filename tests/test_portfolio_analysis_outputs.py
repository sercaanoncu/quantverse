from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import scripts.build_quantverse_portfolio_analysis as report_builder
import scripts.build_quantverse_portfolio_excel as workbook_builder
from scripts.build_quantverse_portfolio_excel import CANONICAL_SHEET_NAMES
from scripts.validate_quantverse_v2_artifacts import _excel_sheet_names


def test_canonical_workbook_has_exactly_fifteen_user_facing_sheets():
    assert len(CANONICAL_SHEET_NAMES) == 15
    assert len(set(CANONICAL_SHEET_NAMES)) == 15
    assert CANONICAL_SHEET_NAMES[0] == "START_HERE"
    assert CANONICAL_SHEET_NAMES[-2:] == ("RAW_WEIGHTS", "RAW_OOS_RETURNS")


def test_report_and_workbook_derive_common_oos_observation_count():
    comparison = pd.DataFrame({"oos_observations": [315, 315, 315]})

    assert report_builder._common_oos_observations(comparison) == 315
    assert workbook_builder._common_oos_observations(comparison) == 315

    inconsistent = pd.DataFrame({"oos_observations": [315, 294]})
    with pytest.raises(RuntimeError, match="one positive common OOS"):
        report_builder._common_oos_observations(inconsistent)
    with pytest.raises(RuntimeError, match="one positive common OOS"):
        workbook_builder._common_oos_observations(inconsistent)


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
    assert text.count("<figure>") == 7
    assert "NOT PROMOTED" not in text
