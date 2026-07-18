"""Build the QuantVerse v2 research PDF and HTML report."""

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
from project.reporting.selected_stock_report_view import (  # noqa: E402
    write_selected_stock_report_artifacts,
)

PROCESSED = ROOT / "data" / "processed"
OUTPUT_PDF = ROOT / "output" / "pdf" / "quantverse_v2_research_report.pdf"
OUTPUT_HTML = ROOT / "output" / "html" / "quantverse_v2_research_report.html"


def main() -> int:
    sections = _sections()
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    _write_pdf(sections)
    _write_html(sections)
    print(f"QuantVerse v2 research PDF written: {OUTPUT_PDF}")
    print(f"QuantVerse v2 research HTML written: {OUTPUT_HTML}")
    return 0


def _sections() -> list[dict[str, object]]:
    summary = _read_json(PROCESSED / "quantverse_v2_demo_summary.json")
    decision = _read_json(PROCESSED / "global_master_decision_summary.json")
    scores = _read_csv(PROCESSED / "global_stock_scores.csv")
    forecasts = _read_csv(PROCESSED / "global_stock_return_forecasts.csv")
    league = _read_csv(PROCESSED / "global_portfolio_league.csv")
    risk = _read_csv(PROCESSED / "global_portfolio_risk_report.csv")
    walk = _read_csv(PROCESSED / "global_walk_forward_model_comparison.csv")
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    leakage = _read_csv(PROCESSED / "global_walk_forward_leakage_audit.csv")
    sanity = _read_csv(PROCESSED / "global_risk_metric_sanity_checks.csv")
    model_selection = _read_csv(PROCESSED / "global_model_selection_report.csv")
    model_selection_diagnostics = _read_csv(
        PROCESSED / "global_model_selection_diagnostics.csv"
    )
    random_percentiles = _read_csv(
        PROCESSED / "global_random_portfolio_percentile_report.csv"
    )
    robustness = _read_csv(PROCESSED / "global_robustness_sensitivity.csv")
    model_stability = _read_csv(PROCESSED / "global_model_stability_report.csv")
    exposure_region = _read_csv(PROCESSED / "global_region_exposure.csv")
    exposure_listing_country = _read_csv(
        PROCESSED / "global_listing_country_exposure.csv"
    )
    exposure_issuer_country = _read_csv(
        PROCESSED / "global_issuer_country_exposure.csv"
    )
    exposure_economic_country = _read_csv(
        PROCESSED / "global_economic_country_exposure.csv"
    )
    exposure_warnings = _read_csv(PROCESSED / "global_exposure_warnings.csv")
    exposure_metadata = _read_csv(PROCESSED / "global_exposure_metadata_quality.csv")
    top_holdings = _read_csv(PROCESSED / "global_top_holdings_explanation.csv")
    universe = _read_csv(
        ROOT / "data" / "universe" / "current_global_equity_universe.csv"
    )
    forecast_validation = _read_csv(
        PROCESSED / "global_forecast_validation_by_horizon.csv"
    )
    visual_summary = _read_csv(PROCESSED / "quantverse_v2_visual_analytics_summary.csv")
    visual_equity = _read_csv(PROCESSED / "quantverse_v2_visual_equity_curve.csv")
    visual_drawdown = _read_csv(PROCESSED / "quantverse_v2_visual_drawdown_curve.csv")
    visual_risk_return = _read_csv(
        PROCESSED / "quantverse_v2_visual_model_risk_return.csv"
    )
    visual_forecast = _read_csv(PROCESSED / "quantverse_v2_visual_forecast_error.csv")
    visual_random = _read_csv(PROCESSED / "quantverse_v2_visual_random_benchmark.csv")
    visual_exposure = _read_csv(PROCESSED / "quantverse_v2_visual_exposure.csv")
    if not visual_exposure.empty and "exposure_type" in visual_exposure:
        visual_exposure = visual_exposure.copy()
        visual_exposure["exposure_type"] = visual_exposure["exposure_type"].replace(
            {"currency": "listing_currency"}
        )
    visual_top_holdings = _read_csv(PROCESSED / "quantverse_v2_visual_top_holdings.csv")
    visual_validation = _read_csv(PROCESSED / "quantverse_v2_visual_validation.csv")
    integrity = validate_v2_numerical_integrity(ROOT)
    integrity_checks = pd.DataFrame(integrity["checks"])
    selected, selected_quality = write_selected_stock_report_artifacts(
        scores,
        top_holdings,
        PROCESSED,
        universe,
    )
    security_identity = _read_csv(PROCESSED / "global_security_identity_audit.csv")
    feature_eligibility = _read_csv(
        PROCESSED / "global_feature_history_eligibility.csv"
    )
    count_reconciliation = _read_csv(
        PROCESSED / "global_cross_artifact_count_reconciliation.csv"
    )
    final_model = str(summary.get("final_selected_model", "Policy Constrained"))
    final_weights = (
        weights.loc[weights["model_name"].astype(str).eq(final_model)]
        if not weights.empty and "model_name" in weights
        else pd.DataFrame()
    )
    return [
        {
            "title": "Executive Summary",
            "bullets": [
                "QuantVerse v2 is a public-data global equity research platform, not investment advice.",
                f"Final public-data research model: {summary.get('final_public_data_research_model', summary.get('final_selected_model', 'not available'))}.",
                f"Institutional/global master promotion: {summary.get('institutional_global_master_promotion', summary.get('promotion_decision', 'not available'))}.",
                f"Promotion decision: {summary.get('promotion_decision', decision.get('promotion_decision', 'not available'))}.",
                f"Numerical integrity: {summary.get('numerical_integrity_status', 'not available')}; failed checks: {summary.get('numerical_integrity_failed_checks', 'not available')}.",
                f"Exposure metadata: {summary.get('exposure_metadata_status', 'not available')}; sector coverage: {summary.get('sector_coverage_ratio', 'not available')}; industry coverage: {summary.get('industry_coverage_ratio', 'not available')}; issuer-country coverage: {summary.get('issuer_country_coverage_ratio', 'not available')}; economic-country coverage: {summary.get('economic_country_coverage_ratio', 'not available')}.",
                f"Universe rows: {summary.get('universe_rows', 'not available')}; assets with returns: {summary.get('assets_with_returns', 'not available')}.",
                f"Security identity status: {summary.get('security_identity_status', 'not available')}; short-history diagnostics: {summary.get('short_history_diagnostic_count', 'not available')}.",
                f"Cross-artifact reconciliation: {summary.get('cross_artifact_reconciliation_status', 'not available')}; run_id: {summary.get('run_id', 'not available')}.",
                "Exact official top-100 and institutional point-in-time claims remain unsupported.",
            ],
            "chart": {
                "labels": ["Scored", "Selected", "League models"],
                "values": [
                    float(summary.get("stocks_scored", len(scores))),
                    float(summary.get("stocks_selected", len(selected))),
                    float(summary.get("models_in_league", len(league))),
                ],
            },
        },
        _stock_scoring_section(selected, selected_quality),
        {
            "title": "Security Identity and History Eligibility",
            "bullets": [
                "A ticker is a routing label, not a permanent security identifier; known symbol reuse requires an official listing boundary.",
                "Standard composite scoring requires 252 valid daily returns so 12-month momentum and volatility are not computed from a shorter sample.",
                "Short-history securities remain visible as diagnostic_short_history but are excluded from standard selection, forecasts and portfolio inputs.",
                "SPCX is a verified ticker-reuse case: the current SpaceX security starts on 2026-06-12 and prior SPCX data must not be linked to it.",
                "Cross-artifact counts and run IDs must reconcile before the report package is considered valid.",
            ],
            "table": (
                security_identity.loc[
                    security_identity["ticker"].astype(str).eq("SPCX")
                ].head(5)
                if not security_identity.empty and "ticker" in security_identity
                else feature_eligibility.head(10)
            ),
            "pdf_columns": [
                "ticker",
                "current_listing_start_date",
                "first_valid_return_date",
                "observed_return_count",
                "history_contamination_status",
                "eligibility_status",
            ],
            "chart": {
                "labels": ["Standard eligible", "Short-history diagnostic"],
                "values": [
                    float(
                        feature_eligibility.get(
                            "standard_composite_score_eligible",
                            pd.Series(dtype=bool),
                        )
                        .map(_as_bool)
                        .sum()
                    ),
                    float(
                        feature_eligibility.get(
                            "eligibility_status", pd.Series(dtype=str)
                        )
                        .astype(str)
                        .eq("diagnostic_short_history")
                        .sum()
                    ),
                ],
            },
        },
        {
            "title": "Cross-Artifact Count Reconciliation",
            "bullets": [
                "Selected-stock, forecast, portfolio-holding and walk-forward counts are different analytical stages and are reconciled under one run identity.",
                "An unexplained same-run count mismatch invalidates the report package; a configured holding cap is accepted only when the relationship is explicit.",
                "The run_id, data as-of date and universe snapshot prevent stale artifacts from being compared as if they came from one execution.",
            ],
            "table": count_reconciliation.head(12),
        },
        {
            "title": "Expected Return Forecasts",
            "bullets": [
                "Random-walk expected return is the mandatory baseline.",
                "Momentum, mean-reversion, rolling mean and ridge diagnostics feed an ensemble expected return.",
                "Prediction intervals widen and confidence falls when history is short or volatility is high.",
            ],
            "table": forecasts.head(12),
        },
        {
            "title": "Portfolio Model League",
            "bullets": [
                "Every requested model appears with explicit status.",
                "Black-Litterman uses public-provider current market caps only as diagnostic priors.",
                "Models with missing prerequisites remain blocked or diagnostic; they are not hidden.",
            ],
            "table": league.head(14),
        },
        {
            "title": "Final Weights and Risk",
            "bullets": [
                f"Final selected model: {final_model}.",
                f"Final weight sum: {summary.get('weight_sum', 'not available')}.",
                "Return label: "
                + str(summary.get("expected_portfolio_return_label", "not available")),
                f"Annualized realized return estimate: {summary.get('expected_portfolio_return', 'not available')}.",
                f"Return warning: {summary.get('expected_portfolio_return_warning', 'not available')}.",
                f"Annualized volatility: {summary.get('expected_portfolio_volatility', 'not available')}.",
                f"Daily historical CVaR: {summary.get('expected_portfolio_cvar', 'not available')}.",
            ],
            "table": (
                final_weights.head(15) if not final_weights.empty else risk.head(10)
            ),
        },
        {
            "title": "Robust Model Selection Rationale",
            "bullets": [
                "The final model is selected by book-grounded walk-forward evidence, not by highest in-sample return alone.",
                "Risk-adjusted performance is return per unit risk: Sharpe, Sortino and Calmar are higher-is-better ratios when inputs are valid.",
                "Equal Weight is a benchmark, not an automatic winner; an active model can become the final public-data research model when it clears risk-adjusted gates.",
                f"Selection method: {summary.get('final_model_selection_method', 'not available')}.",
                f"Selection score: {summary.get('final_model_selection_score', 'not available')}.",
                f"Selection decision: {summary.get('final_model_selection_decision', 'not promoted')}.",
                f"Selection reason: {summary.get('final_model_selection_reason', 'not available')}.",
                "Diagnostic, blocked and future-candidate models are excluded from final selection.",
            ],
            "table": (
                model_selection_diagnostics.head(12)
                if not model_selection_diagnostics.empty
                else model_selection.head(12)
            ),
        },
        {
            "title": "Benchmark and Random Portfolio Context",
            "bullets": [
                "Equal Weight remains the hard benchmark.",
                "Random portfolios obey the same selected universe and max-weight constraint.",
                f"Final random Sharpe percentile: {summary.get('random_portfolio_percentile', 'not available')}.",
                "Random percentile is benchmark context, not proof of future superiority.",
            ],
            "table": random_percentiles.head(12),
        },
        {
            "title": "Robustness and Sensitivity",
            "bullets": [
                f"Robustness status: {summary.get('robustness_status', 'not available')}.",
                f"Sensitivity status: {summary.get('sensitivity_status', 'not available')}.",
                "Sensitivity varies max assets, max weight, transaction costs and random seeds on a bounded grid.",
                "If model choice changes across this grid, that fragility is a limitation rather than a hidden detail.",
            ],
            "table": (
                model_stability.head(10)
                if not model_stability.empty
                else robustness.head(10)
            ),
        },
        {
            "title": "Forecast Validation",
            "bullets": [
                f"Forecast validation status: {summary.get('forecast_validation_status', 'not available')}.",
                "Forecasts are compared with a random-walk baseline.",
                "Forecast outputs remain diagnostic unless they improve net portfolio decision quality after costs and risk.",
            ],
            "table": forecast_validation.head(12),
        },
        {
            "title": "Visual Portfolio Analytics",
            "bullets": [
                "This section is chart-led evidence for the existing v2 final model; it does not add a new portfolio model.",
                "Each chart-ready output includes formula/method, source basis, limitation and invalidation condition.",
                "Output status remains diagnostic public-data research unless promotion gates and public-data limitations are resolved.",
                "Validator file: data/processed/quantverse_v2_visual_validation.csv.",
            ],
            "table": (
                visual_summary.head(12)
                if not visual_summary.empty
                else visual_validation.head(12)
            ),
        },
        {
            "title": "Equity Curve and Drawdown",
            "bullets": [
                "Formula: equity_t = product(1 + daily simple portfolio return), normalized so the first point equals 1.0.",
                "Drawdown formula: equity_t / running peak equity_t - 1; valid drawdown values must be less than or equal to zero.",
                "Interpretation: the chart shows realized path dependence and peak-to-trough loss risk for the final model.",
                "Invalidation: a non-1.0 starting equity curve, positive drawdown, non-simple returns or silent missing-return treatment invalidates the chart.",
            ],
            "table": (
                visual_equity.tail(8)
                if not visual_equity.empty
                else visual_drawdown.tail(8)
            ),
        },
        {
            "title": "Model Risk-Return Map",
            "bullets": [
                "Formula: x-axis is annualized volatility and y-axis is annualized return.",
                "Interpretation: the model set is compared by return per unit risk, not by return alone.",
                "Limitation: these are public-data research metrics, not institutional point-in-time proof.",
                "Invalidation: reversed axes, in-sample-only evidence or unflagged extreme metrics invalidate the chart.",
            ],
            "table": visual_risk_return.head(12),
        },
        {
            "title": "Forecast Error Versus Random Walk",
            "bullets": [
                "Formula: model MAE is compared against random-walk MAE for each horizon.",
                "Interpretation: forecasts remain diagnostic unless they beat a naive benchmark and improve net portfolio decisions.",
                "Limitation: low forecast error alone is not a portfolio promotion gate.",
                "Invalidation: missing random-walk comparator, horizon mismatch or wrong target scale invalidates the chart.",
            ],
            "table": visual_forecast.head(12),
        },
        {
            "title": "Random Benchmark Distribution",
            "bullets": [
                "Formula: histogram of random portfolio Sharpe values under the same selected universe and constraint family.",
                "Interpretation: the final model percentile is benchmark context and not a future performance guarantee.",
                "Limitation: the benchmark is only meaningful if the random distribution is not degenerate.",
                "Invalidation: zero variance random outcomes or different constraints invalidate comparison.",
            ],
            "chart": (
                {
                    "labels": visual_random["bucket_left"]
                    .head(8)
                    .round(3)
                    .astype(str)
                    .tolist(),
                    "values": visual_random["portfolio_count"]
                    .head(8)
                    .astype(float)
                    .tolist(),
                }
                if not visual_random.empty
                and {"bucket_left", "portfolio_count"}.issubset(visual_random)
                else None
            ),
            "table": visual_random.head(12),
        },
        {
            "title": "Exposure and Concentration",
            "bullets": [
                "Formula: grouped final model weights by region, listing country, issuer country, economic country, listing currency, exchange, sector, industry and sleeve; each exposure type must sum to 1.0.",
                "Listing exposure means where the ticker is traded/listed.",
                "Issuer exposure means where the company/entity is domiciled.",
                "Economic exposure means where business risk is economically concentrated when explicit metadata is available.",
                "Interpretation: concentration risk is an economic and governance issue, not only a visual issue.",
                "Limitation: public-source listing, issuer, economic, listing-currency, sector and industry mappings may be incomplete; listing currency is not necessarily economic currency risk.",
                "Invalidation: exposure totals that do not reconcile to one invalidate the chart.",
            ],
            "table": (
                visual_exposure.head(12)
                if not visual_exposure.empty
                else visual_top_holdings.head(12)
            ),
        },
        {
            "title": "Economic Exposure Interpretation",
            "bullets": [
                "A final model must be economically interpretable, not only mathematically optimized.",
                f"Exposure warnings: {summary.get('exposure_warnings', 'not available')}.",
                f"Exposure metadata status: {summary.get('exposure_metadata_status', 'not available')}.",
                f"Sector coverage ratio: {summary.get('sector_coverage_ratio', 'not available')}.",
                f"Industry coverage ratio: {summary.get('industry_coverage_ratio', 'not available')}.",
                f"Listing-country coverage ratio: {summary.get('listing_country_coverage_ratio', 'not available')}.",
                f"Issuer-country coverage ratio: {summary.get('issuer_country_coverage_ratio', 'not available')}.",
                f"Economic-country coverage ratio: {summary.get('economic_country_coverage_ratio', 'not available')}.",
                "If issuer-country metadata is missing, only listing-country exposure is available and it remains diagnostic.",
                "If economic-country metadata is unavailable, economic exposure is unavailable; it is not inferred from listing venue, listing currency or issuer domicile.",
                "ADR/foreign issuer cases are flagged so US-listed/USD tickers are not treated as pure United States issuer exposure by default.",
                "Region, listing-country, issuer-country, economic-country, listing-currency, exchange, sleeve, sector and industry exposure reports are generated separately.",
            ],
            "table": (
                exposure_metadata.head(12)
                if not exposure_metadata.empty
                else (
                    pd.concat(
                        [
                            _tag_exposure(exposure_listing_country, "listing_country"),
                            _tag_exposure(exposure_issuer_country, "issuer_country"),
                            _tag_exposure(
                                exposure_economic_country, "economic_country"
                            ),
                        ],
                        ignore_index=True,
                    ).head(12)
                    if not exposure_listing_country.empty
                    or not exposure_issuer_country.empty
                    or not exposure_economic_country.empty
                    else (
                        top_holdings.head(12)
                        if not top_holdings.empty
                        else (
                            exposure_region.head(12)
                            if not exposure_region.empty
                            else exposure_warnings.head(12)
                        )
                    )
                )
            ),
        },
        {
            "title": "Walk-Forward Validation",
            "bullets": [
                "Walk-forward uses chronological train and next-period test windows.",
                "Because point-in-time membership is unavailable, this is a current-universe public-data walk-forward, not an institutional PIT backtest.",
                f"Walk-forward status: {summary.get('walk_forward_status', 'not available')}.",
                f"Leakage audit passed: {summary.get('walk_forward_leakage_audit_passed', 'not available')}.",
                f"Transaction-cost status: {summary.get('transaction_cost_status', 'not available')}.",
            ],
            "table": walk.head(12),
        },
        {
            "title": "Sanity Checks and Claim Controls",
            "bullets": [
                f"Risk metric sanity passed: {summary.get('risk_metric_sanity_passed', 'not available')}.",
                f"Numerical integrity status: {integrity.get('overall_status', 'not available')}.",
                f"Numerical integrity failed checks: {integrity.get('failed_check_count', 'not available')}.",
                f"Random portfolio percentile: {summary.get('random_portfolio_percentile', 'not available')}.",
                f"Publish-readiness status: {summary.get('publish_readiness_status', 'not available')}.",
                "Extreme return and risk metric values are warnings requiring review, not success claims.",
            ],
            "table": (
                integrity_checks.head(12)
                if not integrity_checks.empty
                else (leakage.head(12) if not leakage.empty else sanity.head(12))
            ),
        },
        {
            "title": "CV/GitHub Interpretation",
            "bullets": [
                "The project demonstrates data engineering, FX-normalized returns, portfolio optimization, risk analytics and validation discipline.",
                "It does not claim official exact top-100 coverage, alpha guarantees, live trading readiness or investment advice.",
                "A recruiter should see a working quant research engine with explicit claim guards.",
            ],
        },
        {
            "title": "Limitations",
            "bullets": [
                "The active global master portfolio promotion decision remains not promoted.",
                "Official exact top-100 membership, point-in-time constituents, delisting evidence and institutional corporate-action reconciliation remain unresolved.",
                "Public-data current-universe walk-forward validation is useful research evidence, not an institutional PIT backtest.",
                "Extreme return, CAGR and Sharpe estimates are warning flags requiring review, not success claims.",
            ],
        },
    ]


