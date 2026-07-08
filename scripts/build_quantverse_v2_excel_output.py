"""Build QuantVerse v2 explainable Excel workbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_numerical_integrity import (
    validate_v2_numerical_integrity,
)  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "excel" / "quantverse_v2_research_output.xlsx"


SHEETS = {
    "UNIVERSE": "data/universe/current_global_equity_universe.csv",
    "STOCK_SCORES": "data/processed/global_stock_scores.csv",
    "SELECTED_STOCKS": "data/processed/global_stock_scores.csv",
    "RETURN_FORECASTS": "data/processed/global_stock_return_forecasts.csv",
    "MODEL_LEAGUE": "data/processed/global_portfolio_league.csv",
    "FINAL_WEIGHTS": "data/processed/global_portfolio_league_weights.csv",
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
    "EXPOSURE_CURRENCY": "data/processed/global_currency_exposure.csv",
    "EXPOSURE_SECTOR": "data/processed/global_sector_exposure.csv",
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
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    summary = _summary_rows()
    with pd.ExcelWriter(OUTPUT, engine="xlsxwriter") as writer:
        _write_dashboard(writer)
        _write_visual_analytics_dashboard(writer)
        pd.DataFrame(_start_here()).to_excel(
            writer, sheet_name="START_HERE", index=False
        )
        pd.DataFrame(summary).to_excel(
            writer, sheet_name="EXECUTIVE_SUMMARY", index=False
        )
        for sheet, raw_path in SHEETS.items():
            frame = _read_csv(ROOT / raw_path)
            if (
                sheet == "SELECTED_STOCKS"
                and not frame.empty
                and "selection_flag" in frame
            ):
                frame = frame.loc[frame["selection_flag"].astype(bool)]
            frame.to_excel(writer, sheet_name=sheet[:31], index=False)
        pd.DataFrame(_appendix()).to_excel(
            writer, sheet_name="APPENDIX_RAW_TABLES", index=False
        )
        pd.DataFrame(_formula_dictionary()).to_excel(
            writer, sheet_name="APPENDIX_FORMULAS", index=False
        )
    print(f"QuantVerse v2 Excel written: {OUTPUT}")
    return 0


def _write_dashboard(writer: pd.ExcelWriter) -> None:
    summary = _read_json(PROCESSED / "quantverse_v2_demo_summary.json")
    risk = _read_csv(PROCESSED / "global_portfolio_risk_report.csv")
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    integrity = validate_v2_numerical_integrity(ROOT)
    exposure_metadata = _read_csv(PROCESSED / "global_exposure_metadata_quality.csv")
    final_model = str(summary.get("final_selected_model", "not available"))
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
                "value": integrity["overall_status"],
            },
            {
                "metric": "numerical_integrity_failed_checks",
                "value": integrity["failed_check_count"],
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
                "metric": "issuer_country_coverage_ratio",
                "value": summary.get(
                    "issuer_country_coverage_ratio",
                    _first_cell(exposure_metadata, "issuer_country_coverage_ratio"),
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
    if integrity["overall_status"] != "passed":
        worksheet.write(13, 1, integrity["overall_status"], warning)

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


def _write_visual_analytics_dashboard(writer: pd.ExcelWriter) -> None:
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

    worksheet.write(0, 0, "QuantVerse v2 Visual Portfolio Analytics", title)
    worksheet.write(
        1,
        0,
        "All charts are diagnostic public-data research views. They do not create a new model or investment recommendation.",
        note,
    )
    worksheet.set_column("A:A", 24)
    worksheet.set_column("B:F", 22)

    summary = _read_csv(PROCESSED / "quantverse_v2_visual_analytics_summary.csv")
    validation = _read_csv(PROCESSED / "quantverse_v2_visual_validation.csv")
    equity = _read_csv(PROCESSED / "quantverse_v2_visual_equity_curve.csv").tail(260)
    drawdown = _read_csv(PROCESSED / "quantverse_v2_visual_drawdown_curve.csv").tail(
        260
    )
    risk_return = _read_csv(PROCESSED / "quantverse_v2_visual_model_risk_return.csv")
    forecast = _read_csv(PROCESSED / "quantverse_v2_visual_forecast_error.csv")
    random_bench = _read_csv(PROCESSED / "quantverse_v2_visual_random_benchmark.csv")
    exposure = _read_csv(PROCESSED / "quantverse_v2_visual_exposure.csv")
    top_holdings = _read_csv(PROCESSED / "quantverse_v2_visual_top_holdings.csv")

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


def _start_here() -> list[dict[str, str]]:
    return [
        {
            "section": "What to inspect first",
            "message": "Read EXECUTIVE_SUMMARY, MODEL_SELECTION, FINAL_WEIGHTS, RISK_METRICS, RANDOM_PERCENTILES, ROBUSTNESS, FORECAST_VALIDATION and TOP_HOLDINGS_EXPLANATION before raw tables.",
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
            "message": "Full model weights are in FINAL_WEIGHTS; final model is reported in EXECUTIVE_SUMMARY.",
        },
        {
            "section": "Return label",
            "message": "The v2 portfolio return field is an annualized arithmetic estimate from realized daily simple returns, not a guaranteed forecast.",
        },
        {
            "section": "Final model selection",
            "message": "MODEL_SELECTION explains why the final public-data model is chosen; blocked and diagnostic models are not eligible final models.",
        },
        {
            "section": "Publish readiness",
            "message": "PUBLISH_READINESS is evidence for GitHub/CV discussion only; it is not a promoted institutional portfolio approval.",
        },
        {
            "section": "Exposure metadata",
            "message": "EXPOSURE_METADATA explains whether country/sector exposure is complete or diagnostic-only. Listing-country exposure is not issuer-country exposure unless issuer metadata is present.",
        },
    ]


def _summary_rows() -> list[dict[str, object]]:
    summary = _read_json(PROCESSED / "quantverse_v2_demo_summary.json")
    return [{"metric": key, "value": value} for key, value in summary.items()]


def _appendix() -> list[dict[str, str]]:
    return [
        {
            "artifact": path.name,
            "path": str(path),
            "note": "Generated local evidence; not committed.",
        }
        for path in sorted(PROCESSED.glob("global_*.csv"))
    ]


def _formula_dictionary() -> list[dict[str, str]]:
    return [
        {
            "metric": "portfolio daily return",
            "formula": "sum_i(weight_i * simple_return_i)",
            "interpretation": "Simple returns aggregate linearly across portfolio weights for one period.",
        },
        {
            "metric": "Sharpe",
            "formula": "(annualized_return - risk_free_rate) / annualized_volatility",
            "interpretation": "Return per unit risk; current v2 output uses zero risk-free assumption unless configured otherwise.",
        },
        {
            "metric": "annualized_return",
            "formula": "mean(daily_simple_return) * 252",
            "interpretation": "Arithmetic annualized estimate, not a guaranteed future return.",
        },
        {
            "metric": "CAGR",
            "formula": "(1 + total_return) ** (252 / observations) - 1",
            "interpretation": "Compounded realized growth over the sample.",
        },
        {
            "metric": "volatility",
            "formula": "std(daily_simple_return) * sqrt(252)",
            "interpretation": "Annualized dispersion of daily simple returns.",
        },
        {
            "metric": "VaR/CVaR",
            "formula": "5th percentile and mean below that percentile",
            "interpretation": "Daily historical tail loss metrics; negative values indicate losses.",
        },
        {
            "metric": "walk-forward",
            "formula": "train on historical window, test on the next chronological window",
            "interpretation": "Public-data current-universe validation, not institutional point-in-time proof.",
        },
    ]


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    sys.exit(main())
