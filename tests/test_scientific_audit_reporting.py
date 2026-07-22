import json
from pathlib import Path

import pandas as pd

import scripts.build_visual_scientific_audit_report as visual_report
from scripts.audit_global_scientific_sanity import run_audit
from scripts.build_explainable_excel_output import _workbook_payload
from scripts.build_explainable_excel_output import _as_boolean_mask as _excel_bool_mask
from scripts.build_methodology_source_audit import build_methodology_source_check
from scripts.build_user_requirement_traceability import build_traceability
from scripts.build_visual_scientific_audit_report import (
    ChartSpec,
    _chart_md,
    _current_v2_decision,
    _legacy_constraint_decision,
    _load_data,
    _market_cap_chart,
    _source_method_chart,
)
from project.data_pipeline.security_universe import REQUIRED_UNIVERSE_COLUMNS
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
    assert {
        "what_is_wrong",
        "why_it_matters",
        "evidence_file",
        "evidence_column",
        "promotion_blocker",
        "next_required_fix",
        "evidence_scope",
        "decision_scope",
        "blocks_v2_public_data_model",
        "blocks_institutional_global_master",
    }.issubset(issues.columns)
    assert {
        "v2_public_data_model_blockers",
        "institutional_global_master_blockers",
    }.issubset(summary.columns)
    assert {"source_data", "fx_currency", "return_risk_scale"}.issubset(
        set(dashboard["category"])
    )


def test_scientific_sanity_blocks_unverified_crypto_price_mapping(tmp_path):
    processed = tmp_path / "processed"
    universe_path = tmp_path / "current_global_equity_universe.csv"
    row = {column: "" for column in REQUIRED_UNIVERSE_COLUMNS}
    row.update(
        {
            "ticker": "BTC-USD",
            "name": "Bitcoin",
            "sleeve": "crypto_top100",
            "region": "Global",
            "country": "Global",
            "exchange": "Crypto",
            "currency": "USD",
            "asset_type": "crypto",
            "market_cap_usd": 1_000_000,
            "market_cap_rank": 1,
            "as_of_date": "2026-06-30",
            "source": "CoinGecko",
            "data_provider": "CoinGecko",
            "investable": True,
            "benchmark_only": False,
            "signal_only": False,
            "include": True,
            "proxy_type": "unverified_yahoo_crypto_symbol_candidate",
            "notes": "unit",
        }
    )
    _write_csv(universe_path, [row])

    _, issues, _ = run_audit(processed, universe_path)

    assert any(
        issue.startswith("unverified_crypto_price_mappings:")
        for issue in issues["issue"].astype(str)
    )
    assert any(
        issue.startswith("invalid_universe_eligibility_flags:")
        for issue in issues["issue"].astype(str)
    )
    crypto_issue = issues.loc[
        issues["issue"].astype(str).str.startswith("unverified_crypto_price_mappings:")
    ].iloc[0]
    assert crypto_issue["decision_scope"] == "institutional_global_master_promotion"
    assert not bool(crypto_issue["blocks_v2_public_data_model"])


def test_cross_sleeve_signal_only_overlap_is_not_investable_duplicate(tmp_path):
    processed = tmp_path / "processed"
    universe_path = tmp_path / "current_global_equity_universe.csv"
    active = {column: "" for column in REQUIRED_UNIVERSE_COLUMNS}
    active.update(
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sleeve": "global_equity_us",
            "region": "North America",
            "country": "United States",
            "exchange": "NASDAQ",
            "currency": "USD",
            "asset_type": "equity",
            "source": "unit",
            "data_provider": "unit",
            "investable": True,
            "benchmark_only": False,
            "signal_only": False,
            "include": True,
            "proxy_type": "current_public_data",
        }
    )
    signal = dict(active)
    signal.update(
        {
            "sleeve": "global_equity_nasdaq",
            "investable": False,
            "signal_only": True,
            "include": False,
            "proxy_type": "signal_only_index_overlap",
        }
    )
    _write_csv(universe_path, [active, signal])

    _, issues, _ = run_audit(processed, universe_path)

    assert (
        not issues["issue"]
        .astype(str)
        .str.startswith("duplicate_investable_tickers:")
        .any()
    )
    assert (
        not issues["issue"]
        .astype(str)
        .str.startswith("duplicate_tickers_in_universe:")
        .any()
    )


def test_active_promotion_blockers_are_scoped_separately(tmp_path):
    processed = tmp_path / "processed"
    universe_path = tmp_path / "missing_universe.csv"
    _write_csv(
        processed / "global_walk_forward_model_comparison.csv",
        [
            {
                "model_name": "Equal Weight",
                "model_status": "benchmark_only",
                "oos_observations": 252,
                "oos_cagr": 1.10,
                "oos_annualized_return": 0.80,
                "oos_volatility": 0.30,
                "oos_sharpe": 2.60,
                "oos_sortino": 4.00,
            },
            {
                "model_name": "Inverse Volatility",
                "model_status": "actually_run",
                "oos_observations": 252,
                "oos_cagr": 0.70,
                "oos_annualized_return": 0.55,
                "oos_volatility": 0.21,
                "oos_sharpe": 2.65,
                "oos_sortino": 4.10,
            },
        ],
    )
    (processed / "global_parameter_sensitivity_summary.json").write_text(
        json.dumps({"robustness_status": "diagnostic_configuration_stability_only"}),
        encoding="utf-8",
    )

    summary, issues, _ = run_audit(processed, universe_path)

    active = issues.loc[
        issues["decision_scope"].eq("active_public_data_challenger_promotion")
    ]
    assert {
        "nested_oos_robustness_not_implemented",
        "multiple_testing_control_incomplete: 2 compared models",
    }.issubset(set(active["issue"]))
    assert int(summary["active_challenger_promotion_blockers"].iloc[0]) >= 2
    assert not active["blocks_v2_public_data_model"].astype(bool).any()
    assert any(
        issue.startswith("Equal Weight: oos_cagr_above_100pct")
        for issue in issues["issue"].astype(str)
    )