def _write_pdf(sections: list[dict[str, object]]) -> None:
    from xml.sax.saxutils import escape

    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    table_header_style = ParagraphStyle(
        "QuantVerseTableHeader",
        parent=styles["BodyText"],
        fontSize=5.5,
        leading=6.5,
        textColor=colors.white,
    )
    table_cell_style = ParagraphStyle(
        "QuantVerseTableCell",
        parent=styles["BodyText"],
        fontSize=5.5,
        leading=6.5,
    )
    available_width = A4[0] - 144
    story = [Paragraph("QuantVerse v2 Public-Data Research Report", styles["Title"])]
    for section in sections:
        story.append(Spacer(1, 10))
        story.append(Paragraph(str(section["title"]), styles["Heading1"]))
        for bullet in section.get("bullets", []):
            story.append(Paragraph("- " + str(bullet), styles["BodyText"]))
        chart = section.get("chart")
        if isinstance(chart, dict):
            story.append(_chart(chart, VerticalBarChart, Drawing, String, colors))
        table = section.get("table")
        if isinstance(table, pd.DataFrame) and not table.empty:
            requested_columns = [
                column
                for column in section.get("pdf_columns", [])
                if column in table.columns
            ]
            selected_table = table[requested_columns] if requested_columns else table
            small = selected_table.head(12).iloc[:, :8].astype(str)
            data = [
                [
                    Paragraph(escape(str(column)), table_header_style)
                    for column in small.columns
                ]
            ]
            data.extend(
                [
                    [Paragraph(escape(str(value)), table_cell_style) for value in row]
                    for row in small.values.tolist()
                ]
            )
            column_width = available_width / max(len(small.columns), 1)
            rendered = Table(
                data,
                repeatRows=1,
                colWidths=[column_width] * len(small.columns),
            )
            rendered.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(Spacer(1, 5))
            story.append(rendered)
    doc = SimpleDocTemplate(str(OUTPUT_PDF), pagesize=A4)
    doc.build(story)


