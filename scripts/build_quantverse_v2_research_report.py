"""Build the QuantVerse v2 research PDF and HTML report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
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
    random_percentiles = _read_csv(
        PROCESSED / "global_random_portfolio_percentile_report.csv"
    )
    robustness = _read_csv(PROCESSED / "global_robustness_sensitivity.csv")
    model_stability = _read_csv(PROCESSED / "global_model_stability_report.csv")
    exposure_region = _read_csv(PROCESSED / "global_region_exposure.csv")
    exposure_warnings = _read_csv(PROCESSED / "global_exposure_warnings.csv")
    top_holdings = _read_csv(PROCESSED / "global_top_holdings_explanation.csv")
    forecast_validation = _read_csv(
        PROCESSED / "global_forecast_validation_by_horizon.csv"
    )
    selected = (
        scores.loc[scores["selection_flag"].astype(bool)]
        if not scores.empty and "selection_flag" in scores
        else scores.head(0)
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
                f"Promotion decision: {summary.get('promotion_decision', decision.get('promotion_decision', 'not available'))}.",
                f"Universe rows: {summary.get('universe_rows', 'not available')}; assets with returns: {summary.get('assets_with_returns', 'not available')}.",
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
        {
            "title": "Stock Scoring Methodology",
            "bullets": [
                "Scores combine coverage, market-cap liquidity proxy, momentum, risk-adjusted return, drawdown penalty and diversification.",
                "Simple returns are used for portfolio aggregation; log returns remain diagnostic.",
                "Scores are deterministic public-data research signals and are not buy recommendations.",
            ],
            "table": selected.head(12),
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
                "The final model is selected by an evidence gate, not by highest in-sample return alone.",
                f"Selection method: {summary.get('final_model_selection_method', 'not available')}.",
                f"Selection score: {summary.get('final_model_selection_score', 'not available')}.",
                f"Selection decision: {summary.get('final_model_selection_decision', 'not promoted')}.",
                f"Selection reason: {summary.get('final_model_selection_reason', 'not available')}.",
                "Diagnostic, blocked and future-candidate models are excluded from final selection.",
            ],
            "table": model_selection.head(12),
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
            "title": "Economic Exposure Interpretation",
            "bullets": [
                "A final model must be economically interpretable, not only mathematically optimized.",
                f"Exposure warnings: {summary.get('exposure_warnings', 'not available')}.",
                "Region, country, currency, sleeve and sector exposure reports are generated separately.",
            ],
            "table": (
                top_holdings.head(12)
                if not top_holdings.empty
                else (
                    exposure_region.head(12)
                    if not exposure_region.empty
                    else exposure_warnings.head(12)
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
                f"Random portfolio percentile: {summary.get('random_portfolio_percentile', 'not available')}.",
                f"Publish-readiness status: {summary.get('publish_readiness_status', 'not available')}.",
                "Extreme return/risk values are warnings requiring review, not success claims.",
            ],
            "table": leakage.head(12) if not leakage.empty else sanity.head(12),
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
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
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
            small = table.head(12).iloc[:, :8].astype(str)
            data = [small.columns.tolist()] + small.values.tolist()
            rendered = Table(data, repeatRows=1)
            rendered.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 6),
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
    chart.valueAxis.valueMax = max(values or [1]) * 1.25
    chart.bars[0].fillColor = colors.HexColor("#1f77b4")
    drawing.add(chart)
    for idx, value in enumerate(values):
        drawing.add(string_cls(55 + idx * 110, 138, f"{value:g}", fontSize=8))
    return drawing


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
            parts.append(table.head(20).to_html(index=False))
    parts.append("</body></html>")
    OUTPUT_HTML.write_text("\n".join(parts), encoding="utf-8")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
