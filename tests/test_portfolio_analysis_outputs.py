from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.build_quantverse_portfolio_analysis as report_builder
from scripts.build_quantverse_portfolio_excel import CANONICAL_SHEET_NAMES


def test_canonical_workbook_has_exactly_fifteen_user_facing_sheets():
    assert len(CANONICAL_SHEET_NAMES) == 15
    assert len(set(CANONICAL_SHEET_NAMES)) == 15
    assert CANONICAL_SHEET_NAMES[0] == "START_HERE"
    assert CANONICAL_SHEET_NAMES[-2:] == ("RAW_WEIGHTS", "RAW_OOS_RETURNS")


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