def test_methodology_source_check_contains_required_guardrails():
    source_check = build_methodology_source_check()
    areas = set(source_check["methodology_area"])

    assert "Black-Litterman" in areas
    assert "FX normalization" in areas
    assert "random portfolio benchmarking" in areas
    assert {
        "portfolio theory rules",
        "risk rules",
        "econometrics/time-series rules",
        "ML validation rules",
        "data/source/FX rules",
    }.issubset(set(source_check["rule_family"]))
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


def test_visual_report_uses_current_universe_evidence_schemas(tmp_path, monkeypatch):
    processed = tmp_path / "processed"
    _write_csv(
        processed / "current_global_universe_summary.csv",
        [{"sleeve": "global_equity_us", "rows": 100, "included": 100}],
    )
    classification = [
        {
            "sleeve": "global_equity_us",
            "rows": 100,
            "classification": "blocked",
            "exact_supported_rows": 0,
        }
    ]
    _write_csv(
        processed / "global_exact_proxy_classification_report.csv", classification
    )
    data = _load_data(processed)

    def fail_if_empty_chart(*_args, **_kwargs):
        raise AssertionError("current evidence schema must not render an empty chart")

    monkeypatch.setattr(visual_report, "_empty_chart", fail_if_empty_chart)
    source_chart = tmp_path / "source.png"
    market_cap_chart = tmp_path / "market_cap.png"
    _source_method_chart(data["source"], source_chart)
    _market_cap_chart(data["market_cap"], market_cap_chart)

    assert len(data["universe"]) == 1
    assert source_chart.stat().st_size > 1_000
    assert market_cap_chart.stat().st_size > 1_000


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
        [
            {"ticker": "AAA", "included_in_returns": "True"},
            {"ticker": "BBB", "included_in_returns": "False"},
        ],
    )
    _write_csv(
        processed / "current_global_universe_summary.csv",
        [{"sleeve": "global_equity_us", "rows": 2, "included": 1}],
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
        "MODEL_APPLICABILITY",
        "FINAL_WEIGHTS",
        "WEIGHT_AUDIT",
        "METHODOLOGY_SOURCE_BASIS",
    }.issubset(sheet_names)
    assert payload["generated_by"] == "scripts/build_explainable_excel_output.py"
    assert not Path(payload["chart_folder"]).is_absolute()
    start_here = next(
        sheet for sheet in payload["sheets"] if sheet["name"] == "START_HERE"
    )
    start_text = " ".join(str(cell) for row in start_here["rows"] for cell in row)
    assert "Global USD master portfolio promotion is blocked" in start_text
    assert "Exact top-100 market-cap claim is not supported" in start_text
    requirement = next(
        sheet
        for sheet in payload["sheets"]
        if sheet["name"] == "REQUIREMENT_TRACEABILITY"
    )
    universe = next(sheet for sheet in payload["sheets"] if sheet["name"] == "UNIVERSE")
    methodology = next(
        sheet
        for sheet in payload["sheets"]
        if sheet["name"] == "METHODOLOGY_SOURCE_BASIS"
    )
    executive = next(
        sheet for sheet in payload["sheets"] if sheet["name"] == "EXECUTIVE_SUMMARY"
    )
    executive_values = {
        row[0]: row[1] for row in executive["rows"][1:] if len(row) >= 2
    }

    assert len(requirement["rows"]) > 30
    assert universe["rows"][1][0] == "global_equity_us"
    assert len(methodology["rows"]) > 10
    assert executive_values["Price included assets"] == 1
    assert executive_values["Price excluded assets"] == 1


def test_excel_boolean_mask_does_not_treat_false_string_as_true():
    mask = _excel_bool_mask(pd.Series(["True", "False", "1", "0", None]))

    assert mask.tolist() == [True, False, True, False, False]


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


def test_visual_audit_separates_v2_model_from_legacy_constraint_gate(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "final_public_data_research_model": "Equal Weight",
                "final_model_selection_decision": "not promoted",
                "institutional_global_master_promotion": "not_promoted",
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_master_decision_summary.json").write_text(
        json.dumps(
            {
                "final_model": "Equal Weight",
                "constraints_pass": False,
                "promotion_decision": "not promoted",
                "reason": "max_region_ok failed",
            }
        ),
        encoding="utf-8",
    )

    decision = _current_v2_decision(processed)
    constraint_text = _legacy_constraint_decision(decision)

    assert decision["final_model"] == "Equal Weight"
    assert decision["legacy_final_model"] == "Equal Weight"
    assert decision["legacy_constraints_pass"] is False
    assert "fails at least one recorded hard constraint" in constraint_text
