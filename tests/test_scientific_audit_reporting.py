import json
from pathlib import Path

import pandas as pd

from scripts.audit_global_scientific_sanity import run_audit
from scripts.build_explainable_excel_output import _workbook_payload
from scripts.build_methodology_source_audit import build_methodology_source_check
from scripts.build_user_requirement_traceability import build_traceability
from scripts.build_visual_scientific_audit_report import ChartSpec, _chart_md
from project.research.global_stock_selection import build_stock_selection_promotion_gate


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_scientific_sanity_flags_market_cap_fx_and_extreme_metrics(tmp_path):
    processed = tmp_path / "processed"
    universe = tmp_path / "current_global_equity_universe.csv"
    _write_csv(
        processed / "global_master_model_comparison.csv",
        [
            {
                "Model": "Equal Weight",
                "Status": "computed",
                "CAGR": 1.25,
                "Annual_Return": 1.50,
                "Volatility": 1.10,
                "Total_Return": 101.0,
                "Sharpe": 3.5,
                "Sortino": 6.0,
            },
            {"Model": "Black-Litterman", "Status": "blocked"},
        ],
    )
    _write_csv(
        processed / "real_global_universe_market_cap_coverage.csv",
        [{"sleeve": "global_equity_us", "rows": 100, "market_cap_rows": 0}],
    )
    _write_csv(
        processed / "global_fx_normalization_report.csv",
        [{"ticker": "TEST", "fx_normalization_status": "not_implemented"}],
    )
    _write_csv(
        processed / "global_master_candidate_weights.csv",
        [
            {"Model": "Policy Constrained", "Ticker": "TEST", "Weight": 1.0},
        ],
    )
    (processed / "global_master_decision_summary.json").write_text(
        json.dumps({"final_model": "Policy Constrained"}),
        encoding="utf-8",
    )
    _write_csv(
        processed / "global_master_constraint_audit.csv",
        [{"Model": "Policy Constrained", "All_Constraints_Pass": True}],
    )
    _write_csv(
        universe,
        [
            {"ticker": "TEST", "notes": ""},
            {"ticker": "TEST", "notes": "duplicate row"},
        ],
    )

    summary, issues, dashboard = run_audit(processed, universe)

    assert int(summary["total_issues"].iloc[0]) >= 4
    assert int(summary["promotion_blockers"].iloc[0]) >= 3
    assert {
        "fx_normalization_incomplete",
        "global_equity_us: equity_market_cap_coverage_missing",
        "duplicate_tickers_in_universe: 1",
    }.issubset(set(issues["issue"]))
    assert {"source_data", "fx_currency", "return_risk_scale"}.issubset(
        set(dashboard["category"])
    )


def test_methodology_source_check_contains_required_guardrails():
    source_check = build_methodology_source_check()
    areas = set(source_check["methodology_area"])

    assert "Black-Litterman" in areas
    assert "FX normalization" in areas
    assert "random portfolio benchmarking" in areas
    assert (
        source_check.loc[
            source_check["methodology_area"].eq("Black-Litterman"),
            "current_quantverse_status",
        ].iloc[0]
        == "blocked_by_data"
    )


def test_requirement_traceability_keeps_promotion_blocker_visible():
    matrix = build_traceability()

    assert len(matrix) >= 30
    row = matrix.loc[
        matrix["requirement"].str.contains("Nothing should be promoted", regex=False)
    ].iloc[0]
    assert row["status"] == "met"
    assert bool(row["this_sprint_fixes_it"])


def test_visual_report_chart_markdown_has_explanation_source_and_decision():
    spec = ChartSpec(
        key="fx_status",
        title="FX status",
        source="data/processed/global_fx_normalization_report.csv",
        explanation="Shows whether FX conversion is implemented.",
        importance="Global USD portfolios require base-currency returns.",
        red_flag="Missing FX conversion blocks promotion.",
        decision="not promoted",
        filename="fx_status.png",
    )

    markdown = "\n".join(_chart_md(1, spec))

    assert "Ne görüyorum?" in markdown
    assert "Neden önemli?" in markdown
    assert "Kırmızı bayrak ne?" in markdown
    assert "Hangi kararı destekliyor?" in markdown
    assert spec.source in markdown


def test_explainable_excel_payload_contains_required_sheets(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "global_master_decision_summary.json").write_text(
        json.dumps(
            {
                "final_model": "Policy Constrained",
                "promotion_decision": "not promoted",
                "reason": "unit-test blocker",
                "selected_holdings": 3,
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        processed / "global_scientific_sanity_summary.csv",
        [{"total_issues": 2, "promotion_blockers": 1}],
    )
    _write_csv(
        processed / "global_returns_coverage_report.csv",
        [{"ticker": "AAA", "included_in_returns": True}],
    )
    _write_csv(
        processed / "global_fx_normalization_report.csv",
        [{"ticker": "AAA", "fx_normalization_status": "native_base"}],
    )
    _write_csv(
        processed / "global_master_candidate_weights.csv",
        [{"Model": "Policy Constrained", "Ticker": "AAA", "Weight": 1.0}],
    )

    payload = _workbook_payload(processed)
    sheet_names = {sheet["name"] for sheet in payload["sheets"]}

    assert {
        "START_HERE",
        "EXECUTIVE_SUMMARY",
        "RED_FLAGS",
        "REQUIREMENT_TRACEABILITY",
        "FINAL_WEIGHTS",
        "METHODOLOGY_SOURCE_BASIS",
    }.issubset(sheet_names)
    assert payload["generated_by"] == "scripts/build_explainable_excel_output.py"


def test_promotion_gate_failure_reason_is_not_misleading():
    gate = build_stock_selection_promotion_gate(
        {
            "Beats_Equal_Weight_CAGR": False,
            "Beats_Equal_Weight_Sharpe": False,
            "Volatility_Ratio_vs_Equal_Weight": 2.0,
            "Max_Drawdown_Diff_vs_Equal_Weight": -1.0,
            "CVaR_Diff_vs_Equal_Weight": -1.0,
            "Random_Sharpe_Percentile": 0.1,
            "Turnover": 2.0,
            "Transaction_Cost_Drag": 1.0,
        }
    )

    assert gate["Promotion_Decision"] == "not promoted"
    assert "net CAGR is not greater than Equal Weight" in gate["Reason"]
    assert "not promoted because: net CAGR greater" not in gate["Reason"]