def _chart(config: dict, chart_cls, drawing_cls, string_cls, colors):
    labels = [str(value) for value in config.get("labels", [])]
    values = [float(value) for value in config.get("values", [])]
    drawing = drawing_cls(460, 165)
    chart = chart_cls()
    chart.x = 40
    chart.y = 45
    chart.height = 85
    chart.width = 360
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 25
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(max(values or [1.0]), 1.0) * 1.25
    chart.bars[0].fillColor = colors.HexColor("#1f77b4")
    drawing.add(chart)
    for idx, value in enumerate(values):
        drawing.add(string_cls(55 + idx * 110, 138, f"{value:g}", fontSize=8))
    return drawing


def _tag_exposure(frame: pd.DataFrame, exposure_type: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    tagged = frame.copy()
    tagged.insert(0, "exposure_type", exposure_type)
    return tagged


def _stock_scoring_section(
    selected: pd.DataFrame,
    selected_quality: pd.DataFrame,
) -> dict[str, object]:
    display = selected.copy()
    if "selection_rank" in display:
        display["selection_rank"] = pd.to_numeric(
            display["selection_rank"], errors="coerce"
        ).astype("Int64")
    if "composite_quant_score" in display:
        display["composite_quant_score"] = pd.to_numeric(
            display["composite_quant_score"], errors="coerce"
        ).round(4)
    bullets = [
        "Scores combine coverage, market-cap liquidity proxy, momentum, risk-adjusted return, drawdown penalty and diversification.",
        "Simple returns are used for portfolio aggregation; log returns remain diagnostic.",
        "Scores are deterministic public-data research signals and are not buy recommendations.",
        "Listing country identifies where the security is traded. Issuer country identifies the company's domicile. Economic-country exposure is unavailable unless explicit supported business-exposure metadata exists.",
    ]
    economic_coverage = (
        _float(selected_quality["economic_country_coverage_ratio"].iloc[0])
        if not selected_quality.empty
        and "economic_country_coverage_ratio" in selected_quality
        else 0.0
    )
    if economic_coverage == 0.0:
        bullets.append(
            "Economic-country exposure is unavailable and is not inferred from listing venue, trading currency or issuer domicile."
        )
    return {
        "title": "Stock Scoring Methodology",
        "bullets": bullets,
        "table": display,
        "table_id": "selected-stock-semantic-view",
        "pdf_columns": [
            "ticker",
            "selection_rank",
            "composite_quant_score",
            "listing_country",
            "issuer_country",
            "economic_country",
            "listing_currency",
            "metadata_confidence",
        ],
    }


def _write_html(sections: list[dict[str, object]]) -> None:
    parts = [
        "<html><head><meta charset='utf-8'><title>QuantVerse v2 Research Report</title>",
        "<style>body{font-family:Arial,sans-serif;max-width:1100px;margin:40px auto;line-height:1.45}table{border-collapse:collapse;font-size:12px}td,th{border:1px solid #ccc;padding:4px}th{background:#1f2937;color:white}</style>",
        "</head><body><h1>QuantVerse v2 Public-Data Research Report</h1>",
    ]
    for section in sections:
        parts.append(f"<h2>{section['title']}</h2>")
        for bullet in section.get("bullets", []):
            parts.append(f"<p>{bullet}</p>")
        table = section.get("table")
        if isinstance(table, pd.DataFrame) and not table.empty:
            parts.append(
                table.head(20).to_html(
                    index=False,
                    table_id=str(section.get("table_id", "")) or None,
                )
            )
    parts.append("</body></html>")
    OUTPUT_HTML.write_text("\n".join(parts), encoding="utf-8")


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


def _as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    sys.exit(main())
