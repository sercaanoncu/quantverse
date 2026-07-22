"""Build QuantVerse v2 explainable Excel workbook."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.reporting.artifact_publication import (  # noqa: E402
    publish_staged_files,
    staged_publication,
)
from project.reporting.quantverse_v2_publication import (  # noqa: E402
    RUN_IDENTITY_FIELDS,
    PublicationEvidence,
    load_publication_evidence,
)

PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "excel" / "quantverse_v2_research_output.xlsx"
PUBLICATION_MANIFEST = ROOT / "output" / "quantverse_v2_excel_publication_manifest.json"
EXCEL_ENGINE_KWARGS = {
    "options": {
        "strings_to_formulas": False,
        "strings_to_urls": False,
    }
}


SHEETS = {
    "UNIVERSE": "data/universe/current_global_equity_universe.csv",
    "STOCK_SCORES": "data/processed/global_stock_scores.csv",
    "SELECTED_STOCKS_RAW": "data/processed/global_stock_scores.csv",
    "SELECTED_STOCKS": "data/processed/global_selected_stocks_report_view.csv",
    "SELECTED_METADATA_QUALITY": "data/processed/global_selected_stocks_report_view_quality.csv",
    "SECURITY_IDENTITY": "data/processed/global_security_identity_audit.csv",
    "HISTORY_ELIGIBILITY": "data/processed/global_security_history_eligibility.csv",
    "FEATURE_ELIGIBILITY": "data/processed/global_feature_history_eligibility.csv",
    "COUNT_RECONCILIATION": "data/processed/global_cross_artifact_count_reconciliation.csv",
    "RETURN_FORECASTS": "data/processed/global_stock_return_forecasts.csv",
    "MODEL_LEAGUE": "data/processed/global_portfolio_league.csv",
    "FINAL_WEIGHTS": "data/processed/global_portfolio_league_weights.csv",
    "ALL_MODEL_WEIGHTS": "data/processed/global_portfolio_league_weights.csv",
    "RISK_METRICS": "data/processed/global_portfolio_risk_report.csv",
    "RISK_CONTRIBUTIONS": "data/processed/global_risk_contribution_report.csv",
    "STRESS_TESTS": "data/processed/global_stress_test_results.csv",
    "WALK_FORWARD": "data/processed/global_walk_forward_model_comparison.csv",
    "BENCHMARK_COMPARISON": "data/processed/global_master_equal_weight_comparison.csv",
    "RANDOM_PORTFOLIOS": "data/processed/global_master_random_portfolio_benchmark.csv",
    "MODEL_SELECTION": "data/processed/global_model_selection_report.csv",
    "MODEL_SELECTION_DIAGNOSTICS": "data/processed/global_model_selection_diagnostics.csv",
    "FINAL_MODEL_DECISION": "data/processed/global_final_model_decision.csv",
    "ROBUSTNESS": "data/processed/global_robustness_sensitivity.csv",
    "RANDOM_DISTRIBUTION": "data/processed/global_random_portfolio_distribution.csv",
    "RANDOM_PERCENTILES": "data/processed/global_random_portfolio_percentile_report.csv",
    "EXPOSURE_REGION": "data/processed/global_region_exposure.csv",
    "EXPOSURE_COUNTRY": "data/processed/global_country_exposure.csv",
    "EXPOSURE_LISTING_COUNTRY": "data/processed/global_listing_country_exposure.csv",
    "EXPOSURE_ISSUER_COUNTRY": "data/processed/global_issuer_country_exposure.csv",
    "EXPOSURE_ECON_COUNTRY": "data/processed/global_economic_country_exposure.csv",
    "EXPOSURE_CURRENCY": "data/processed/global_currency_exposure.csv",
    "EXPOSURE_EXCHANGE": "data/processed/global_exchange_exposure.csv",
    "EXPOSURE_SECTOR": "data/processed/global_sector_exposure.csv",
    "EXPOSURE_INDUSTRY": "data/processed/global_industry_exposure.csv",
    "EXPOSURE_METADATA": "data/processed/global_exposure_metadata_quality.csv",
    "TOP_HOLDINGS_EXPLANATION": "data/processed/global_top_holdings_explanation.csv",
    "FORECAST_VALIDATION": "data/processed/global_forecast_validation_by_horizon.csv",
    "PUBLISH_READINESS": "data/processed/global_model_selection_report.csv",
    "WARNINGS": "data/processed/global_risk_metric_sanity_checks.csv",
    "CLAIM_CONTROL": "data/processed/global_exact_proxy_classification_report.csv",
    "VISUAL_SUMMARY": "data/processed/quantverse_v2_visual_analytics_summary.csv",
    "VISUAL_EQUITY_CURVE": "data/processed/quantverse_v2_visual_equity_curve.csv",
    "VISUAL_DRAWDOWN": "data/processed/quantverse_v2_visual_drawdown_curve.csv",
    "VISUAL_RISK_RETURN": "data/processed/quantverse_v2_visual_model_risk_return.csv",
    "VISUAL_FORECAST_ERROR": "data/processed/quantverse_v2_visual_forecast_error.csv",
    "VISUAL_RANDOM_BENCH": "data/processed/quantverse_v2_visual_random_benchmark.csv",
    "VISUAL_EXPOSURE": "data/processed/quantverse_v2_visual_exposure.csv",
    "VISUAL_TOP_HOLDINGS": "data/processed/quantverse_v2_visual_top_holdings.csv",
    "VISUAL_VALIDATION": "data/processed/quantverse_v2_visual_validation.csv",
}


def main() -> int:
    snapshot_csv_paths = [
        ROOT / relative_path for relative_path in dict.fromkeys(SHEETS.values())
    ]
    evidence = load_publication_evidence(
        ROOT,
        additional_csv_paths=snapshot_csv_paths,
        additional_json_paths=[
            PROCESSED / "quantverse_v2_demo_summary.json",
        ],
    )
    run_identity = {
        field: evidence.manifest.get(field, "missing") for field in RUN_IDENTITY_FIELDS
    }
    with staged_publication(ROOT, "quantverse-v2-excel") as stage:
        staged_output = stage / OUTPUT.name
        _build_workbook(staged_output, evidence)
        publish_staged_files(
            {staged_output: OUTPUT},
            root=ROOT,
            manifest_path=PUBLICATION_MANIFEST,
            run_identity=run_identity,
            publication_type="quantverse_v2_analytical_workbook",
        )
    print(f"QuantVerse v2 Excel written: {OUTPUT}")
    print(f"QuantVerse v2 Excel publication manifest: {PUBLICATION_MANIFEST}")
    return 0


def _build_workbook(path: Path, evidence: PublicationEvidence) -> None:
    summary = _summary_rows(evidence)
    with pd.ExcelWriter(
        path,
        engine="xlsxwriter",
        engine_kwargs=EXCEL_ENGINE_KWARGS,
    ) as writer:
        writer.book.set_properties(
            {
                "title": "QuantVerse v2 Analytical Research Workbook",
                "subject": "Public-data portfolio research and validation evidence",
                "author": "QuantVerse",
                "comments": "Research only; not investment advice.",
            }
        )
        tabular_frames: dict[str, pd.DataFrame] = {}
        start_here = pd.DataFrame(_start_here())
        start_here.to_excel(writer, sheet_name="START_HERE", index=False)
        tabular_frames["START_HERE"] = start_here
        _write_executive_dashboard(writer, evidence)
        tabular_frames.update(_write_user_facing_sheets(writer, evidence))
        _write_dashboard(writer, evidence)
        _write_visual_analytics_dashboard(writer, evidence)
        executive_summary = pd.DataFrame(summary)
        executive_summary.to_excel(writer, sheet_name="EXECUTIVE_SUMMARY", index=False)
        tabular_frames["EXECUTIVE_SUMMARY"] = executive_summary
        for sheet, raw_path in SHEETS.items():
            frame = evidence.frame_for(ROOT / raw_path)
            if sheet == "FINAL_WEIGHTS" and not frame.empty and "model_name" in frame:
                frame = frame.loc[
                    frame["model_name"].astype(str).eq(evidence.final_model)
                ].copy()
            if (
                sheet == "SELECTED_STOCKS_RAW"
                and not frame.empty
                and "selection_flag" in frame
            ):
                frame = frame.loc[frame["selection_flag"].map(_truthy)]
            if sheet == "SELECTED_STOCKS":
                _write_selected_stocks_sheet(writer, frame)
                continue
            frame.to_excel(writer, sheet_name=sheet[:31], index=False)
            tabular_frames[sheet[:31]] = frame
        appendix = pd.DataFrame(_appendix(evidence))
        appendix.to_excel(writer, sheet_name="APPENDIX_RAW_TABLES", index=False)
        tabular_frames["APPENDIX_RAW_TABLES"] = appendix
        formulas = pd.DataFrame(_formula_dictionary())
        formulas.to_excel(writer, sheet_name="APPENDIX_FORMULAS", index=False)
        tabular_frames["APPENDIX_FORMULAS"] = formulas
        _format_tabular_sheets(writer, tabular_frames)


def _write_executive_dashboard(
    writer: pd.ExcelWriter,
    evidence: PublicationEvidence,
) -> None:
    """Create the first decision-oriented analytical dashboard."""
    workbook = writer.book
    worksheet = workbook.add_worksheet("EXECUTIVE_DASHBOARD")
    writer.sheets["EXECUTIVE_DASHBOARD"] = worksheet
    worksheet.hide_gridlines(2)
    worksheet.freeze_panes(3, 0)
    worksheet.set_tab_color("#2A9D8F")
    worksheet.set_column("A:A", 3)
    worksheet.set_column("B:C", 18)
    worksheet.set_column("D:J", 15)
    worksheet.set_column("M:Q", 14, None, {"hidden": True})

    title = workbook.add_format(
        {
            "bold": True,
            "font_size": 22,
            "font_color": "white",
            "bg_color": "#17252E",
            "align": "left",
            "valign": "vcenter",
        }
    )
    subtitle = workbook.add_format(
        {
            "font_size": 10,
            "font_color": "#D8E4E7",
            "bg_color": "#17252E",
            "align": "left",
            "valign": "vcenter",
        }
    )
    decision = workbook.add_format(
        {
            "bold": True,
            "font_size": 13,
            "font_color": "#17252E",
            "bg_color": "#FFF6D8",
            "border": 1,
            "border_color": "#E9C46A",
            "text_wrap": True,
            "valign": "vcenter",
        }
    )
    metric_label = workbook.add_format(
        {
            "bold": True,
            "font_color": "#176B87",
            "bg_color": "#EAF4F8",
            "border": 1,
            "border_color": "#CBD9DE",
            "align": "center",
        }
    )
    note = workbook.add_format(
        {
            "font_color": "#68737D",
            "font_size": 9,
            "text_wrap": True,
            "valign": "top",
        }
    )
    warning = workbook.add_format(
        {
            "bold": True,
            "font_color": "#8A2D20",
            "bg_color": "#FCE8E6",
            "border": 1,
            "border_color": "#C8553D",
            "text_wrap": True,
            "valign": "vcenter",
        }
    )

    worksheet.merge_range("B2:J3", "QuantVerse v2 Analytical Research Workbook", title)
    worksheet.merge_range(
        "B4:J4",
        (
            f"Run {evidence.manifest.get('run_id')} | "
            f"Data as of {evidence.manifest.get('data_as_of_date')} | "
            "Public-data research, not investment advice"
        ),
        subtitle,
    )
    worksheet.merge_range(
        "B6:E8",
        f"CURRENT RESEARCH MODEL\n{evidence.final_model}",
        decision,
    )
    worksheet.merge_range(
        "F6:J8",
        f"PORTFOLIO PROMOTION\n{evidence.final_decision.upper()}",
        decision,
    )

    final_row = evidence.model_selection.loc[
        evidence.model_selection["model_name"].astype(str).eq(evidence.final_model)
    ]
    row = final_row.iloc[0] if not final_row.empty else pd.Series(dtype=object)
    metrics = [
        (
            "OOS annualized return",
            _float(row.get("walk_forward_annualized_return")),
            "0.0%",
        ),
        ("OOS volatility", _float(row.get("walk_forward_volatility")), "0.0%"),
        ("OOS Sharpe", _float(row.get("walk_forward_sharpe")), "0.00"),
        ("OOS max drawdown", _float(row.get("walk_forward_max_drawdown")), "0.0%"),
    ]
    for index, (label, value, number_format) in enumerate(metrics):
        first = 1 + index * 2
        worksheet.merge_range(10, first, 10, first + 1, label, metric_label)
        formatted_value = workbook.add_format(
            {
                "bold": True,
                "font_size": 17,
                "font_color": "#17252E",
                "bg_color": "white",
                "border": 1,
                "border_color": "#CBD9DE",
                "align": "center",
                "valign": "vcenter",
                "num_format": number_format,
            }
        )
        worksheet.merge_range(11, first, 12, first + 1, value, formatted_value)

    worksheet.merge_range(
        "B15:J17",
        (
            "Metric warning: the stitched OOS path has approximately 252 "
            "observations. High annualized return and Sharpe estimates are "
            "regime-sensitive warnings, not expected future performance."
        ),
        warning,
    )
    worksheet.merge_range(
        "B19:J21",
        str(evidence.decision.get("final_decision_reason", "")),
        note,
    )

    comparison = evidence.model_selection.sort_values(
        "book_grounded_rank", na_position="last"
    ).head(8)
    comparison[["model_name", "walk_forward_sharpe"]].to_excel(
        writer,
        sheet_name="EXECUTIVE_DASHBOARD",
        startrow=1,
        startcol=12,
        index=False,
    )
    chart = workbook.add_chart({"type": "column"})
    chart.add_series(
        {
            "name": "OOS Sharpe",
            "categories": [
                "EXECUTIVE_DASHBOARD",
                2,
                12,
                1 + len(comparison),
                12,
            ],
            "values": [
                "EXECUTIVE_DASHBOARD",
                2,
                13,
                1 + len(comparison),
                13,
            ],
            "fill": {"color": "#176B87"},
        }
    )
    chart.set_title({"name": "Model comparison: stitched OOS Sharpe"})
    chart.set_y_axis({"name": "Sharpe", "major_gridlines": {"visible": True}})
    chart.set_legend({"none": True})
    chart.set_style(10)
    worksheet.insert_chart("B24", chart, {"x_scale": 1.15, "y_scale": 1.0})

    holdings = evidence.final_weights.sort_values("weight", ascending=False).head(12)
    holdings[["ticker", "weight"]].to_excel(
        writer,
        sheet_name="EXECUTIVE_DASHBOARD",
        startrow=12,
        startcol=12,
        index=False,
    )
    chart = workbook.add_chart({"type": "bar"})
    chart.add_series(
        {
            "name": "Weight",
            "categories": [
                "EXECUTIVE_DASHBOARD",
                13,
                12,
                12 + len(holdings),
                12,
            ],
            "values": [
                "EXECUTIVE_DASHBOARD",
                13,
                13,
                12 + len(holdings),
                13,
            ],
            "fill": {"color": "#2A9D8F"},
        }
    )
    chart.set_title({"name": "Largest final-model holdings"})
    chart.set_x_axis({"name": "Weight", "num_format": "0.0%"})
    chart.set_legend({"none": True})
    chart.set_style(10)
    worksheet.insert_chart("F24", chart, {"x_scale": 1.15, "y_scale": 1.0})


def _write_user_facing_sheets(
    writer: pd.ExcelWriter,
    evidence: PublicationEvidence,
) -> dict[str, pd.DataFrame]:
    """Write curated reader sheets before the technical evidence appendix."""
    frames: dict[str, pd.DataFrame] = {}
    holdings = evidence.holdings.loc[
        evidence.holdings["model_name"].astype(str).eq(evidence.final_model)
    ].copy()
    portfolio_columns = [
        "ticker",
        "name",
        "weight",
        "sector",
        "industry",
        "issuer_country",
        "listing_country",
        "listing_currency",
        "risk_contribution_pct",
    ]
    frames["PORTFOLIO"] = holdings[
        [column for column in portfolio_columns if column in holdings]
    ]
    frames["HOLDINGS_DETAIL"] = holdings

    comparison_columns = [
        "model_name",
        "model_status",
        "walk_forward_annualized_return",
        "walk_forward_volatility",
        "walk_forward_sharpe",
        "walk_forward_sortino",
        "walk_forward_max_drawdown",
        "walk_forward_cvar_95",
        "turnover",
        "random_sharpe_percentile",
        "selection_label",
    ]
    frames["MODEL_COMPARISON"] = evidence.model_selection[
        [column for column in comparison_columns if column in evidence.model_selection]
    ].sort_values("walk_forward_sharpe", ascending=False)
    decision_columns = [
        "model_name",
        "model_status",
        "eligible_final_model",
        "constraint_pass",
        "uncertainty_gate_pass",
        "random_sharpe_gate_pass",
        "robustness_gate_pass",
        "robustness_evidence_status",
        "selection_label",
        "rejection_reason",
    ]
    frames["MODEL_DECISIONS"] = evidence.model_selection[
        [column for column in decision_columns if column in evidence.model_selection]
    ]
    frames["UNCERTAINTY"] = evidence.uncertainty
    frames["RISK"] = evidence.risk
    frames["EXPOSURE"] = evidence.exposure
    forecast_validation = evidence.frame_for(
        PROCESSED / "global_forecast_validation_by_horizon.csv"
    )
    frames["FORECASTS"] = forecast_validation
    eligibility_columns = [
        "ticker",
        "identity_continuity_status",
        "history_contamination_status",
        "observed_return_count",
        "standard_scoring_eligible",
        "forecast_eligible",
        "walk_forward_eligible",
        "exclusion_reason",
        "warning_flags",
    ]
    frames["ELIGIBILITY"] = evidence.eligibility[
        [column for column in eligibility_columns if column in evidence.eligibility]
    ]
    frames["AUDIT_FINDINGS"] = _audit_findings(evidence)
    frames["DECISION_REGISTER"] = _decision_register_rows()
    frames["FORMULA_DICTIONARY"] = pd.DataFrame(_formula_dictionary())
    frames["DATA_DICTIONARY"] = _data_dictionary()

    for sheet_name, frame in frames.items():
        frame.to_excel(writer, sheet_name=sheet_name, index=False)
    return frames


def _audit_findings(evidence: PublicationEvidence) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for source, frame in [
        ("risk_metric_sanity", evidence.sanity),
        ("visual_validation", evidence.visual_validation),
    ]:
        for _, row in frame.iterrows():
            passed = _truthy(row.get("passed"))
            rows.append(
                {
                    "source": source,
                    "finding": row.get("check", "unnamed_check"),
                    "status": "passed" if passed else "failed",
                    "details": row.get("details", ""),
                    "promotion_blocker": not passed,
                }
            )
    for _, row in evidence.model_selection.iterrows():
        warning = str(row.get("extreme_metric_warning", "")).strip()
        if warning and warning.lower() not in {"none", "nan"}:
            rows.append(
                {
                    "source": "model_selection",
                    "finding": f"{row.get('model_name')} metric warning",
                    "status": "warning",
                    "details": warning,
                    "promotion_blocker": True,
                }
            )
    return pd.DataFrame(rows)


def _decision_register_rows() -> pd.DataFrame:
    path = ROOT / "docs" / "audit" / "QUANTVERSE_V2_DECISION_REGISTER.md"
    if not path.exists():
        return pd.DataFrame({"status": ["decision register unavailable"]})
    rows: list[dict[str, str]] = []
    text = path.read_text(encoding="utf-8")
    for section in text.split("\n## "):
        if not section.startswith("QV2-DEC-"):
            continue
        heading, *body = section.splitlines()
        decision_id, _, title = heading.partition(" - ")
        fields: dict[str, str] = {}
        for line in body:
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) == 2 and cells[0] != "Field":
                fields[cells[0]] = cells[1].replace("`", "")
        rows.append(
            {
                "decision_id": decision_id,
                "title": title,
                "problem": fields.get("Problem", ""),
                "chosen_method": fields.get("Chosen method", ""),
                "observed_impact": fields.get("Observed impact", ""),
                "invalidation_conditions": fields.get("Invalidation conditions", ""),
                "residual_limitation": fields.get("Residual limitation", ""),
                "status": fields.get("Status", ""),
            }
        )
    return pd.DataFrame(rows)


def _data_dictionary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (
                "START_HERE",
                "Workbook navigation",
                "Read first",
                "Explains evidence boundaries and next sheets",
            ),
            (
                "EXECUTIVE_DASHBOARD",
                "Derived from final decision, model selection and weights",
                "Decision summary",
                "Point estimates remain sample-dependent",
            ),
            (
                "PORTFOLIO",
                "global_top_holdings_explanation.csv",
                "Full final-model holdings",
                "Research weights, not recommendations",
            ),
            (
                "MODEL_COMPARISON",
                "global_model_selection_report.csv",
                "Same-protocol OOS comparison",
                "Short OOS history",
            ),
            (
                "MODEL_DECISIONS",
                "global_model_selection_report.csv",
                "Promotion and rejection gates",
                "Robustness remains diagnostic",
            ),
            (
                "WALK_FORWARD",
                "global_walk_forward_model_comparison.csv",
                "Stitched non-overlapping OOS metrics",
                "Current-universe public data, not PIT",
            ),
            (
                "UNCERTAINTY",
                "global_walk_forward_uncertainty.csv",
                "Paired block-bootstrap intervals",
                "Approximately 252 paired observations",
            ),
            (
                "RISK",
                "global_portfolio_risk_report.csv",
                "Return, volatility, drawdown and tail metrics",
                "Historical estimates do not forecast future loss",
            ),
            (
                "EXPOSURE",
                "quantverse_v2_visual_exposure.csv",
                "Portfolio concentration by metadata dimension",
                "Economic-country coverage can be unavailable",
            ),
            (
                "FORECASTS",
                "global_forecast_validation_by_horizon.csv",
                "Model error versus random walk",
                "Diagnostic only; no allocation promotion",
            ),
            (
                "SECURITY_IDENTITY",
                "global_security_identity_audit.csv",
                "Ticker/listing identity evidence",
                "Public evidence is not an institutional security master",
            ),
            (
                "AUDIT_FINDINGS",
                "Risk, visual and selection validators",
                "Failures and warnings",
                "A passing file check alone is not scientific proof",
            ),
        ],
        columns=["sheet", "source", "purpose", "limitation"],
    )


def _format_tabular_sheets(
    writer: pd.ExcelWriter,
    frames: dict[str, pd.DataFrame],
) -> None:
    """Apply bounded, readable formatting to evidence tables."""
    workbook = writer.book
    header = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#1F2937",
            "font_color": "white",
            "text_wrap": True,
            "valign": "top",
            "border": 1,
        }
    )
    body = workbook.add_format({"text_wrap": True, "valign": "top"})
    percent = workbook.add_format(
        {"text_wrap": True, "valign": "top", "num_format": "0.00%"}
    )
    number = workbook.add_format(
        {"text_wrap": True, "valign": "top", "num_format": "0.0000"}
    )
    user_facing = {
        "START_HERE",
        "PORTFOLIO",
        "HOLDINGS_DETAIL",
        "MODEL_COMPARISON",
        "MODEL_DECISIONS",
        "UNCERTAINTY",
        "RISK",
        "EXPOSURE",
        "FORECASTS",
        "ELIGIBILITY",
        "AUDIT_FINDINGS",
        "DECISION_REGISTER",
        "FORMULA_DICTIONARY",
        "DATA_DICTIONARY",
    }
    for sheet_name, frame in frames.items():
        worksheet = writer.sheets[sheet_name]
        worksheet.hide_gridlines(2)
        worksheet.freeze_panes(1, 0)
        worksheet.set_row(0, 30, header)
        worksheet.set_tab_color("#2A9D8F" if sheet_name in user_facing else "#8A969C")
        if not frame.empty and len(frame.columns):
            worksheet.autofilter(0, 0, len(frame), len(frame.columns) - 1)
        for column_index, column in enumerate(frame.columns):
            worksheet.write(0, column_index, column, header)
            sample = frame[column].head(100).fillna("").astype(str)
            maximum = max(
                [len(str(column)), *(len(value) for value in sample)],
                default=len(str(column)),
            )
            width = min(max(maximum + 2, 10), 32)
            column_name = str(column).lower()
            if pd.api.types.is_numeric_dtype(frame[column]) and any(
                token in column_name
                for token in [
                    "weight",
                    "return",
                    "volatility",
                    "drawdown",
                    "cvar",
                    "var_",
                    "percentile",
                    "probability",
                    "contribution_pct",
                ]
            ):
                cell_format = percent
            elif pd.api.types.is_numeric_dtype(frame[column]):
                cell_format = number
            else:
                cell_format = body
            worksheet.set_column(column_index, column_index, width, cell_format)
            if any(
                token in column_name
                for token in ["status", "decision", "warning", "blocker", "passed"]
            ):
                worksheet.conditional_format(
                    1,
                    column_index,
                    max(len(frame), 1),
                    column_index,
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": "fail",
                        "format": workbook.add_format(
                            {"bg_color": "#FCE8E6", "font_color": "#8A2D20"}
                        ),
                    },
                )
                worksheet.conditional_format(
                    1,
                    column_index,
                    max(len(frame), 1),
                    column_index,
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": "not promoted",
                        "format": workbook.add_format(
                            {"bg_color": "#FFF6D8", "font_color": "#6B5300"}
                        ),
                    },
                )

    start = writer.sheets.get("START_HERE")
    if start is not None:
        start.activate()
        start.set_column("A:A", 30, body)
        start.set_column("B:B", 92, body)
        for row in range(1, len(frames["START_HERE"]) + 1):
            start.set_row(row, 42)

    executive = writer.sheets.get("EXECUTIVE_SUMMARY")
    if executive is not None:
        executive.set_column("A:A", 42, body)
        executive.set_column("B:B", 82, body)

    reconciliation = writer.sheets.get("COUNT_RECONCILIATION")
    if reconciliation is not None:
        reconciliation.set_column("A:A", 30, body)
        reconciliation.set_column("B:C", 14, body)
        reconciliation.set_column("D:D", 36, body)
        reconciliation.set_column("E:F", 38, body)
        reconciliation.set_column("G:G", 12, body)
        reconciliation.set_column("H:H", 68, body)
        reconciliation.set_column("I:J", 32, body)
        for row in range(1, len(frames["COUNT_RECONCILIATION"]) + 1):
            reconciliation.set_row(row, 44)

    identity = writer.sheets.get("SECURITY_IDENTITY")
    if identity is not None:
        identity.freeze_panes(1, 2)
        identity.set_column("A:B", 13, body)
        identity.set_column("C:D", 38, body)
        identity.set_column("E:G", 24, body)
        identity.set_column("X:X", 65, body)
        identity.set_column("AD:AD", 58, body)


def _write_dashboard(
    writer: pd.ExcelWriter,
    evidence: PublicationEvidence,
) -> None:
    summary = evidence.json_for(PROCESSED / "quantverse_v2_demo_summary.json")
    risk = evidence.risk
    weights = evidence.weights
    exposure_metadata = evidence.frame_for(
        PROCESSED / "global_exposure_metadata_quality.csv"
    )
    final_model = evidence.final_model
    integrity_status = str(summary.get("numerical_integrity_status", "not available"))
    integrity_failed_checks = summary.get("numerical_integrity_failed_checks")
    risk_row = (
        risk.loc[risk["model_name"].astype(str).eq(final_model)].iloc[0].to_dict()
        if not risk.empty
        and "model_name" in risk
        and risk["model_name"].astype(str).eq(final_model).any()
        else {}
    )
    dashboard = pd.DataFrame(
        [
            {"metric": "final_selected_model", "value": final_model},
            {
                "metric": "final_public_data_research_model",
                "value": summary.get("final_public_data_research_model", final_model),
            },
            {
                "metric": "institutional_global_master_promotion",
                "value": summary.get(
                    "institutional_global_master_promotion",
                    summary.get("promotion_decision", "not promoted"),
                ),
            },
            {
                "metric": "promotion_decision",
                "value": summary.get("final_model_selection_decision", "not promoted"),
            },
            {
                "metric": "final_holdings_count",
                "value": summary.get("final_selected_holdings"),
            },
            {"metric": "weight_sum", "value": summary.get("weight_sum")},
            {"metric": "annualized_return", "value": risk_row.get("annualized_return")},
            {
                "metric": "annualized_volatility",
                "value": risk_row.get("annualized_volatility"),
            },
            {"metric": "sharpe", "value": risk_row.get("sharpe")},
            {"metric": "max_drawdown", "value": risk_row.get("max_drawdown")},
            {"metric": "var_95", "value": risk_row.get("var_95")},
            {"metric": "cvar_95", "value": risk_row.get("cvar_95")},
            {
                "metric": "walk_forward_status",
                "value": summary.get("walk_forward_status"),
            },
            {
                "metric": "forecast_validation_status",
                "value": summary.get("forecast_validation_status"),
            },
            {
                "metric": "numerical_integrity_status",
                "value": integrity_status,
            },
            {
                "metric": "numerical_integrity_failed_checks",
                "value": integrity_failed_checks,
            },
            {
                "metric": "exposure_metadata_status",
                "value": summary.get(
                    "exposure_metadata_status",
                    _first_cell(exposure_metadata, "exposure_metadata_status"),
                ),
            },
            {
                "metric": "sector_coverage_ratio",
                "value": summary.get(
                    "sector_coverage_ratio",
                    _first_cell(exposure_metadata, "sector_coverage_ratio"),
                ),
            },
            {
                "metric": "industry_coverage_ratio",
                "value": summary.get(
                    "industry_coverage_ratio",
                    _first_cell(exposure_metadata, "industry_coverage_ratio"),
                ),
            },
            {
                "metric": "issuer_country_coverage_ratio",
                "value": summary.get(
                    "issuer_country_coverage_ratio",
                    _first_cell(exposure_metadata, "issuer_country_coverage_ratio"),
                ),
            },
            {
                "metric": "economic_country_coverage_ratio",
                "value": summary.get(
                    "economic_country_coverage_ratio",
                    _first_cell(exposure_metadata, "economic_country_coverage_ratio"),
                ),
            },
            {
                "metric": "listing_country_coverage_ratio",
                "value": summary.get(
                    "listing_country_coverage_ratio",
                    _first_cell(exposure_metadata, "listing_country_coverage_ratio"),
                ),
            },
            {
                "metric": "metadata_confidence_distribution",
                "value": summary.get(
                    "metadata_confidence_distribution",
                    _first_cell(exposure_metadata, "metadata_confidence_distribution"),
                ),
            },
        ]
    )
    dashboard.to_excel(writer, sheet_name="PORTFOLIO_DASHBOARD", index=False)
    workbook = writer.book
    worksheet = writer.sheets["PORTFOLIO_DASHBOARD"]
    header = workbook.add_format(
        {"bold": True, "bg_color": "#1F2937", "font_color": "white"}
    )
    warning = workbook.add_format({"bg_color": "#FEE2E2"})
    worksheet.set_row(0, None, header)
    worksheet.set_column("A:A", 30)
    worksheet.set_column("B:B", 48)
    if integrity_status != "passed":
        worksheet.write(13, 1, integrity_status, warning)

    final_weights = (
        weights.loc[weights["model_name"].astype(str).eq(final_model)].copy()
        if not weights.empty and "model_name" in weights
        else pd.DataFrame()
    )
    if not final_weights.empty:
        top = final_weights.sort_values("weight", ascending=False).head(10)
        start_row = len(dashboard) + 3
        top[["ticker", "weight"]].to_excel(
            writer,
            sheet_name="PORTFOLIO_DASHBOARD",
            startrow=start_row,
            index=False,
        )
        worksheet.write(start_row - 1, 0, "Top holdings by weight")
        chart = workbook.add_chart({"type": "bar"})
        chart.add_series(
            {
                "name": "Weight",
                "categories": [
                    "PORTFOLIO_DASHBOARD",
                    start_row + 1,
                    0,
                    start_row + len(top),
                    0,
                ],
                "values": [
                    "PORTFOLIO_DASHBOARD",
                    start_row + 1,
                    1,
                    start_row + len(top),
                    1,
                ],
            }
        )
        chart.set_title({"name": "Top Holdings Weight"})
        chart.set_x_axis({"name": "Weight"})
        chart.set_y_axis({"name": "Ticker"})
        worksheet.insert_chart("D4", chart, {"x_scale": 1.25, "y_scale": 1.15})

    risk_chart_data = pd.DataFrame(
        [
            {
                "metric": "Annual Return",
                "value": _float(risk_row.get("annualized_return")),
            },
            {
                "metric": "Volatility",
                "value": _float(risk_row.get("annualized_volatility")),
            },
            {"metric": "Sharpe", "value": _float(risk_row.get("sharpe"))},
            {"metric": "Max Drawdown", "value": _float(risk_row.get("max_drawdown"))},
            {"metric": "CVaR 95", "value": _float(risk_row.get("cvar_95"))},
        ]
    )
    risk_start = len(dashboard) + 18
    risk_chart_data.to_excel(
        writer,
        sheet_name="PORTFOLIO_DASHBOARD",
        startrow=risk_start,
        index=False,
    )
    chart = workbook.add_chart({"type": "column"})
    chart.add_series(
        {
            "name": "Risk/Return",
            "categories": [
                "PORTFOLIO_DASHBOARD",
                risk_start + 1,
                0,
                risk_start + len(risk_chart_data),
                0,
            ],
            "values": [
                "PORTFOLIO_DASHBOARD",
                risk_start + 1,
                1,
                risk_start + len(risk_chart_data),
                1,
            ],
        }
    )
    chart.set_title({"name": "Final Model Metrics"})
    worksheet.insert_chart("D22", chart, {"x_scale": 1.25, "y_scale": 1.0})


def _write_visual_analytics_dashboard(
    writer: pd.ExcelWriter,
    evidence: PublicationEvidence,
) -> None:
    workbook = writer.book
    worksheet = workbook.add_worksheet("VISUAL_ANALYTICS_DASHBOARD")
    writer.sheets["VISUAL_ANALYTICS_DASHBOARD"] = worksheet

    title = workbook.add_format(
        {"bold": True, "font_size": 16, "bg_color": "#111827", "font_color": "white"}
    )
    header = workbook.add_format(
        {"bold": True, "bg_color": "#1F2937", "font_color": "white"}
    )
    note = workbook.add_format({"text_wrap": True, "valign": "top"})
    warning = workbook.add_format({"bg_color": "#FEF3C7", "text_wrap": True})

    worksheet.merge_range("A1:F1", "QuantVerse v2 Visual Portfolio Analytics", title)
    worksheet.merge_range(
        "A2:F2",
        "All charts are diagnostic public-data research views. They do not create a new model or investment recommendation.",
        note,
    )
    worksheet.set_column("A:A", 24)
    worksheet.set_column("B:F", 22)

    summary = evidence.frame_for(
        PROCESSED / "quantverse_v2_visual_analytics_summary.csv"
    )
    validation = evidence.visual_validation.copy()
    equity = evidence.equity.tail(260).copy()
    drawdown = evidence.drawdown.tail(260).copy()
    risk_return = evidence.risk_return.copy()
    forecast = evidence.forecast_error.copy()
    random_bench = evidence.random_benchmark.copy()
    exposure = evidence.exposure.copy()
    if not exposure.empty and "exposure_type" in exposure:
        exposure = exposure.copy()
        exposure["exposure_type"] = exposure["exposure_type"].replace(
            {"currency": "listing_currency"}
        )
    top_holdings = evidence.frame_for(
        PROCESSED / "quantverse_v2_visual_top_holdings.csv"
    )

    row = 3
    _write_excel_table(writer, "VISUAL_ANALYTICS_DASHBOARD", summary, row)
    worksheet.set_row(row, None, header)
    row += max(len(summary), 1) + 3

    worksheet.write(row, 0, "Validation checks", header)
    _write_excel_table(writer, "VISUAL_ANALYTICS_DASHBOARD", validation, row + 1)
    if not validation.empty and not validation["passed"].astype(bool).all():
        worksheet.write(row, 5, "One or more visual checks failed.", warning)
    row += max(len(validation), 1) + 4

    equity_start = row
    _write_excel_table(
        writer,
        "VISUAL_ANALYTICS_DASHBOARD",
        equity[["date", "equity_curve"]] if not equity.empty else equity,
        equity_start,
    )
    if not equity.empty:
        chart = workbook.add_chart({"type": "line"})
        chart.add_series(
            {
                "name": "Equity curve",
                "categories": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    equity_start + 1,
                    0,
                    equity_start + len(equity),
                    0,
                ],
                "values": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    equity_start + 1,
                    1,
                    equity_start + len(equity),
                    1,
                ],
            }
        )
        chart.set_title({"name": "Equity Curve Starts at 1.0"})
        chart.set_y_axis({"name": "Cumulative wealth"})
        worksheet.insert_chart("H4", chart, {"x_scale": 1.2, "y_scale": 1.0})

    drawdown_start = equity_start + max(len(equity), 1) + 3
    _write_excel_table(
        writer,
        "VISUAL_ANALYTICS_DASHBOARD",
        drawdown[["date", "drawdown"]] if not drawdown.empty else drawdown,
        drawdown_start,
    )
    if not drawdown.empty:
        chart = workbook.add_chart({"type": "line"})
        chart.add_series(
            {
                "name": "Drawdown",
                "categories": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    drawdown_start + 1,
                    0,
                    drawdown_start + len(drawdown),
                    0,
                ],
                "values": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    drawdown_start + 1,
                    1,
                    drawdown_start + len(drawdown),
                    1,
                ],
            }
        )
        chart.set_title({"name": "Drawdown Non-Positive"})
        chart.set_y_axis({"name": "Drawdown"})
        worksheet.insert_chart("H20", chart, {"x_scale": 1.2, "y_scale": 1.0})

    risk_start = drawdown_start + max(len(drawdown), 1) + 3
    risk_columns = ["model_name", "risk_x", "return_y"]
    _write_excel_table(
        writer,
        "VISUAL_ANALYTICS_DASHBOARD",
        (
            risk_return[risk_columns]
            if set(risk_columns).issubset(risk_return)
            else risk_return
        ),
        risk_start,
    )
    if not risk_return.empty and set(risk_columns).issubset(risk_return):
        chart = workbook.add_chart({"type": "scatter"})
        chart.add_series(
            {
                "name": "Risk-return",
                "categories": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    risk_start + 1,
                    1,
                    risk_start + len(risk_return),
                    1,
                ],
                "values": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    risk_start + 1,
                    2,
                    risk_start + len(risk_return),
                    2,
                ],
                "marker": {"type": "circle", "size": 6},
                "line": {"none": True},
            }
        )
        chart.set_title({"name": "Risk on X-Axis, Return on Y-Axis"})
        chart.set_x_axis({"name": "Annualized volatility"})
        chart.set_y_axis({"name": "Annualized return"})
        worksheet.insert_chart("H36", chart, {"x_scale": 1.2, "y_scale": 1.0})

    forecast_start = risk_start + max(len(risk_return), 1) + 3
    forecast_columns = ["horizon", "model_mae", "random_walk_mae"]
    _write_excel_table(
        writer,
        "VISUAL_ANALYTICS_DASHBOARD",
        (
            forecast[forecast_columns]
            if set(forecast_columns).issubset(forecast)
            else forecast
        ),
        forecast_start,
    )
    if not forecast.empty and set(forecast_columns).issubset(forecast):
        chart = workbook.add_chart({"type": "column"})
        for col, name in [(1, "Model MAE"), (2, "Random-walk MAE")]:
            chart.add_series(
                {
                    "name": name,
                    "categories": [
                        "VISUAL_ANALYTICS_DASHBOARD",
                        forecast_start + 1,
                        0,
                        forecast_start + len(forecast),
                        0,
                    ],
                    "values": [
                        "VISUAL_ANALYTICS_DASHBOARD",
                        forecast_start + 1,
                        col,
                        forecast_start + len(forecast),
                        col,
                    ],
                }
            )
        chart.set_title({"name": "Forecast Error vs Random Walk"})
        worksheet.insert_chart("H52", chart, {"x_scale": 1.2, "y_scale": 1.0})

    benchmark_start = forecast_start + max(len(forecast), 1) + 3
    if not random_bench.empty:
        bench = random_bench.copy()
        bench["bucket_mid"] = (
            pd.to_numeric(bench["bucket_left"], errors="coerce")
            + pd.to_numeric(bench["bucket_right"], errors="coerce")
        ) / 2
        bench = bench[["bucket_mid", "portfolio_count"]]
    else:
        bench = random_bench
    _write_excel_table(writer, "VISUAL_ANALYTICS_DASHBOARD", bench, benchmark_start)
    if not bench.empty:
        chart = workbook.add_chart({"type": "column"})
        chart.add_series(
            {
                "name": "Random portfolio count",
                "categories": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    benchmark_start + 1,
                    0,
                    benchmark_start + len(bench),
                    0,
                ],
                "values": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    benchmark_start + 1,
                    1,
                    benchmark_start + len(bench),
                    1,
                ],
            }
        )
        chart.set_title({"name": "Random Portfolio Sharpe Distribution"})
        worksheet.insert_chart("H68", chart, {"x_scale": 1.2, "y_scale": 1.0})

    exposure_start = benchmark_start + max(len(bench), 1) + 3
    if not exposure.empty:
        exposure_plot = exposure.loc[
            exposure["exposure_type"].astype(str).eq("region"),
            ["bucket", "weight"],
        ]
        if exposure_plot.empty:
            exposure_plot = exposure[["bucket", "weight"]].head(12)
    else:
        exposure_plot = exposure
    _write_excel_table(
        writer, "VISUAL_ANALYTICS_DASHBOARD", exposure_plot, exposure_start
    )
    if not exposure_plot.empty:
        chart = workbook.add_chart({"type": "bar"})
        chart.add_series(
            {
                "name": "Exposure weight",
                "categories": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    exposure_start + 1,
                    0,
                    exposure_start + len(exposure_plot),
                    0,
                ],
                "values": [
                    "VISUAL_ANALYTICS_DASHBOARD",
                    exposure_start + 1,
                    1,
                    exposure_start + len(exposure_plot),
                    1,
                ],
            }
        )
        chart.set_title({"name": "Exposure Weights Sum to One"})
        worksheet.insert_chart("H84", chart, {"x_scale": 1.2, "y_scale": 1.0})

    holdings_start = exposure_start + max(len(exposure_plot), 1) + 3
    _write_excel_table(
        writer,
        "VISUAL_ANALYTICS_DASHBOARD",
        (
            top_holdings[["ticker", "weight", "rank"]]
            if {"ticker", "weight", "rank"}.issubset(top_holdings)
            else top_holdings
        ),
        holdings_start,
    )


def _write_excel_table(
    writer: pd.ExcelWriter,
    sheet_name: str,
    frame: pd.DataFrame,
    startrow: int,
) -> None:
    safe = (
        frame.copy() if not frame.empty else pd.DataFrame({"status": ["not available"]})
    )
    safe.to_excel(writer, sheet_name=sheet_name, startrow=startrow, index=False)


def _write_selected_stocks_sheet(
    writer: pd.ExcelWriter,
    frame: pd.DataFrame,
) -> None:
    workbook = writer.book
    worksheet = workbook.add_worksheet("SELECTED_STOCKS")
    writer.sheets["SELECTED_STOCKS"] = worksheet
    note = (
        "Listing country is the trading/listing venue; issuer country is the "
        "company domicile; economic country requires explicit business-exposure "
        "metadata and is shown as unavailable when unsupported. Listing currency "
        "is the security trading currency, not necessarily its economic currency risk."
    )
    note_format = workbook.add_format(
        {
            "bg_color": "#FEF3C7",
            "font_color": "#78350F",
            "text_wrap": True,
            "valign": "vcenter",
            "bold": True,
        }
    )
    last_column = max(min(len(frame.columns) - 1, 16), 0)
    worksheet.merge_range(0, 0, 0, last_column, note, note_format)
    worksheet.set_row(0, 48)
    frame.to_excel(writer, sheet_name="SELECTED_STOCKS", startrow=2, index=False)
    worksheet.freeze_panes(3, 2)
    if not frame.empty:
        worksheet.autofilter(2, 0, len(frame) + 2, len(frame.columns) - 1)
    worksheet.set_column("A:A", 12)
    worksheet.set_column("B:B", 32)
    worksheet.set_column("C:D", 18)
    worksheet.set_column("E:K", 20)
    worksheet.set_column("L:Q", 28)


def _start_here() -> list[dict[str, str]]:
    return [
        {
            "section": "What to inspect first",
            "message": "Open EXECUTIVE_DASHBOARD first, then PORTFOLIO, MODEL_DECISIONS, UNCERTAINTY, RISK, AUDIT_FINDINGS and DATA_DICTIONARY. Technical raw sheets follow these reader-facing views.",
        },
        {
            "section": "Trust status",
            "message": "This is public-data research output, not investment advice or institutional PIT evidence.",
        },
        {
            "section": "Blocked claims",
            "message": "Official exact top-100 and institutional point-in-time claims remain unsupported.",
        },
        {
            "section": "Weights",
            "message": "PORTFOLIO and HOLDINGS_DETAIL show the complete final-model holdings with issuer/sector context. FINAL_WEIGHTS contains the full final-model weight vector; ALL_MODEL_WEIGHTS is the technical multi-model matrix.",
        },
        {
            "section": "Return label",
            "message": "The v2 portfolio return field is an annualized arithmetic estimate from realized daily simple returns, not a guaranteed forecast.",
        },
        {
            "section": "Final model selection",
            "message": "MODEL_DECISIONS is the reader view of every promotion gate and rejection reason. MODEL_SELECTION retains the complete technical evidence.",
        },
        {
            "section": "Publish readiness",
            "message": "A complete workbook publication manifest binds this file to one run and SHA-256 hash. Research publish readiness is not institutional portfolio approval.",
        },
        {
            "section": "Exposure metadata",
            "message": "EXPOSURE_METADATA explains whether listing, issuer, economic, sector and industry exposure is usable or diagnostic-only. Listing-country exposure is not issuer-country or economic-country exposure unless explicit metadata is present.",
        },
        {
            "section": "Selected stocks",
            "message": "Use SELECTED_STOCKS for the curated semantic view, SELECTED_METADATA_QUALITY for join/coverage checks and SELECTED_STOCKS_RAW only for unmodified scoring evidence.",
        },
        {
            "section": "Security identity",
            "message": "Read SECURITY_IDENTITY before interpreting returns. A ticker is not a permanent identifier; known reuse, verified listing dates and any history truncation are recorded there.",
        },
        {
            "section": "Short history",
            "message": "FEATURE_ELIGIBILITY shows whether 1M/3M/6M/12M features have enough observations. diagnostic_short_history rows remain visible but cannot enter the standard portfolio selection.",
        },
        {
            "section": "Run consistency",
            "message": "COUNT_RECONCILIATION must pass before selected-stock, forecast, final-holding and walk-forward counts are compared; all core outputs must share one run_id.",
        },
        {
            "section": "Formula and decision traceability",
            "message": "FORMULA_DICTIONARY states the active metric convention and invalidation rule. DECISION_REGISTER records why material methods were chosen and what would reverse each decision.",
        },
        {
            "section": "Country exposure distinction",
            "message": "Use EXPOSURE_LISTING_COUNTRY for listing venue, EXPOSURE_ISSUER_COUNTRY for company domicile and EXPOSURE_ECON_COUNTRY only where economic-risk geography is explicitly available.",
        },
        {
            "section": "Legacy exposure aliases",
            "message": "EXPOSURE_COUNTRY is a legacy listing-country alias and EXPOSURE_CURRENCY is a legacy listing-currency alias; neither is issuer, economic-country or economic-currency exposure.",
        },
    ]


def _summary_rows(evidence: PublicationEvidence) -> list[dict[str, object]]:
    summary = evidence.json_for(PROCESSED / "quantverse_v2_demo_summary.json")
    return [{"metric": key, "value": value} for key, value in summary.items()]


def _appendix(evidence: PublicationEvidence) -> list[dict[str, str]]:
    return [
        {
            "artifact": Path(relative_path).name,
            "path": relative_path,
            "note": "Generated local evidence; not committed.",
        }
        for relative_path in sorted(evidence.frames)
        if relative_path.startswith("data/processed/global_")
        and relative_path.endswith(".csv")
    ]


def _formula_dictionary() -> list[dict[str, str]]:
    return [
        {
            "metric": "simple return",
            "formula": "r_t = adjusted_price_t / adjusted_price_(t-1) - 1",
            "interpretation": "One-period asset return used for portfolio aggregation.",
            "unit_sign": "daily decimal; signed",
            "invalidation": "Unadjusted price, wrong security identity or silent missing value.",
        },
        {
            "metric": "portfolio daily return",
            "formula": "sum_i(lagged_weight_i * simple_return_i)",
            "interpretation": "Simple returns aggregate linearly across lagged portfolio weights.",
            "unit_sign": "daily decimal; signed",
            "invalidation": "Future weights, missing selected return or weight sum != 1.",
        },
        {
            "metric": "Sharpe",
            "formula": (
                "mean(daily_simple_return - compounded_daily_risk_free_hurdle) "
                "* 252 / annualized_volatility"
            ),
            "interpretation": "Arithmetic excess return per unit annualized volatility.",
            "unit_sign": "dimensionless",
            "invalidation": "Risk-free frequency mismatch or zero volatility.",
        },
        {
            "metric": "Sortino",
            "formula": "mean(daily_excess_return) * 252 / annualized_downside_deviation",
            "interpretation": "Excess return relative to downside semideviation.",
            "unit_sign": "dimensionless",
            "invalidation": "No downside observations or hurdle mismatch.",
        },
        {
            "metric": "annualized_return",
            "formula": "mean(daily_simple_return) * 252",
            "interpretation": "Arithmetic annualized estimate, not a guaranteed future return.",
            "unit_sign": "annual decimal; signed",
            "invalidation": "Frequency mismatch or presentation as forecast.",
        },
        {
            "metric": "CAGR",
            "formula": "product(1 + daily_simple_return) ** (252 / observations) - 1",
            "interpretation": "Compounded realized growth over the sample.",
            "unit_sign": "annual decimal; signed",
            "invalidation": "Any return <= -100% or inconsistent sample frequency.",
        },
        {
            "metric": "volatility",
            "formula": "sample_std(daily_simple_return, ddof=1) * sqrt(252)",
            "interpretation": "Annualized dispersion of daily simple returns.",
            "unit_sign": "annual decimal; non-negative",
            "invalidation": "Fewer than two observations or wrong annualization.",
        },
        {
            "metric": "drawdown",
            "formula": "wealth_t / running_max(wealth)_t - 1",
            "interpretation": "Peak-to-trough path loss; values must be non-positive.",
            "unit_sign": "decimal; <= 0",
            "invalidation": "Positive drawdown or non-wealth input.",
        },
        {
            "metric": "VaR/CVaR",
            "formula": "empirical 5th percentile; mean(return <= VaR_95)",
            "interpretation": "Daily historical tail loss metrics; negative values indicate losses.",
            "unit_sign": "daily decimal; loss is negative",
            "invalidation": "Reversed sign, insufficient tail data or parametric relabeling.",
        },
        {
            "metric": "turnover",
            "formula": ("sum_i(abs(target_weight_i,t - drifted_pre_trade_weight_i,t))"),
            "interpretation": (
                "Gross traded notional after the prior target weights drift through "
                "the preceding holding-period returns."
            ),
            "unit_sign": "fraction; non-negative",
            "invalidation": (
                "Target-to-target comparison, omitted exits/entries, missing selected "
                "returns or use of future returns."
            ),
        },
        {
            "metric": "transaction cost",
            "formula": "turnover_t * transaction_cost_bps / 10000",
            "interpretation": "Cost drag deducted from the OOS return path.",
            "unit_sign": "daily decimal drag",
            "invalidation": "Gross path mislabeled net or cost applied twice.",
        },
        {
            "metric": "walk-forward",
            "formula": "train on historical window, test on the next chronological window",
            "interpretation": "Public-data current-universe validation, not institutional point-in-time proof.",
            "unit_sign": "chronological protocol",
            "invalidation": "Overlapping test dates, leakage or test-informed tuning.",
        },
        {
            "metric": "paired block bootstrap",
            "formula": "circular block resample of common-date model and benchmark return pairs",
            "interpretation": "Confidence interval for model-minus-benchmark metric differences.",
            "unit_sign": "metric-difference units",
            "invalidation": "Unpaired samples, different dates or test-driven block tuning.",
        },
        {
            "metric": "random benchmark percentile",
            "formula": "mean(random_metric <= candidate_metric)",
            "interpretation": "Candidate location in a same-protocol constrained random distribution.",
            "unit_sign": "0 to 1",
            "invalidation": "Different dates, universe, constraints, costs or degenerate distribution.",
        },
    ]


def _float(value: object) -> float:
    try:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _first_cell(frame: pd.DataFrame, column: str) -> object:
    if frame.empty or column not in frame:
        return "not available"
    return frame[column].iloc[0]


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    sys.exit(main())
