"""Build real global stock master report and presentation PDF artifacts."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

PROCESSED = Path("data/processed")
REPORT_MD = Path("output/reports/quantverse_real_global_stock_master_report.md")
REPORT_PDF = Path("output/pdf/quantverse_real_global_stock_master_report.pdf")
PRESENTATION_MD = Path(
    "output/reports/quantverse_real_global_stock_master_presentation.md"
)
PRESENTATION_PDF = Path(
    "output/pdf/quantverse_real_global_stock_master_presentation.pdf"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROCESSED))
    parser.add_argument("--report-md", default=str(REPORT_MD))
    parser.add_argument("--report-pdf", default=str(REPORT_PDF))
    parser.add_argument("--presentation-md", default=str(PRESENTATION_MD))
    parser.add_argument("--presentation-pdf", default=str(PRESENTATION_PDF))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed = Path(args.processed_dir)
    report = _build_report(processed)
    presentation = _build_presentation(processed)
    _write_text(Path(args.report_md), report)
    _write_text(Path(args.presentation_md), presentation)
    _markdown_to_pdf(
        report, Path(args.report_pdf), "QuantVerse Real Global Stock Master Report"
    )
    _markdown_to_pdf(
        presentation,
        Path(args.presentation_pdf),
        "QuantVerse Real Global Stock Master Presentation",
        pagesize=landscape(A4),
        page_break_on_h2=True,
    )
    print(f"Report written: {args.report_pdf}")
    print(f"Presentation written: {args.presentation_pdf}")
    return 0


def _build_report(processed: Path) -> str:
    decision = _read_json(processed / "global_master_decision_summary.json")
    returns_status = _read_json(processed / "global_returns_matrix_status.json")
    universe_summary = _read_csv(
        processed / "real_global_universe_population_summary.csv"
    )
    source_coverage = _read_csv(processed / "real_global_universe_source_coverage.csv")
    market_caps = _read_csv(processed / "real_global_universe_market_cap_coverage.csv")
    coverage = _read_csv(processed / "global_returns_coverage_report.csv")
    fx = _read_csv(processed / "global_fx_normalization_report.csv")
    diagnostics = _read_csv(processed / "global_summary_statistics.csv")
    normality = _read_csv(processed / "global_normality_tests.csv")
    stationarity = _read_csv(processed / "global_stationarity_tests.csv")
    clusters = _read_csv(processed / "global_cluster_diagnostics.csv")
    cluster_membership = _read_csv(processed / "global_cluster_membership.csv")
    covariance = _read_csv(processed / "global_covariance_estimator_comparison.csv")
    applicability = _read_csv(processed / "model_applicability_matrix.csv")
    model_comparison = _read_csv(processed / "global_master_model_comparison.csv")
    weights = _read_csv(processed / "global_master_candidate_weights.csv")
    constraint = _read_csv(processed / "global_master_constraint_audit.csv")
    asset_class = _read_csv(processed / "global_master_asset_class_weights.csv")
    region = _read_csv(processed / "global_master_region_weights.csv")
    cluster_weights = _read_csv(processed / "global_master_cluster_weights.csv")
    equal_weight = _read_csv(processed / "global_master_equal_weight_comparison.csv")
    random_benchmark = _read_csv(
        processed / "global_master_random_portfolio_benchmark.csv"
    )
    risk = _read_csv(processed / "global_master_risk_report.csv")
    forecast_league = _read_csv(processed / "global_forecast_model_league.csv")
    regression = _read_csv(processed / "global_forecast_regression_metrics.csv")
    classification = _read_csv(processed / "global_forecast_classification_metrics.csv")
    confusion = _read_csv(processed / "global_forecast_confusion_matrix.csv")
    roc = _read_csv(processed / "global_forecast_roc_auc.csv")
    timeseries = _read_csv(processed / "global_forecast_time_series_metrics.csv")
    monte_carlo = _read_csv(processed / "global_monte_carlo_projection.csv")
    scenario = _read_csv(processed / "global_scenario_analysis.csv")
    stress = _read_csv(processed / "global_stress_test_results.csv")
    capability = _read_csv(processed / "global_quant_capability_gap_matrix.csv")

    final_model = str(decision.get("final_model", "missing"))
    final_weights = _final_weights(weights, final_model)
    final_weight_sum = (
        final_weights["Weight"].sum() if "Weight" in final_weights else float("nan")
    )
    fx_status = decision.get("fx_normalization_status", "missing")
    promotion = decision.get("promotion_decision", "missing")

    lines = [
        "# QuantVerse Real Global Stock Master Report",
        "",
        "This report is generated from local QuantVerse outputs. It is not investment advice and does not claim guaranteed outperformance.",
        "",
        "## 1. Executive Summary",
        "",
        f"- Real stocks entered the current research universe: {_yes_no(_stock_rows(universe_summary) > 0)}.",
        f"- Final research candidate model: `{final_model}`.",
        f"- Promotion decision: `{promotion}`.",
        f"- FX normalization status: `{fx_status}`.",
        f"- Final candidate selected holdings: `{decision.get('selected_holdings', 'missing')}`.",
        f"- Final candidate full weight sum: `{final_weight_sum:.10f}`.",
        f"- Decision reason: {decision.get('reason', 'missing')}",
        "",
        "The system produced a constrained global research candidate, but the current run is not a promoted global USD master portfolio when local-currency assets are mixed without full FX normalization.",
        "",
        "## 2. Real Universe Counts",
        "",
        _table(universe_summary, max_rows=20),
        "",
        "## 3. Source Coverage and Source URLs",
        "",
        _table(source_coverage, max_rows=20),
        "",
        "## 4. Market-Cap Coverage",
        "",
        _table(market_caps, max_rows=20),
        "",
        "Equity sleeves with missing market caps are labelled as index proxies or manual-review proxies. They do not support exact top-100 market-cap claims.",
        "",
        "## 5. Price and Return Coverage",
        "",
        f"- Return matrix status: `{returns_status.get('status', 'missing')}`.",
        f"- Return matrix assets reported by status file: `{returns_status.get('assets', 'missing')}`.",
        _table(_summarize_coverage(coverage), max_rows=20),
        "",
        "## 6. FX Normalization",
        "",
        _table(_summarize_fx(fx), max_rows=20),
        "",
        "Promotion to a global USD portfolio is blocked when non-USD local returns are not converted into USD returns.",
        "",
        "## 7. Simple vs Log Return Policy",
        "",
        "- Simple returns are used for portfolio aggregation and weighted portfolio return series.",
        "- Log returns are produced for statistical diagnostics and time aggregation checks.",
        "- Both matrices are written to `data/processed/`.",
        "",
        "## 8. Normality and Stationarity Diagnostics",
        "",
        _normality_summary(normality),
        "",
        _stationarity_summary(stationarity),
        "",
        "## 9. Correlation, Clustering and PCA",
        "",
        _table(clusters, max_rows=15),
        "",
        _cluster_summary(cluster_membership),
        "",
        "## 10. Covariance Estimator Comparison",
        "",
        _table(covariance, max_rows=10),
        "",
        "## 11. Model Applicability Matrix",
        "",
        _table(_summarize_applicability(applicability), max_rows=30),
        "",
        "Models marked blocked, optional or not scientifically appropriate are not promoted as allocation engines.",
        "",
        "## 12. Portfolio Models Tested",
        "",
        _table(model_comparison, max_rows=30),
        "",
        "## 13. Weights and Constraint Audit",
        "",
        f"- Full weights file: `data/processed/global_master_candidate_weights.csv`.",
        f"- Final model weight sum: `{final_weight_sum:.10f}`.",
        _table(constraint, max_rows=20),
        "",
        "The holdings excerpt below is partial; use the full CSV for all weights.",
        "",
        _table(final_weights.sort_values("Weight", ascending=False), max_rows=40),
        "",
        "## 14. Asset-Class, Region and Cluster Weights",
        "",
        _table(asset_class, max_rows=20),
        "",
        _table(region, max_rows=20),
        "",
        _table(cluster_weights, max_rows=30),
        "",
        "## 15. Equal Weight Comparison",
        "",
        _table(equal_weight, max_rows=10),
        "",
        "## 16. Random Portfolio Benchmark",
        "",
        _table(_summarize_random_benchmark(random_benchmark), max_rows=20),
        "",
        "Random portfolios are a robustness benchmark, not proof of future superiority.",
        "",
        "## 17. Risk Metrics, VaR, CVaR and Drawdown",
        "",
        _table(risk, max_rows=20),
        "",
        "## 18. Forecast Model League and Train/Test Diagnostics",
        "",
        _table(forecast_league, max_rows=20),
        "",
        _table(regression, max_rows=10),
        "",
        _table(classification, max_rows=10),
        "",
        _table(confusion, max_rows=10),
        "",
        _table(roc, max_rows=10),
        "",
        _table(timeseries, max_rows=10),
        "",
        "AIC/BIC are reported only for model classes where they are meaningful. Optional ARIMA/GARCH rows are not treated as implemented allocation engines.",
        "",
        "## 19. Monte Carlo, Scenario and Stress Projections",
        "",
        _table(monte_carlo, max_rows=20),
        "",
        _table(scenario, max_rows=20),
        "",
        _table(stress, max_rows=20),
        "",
        "Projection outputs are scenario and simulation estimates, not investment advice or guarantees.",
        "",
        "## 20. Promotion Decision",
        "",
        f"- Promotion decision: `{promotion}`.",
        f"- Final model: `{final_model}`.",
        f"- Constraints pass for final model: `{decision.get('constraints_pass', 'missing')}`.",
        f"- Reason: {decision.get('reason', 'missing')}",
        "",
        "## 21. Capability Gap Matrix Summary",
        "",
        _table(_summarize_capability(capability), max_rows=20),
        "",
        "## 22. Output Artifacts",
        "",
        "- `data/processed/global_master_selected_assets.csv`",
        "- `data/processed/global_master_candidate_weights.csv`",
        "- `data/processed/global_master_asset_class_weights.csv`",
        "- `data/processed/global_master_region_weights.csv`",
        "- `data/processed/global_master_cluster_weights.csv`",
        "- `data/processed/global_master_model_comparison.csv`",
        "- `data/processed/global_master_equal_weight_comparison.csv`",
        "- `data/processed/global_master_random_portfolio_benchmark.csv`",
        "- `data/processed/global_master_constraint_audit.csv`",
        "- `data/processed/global_master_promotion_gate.csv`",
        "- `data/processed/global_forecast_model_league.csv`",
        "- `data/processed/global_monte_carlo_projection.csv`",
        "- `output/pdf/quantverse_real_global_stock_master_report.pdf`",
        "- `output/pdf/quantverse_real_global_stock_master_presentation.pdf`",
        "",
        "## 23. Remaining Limitations",
        "",
        "- Current constituent proxies are not point-in-time historical membership files.",
        "- Exact top-100 market-cap rankings are missing for most equity sleeves.",
        "- Global USD promotion is blocked until FX normalization is implemented.",
        "- Some Yahoo Finance price lookups can fail for specific tickers.",
        "- Transaction-cost and bootstrap robustness for the global stock master layer are still lighter than the ETF/challenger research layer.",
        "- Forecasting models remain diagnostic and are not direct buy/sell signals.",
        "",
        "## 24. Next Sprint",
        "",
        "Implement a point-in-time, FX-normalized global stock backtest: sourced market caps, dated membership, delistings, corporate actions, FX conversion, transaction-cost grid, bootstrap robustness and walk-forward global master promotion gates.",
    ]
    return "\n".join(lines) + "\n"


def _build_presentation(processed: Path) -> str:
    decision = _read_json(processed / "global_master_decision_summary.json")
    universe_summary = _read_csv(
        processed / "real_global_universe_population_summary.csv"
    )
    market_caps = _read_csv(processed / "real_global_universe_market_cap_coverage.csv")
    coverage = _read_csv(processed / "global_returns_coverage_report.csv")
    fx = _read_csv(processed / "global_fx_normalization_report.csv")
    model_comparison = _read_csv(processed / "global_master_model_comparison.csv")
    constraint = _read_csv(processed / "global_master_constraint_audit.csv")
    weights = _read_csv(processed / "global_master_candidate_weights.csv")
    risk = _read_csv(processed / "global_master_risk_report.csv")
    projection = _read_csv(processed / "global_monte_carlo_projection.csv")
    final_model = str(decision.get("final_model", "missing"))
    final_weights = _final_weights(weights, final_model)

    slides = [
        (
            "Slide 1: Current State",
            [
                "QuantVerse now produces a real current global research candidate from sourced stocks, crypto, commodities and defensive proxies.",
                f"Promotion decision: {decision.get('promotion_decision', 'missing')}.",
                "The output is research evidence, not investment advice.",
            ],
        ),
        (
            "Slide 2: Real Universe",
            [
                f"Stock/proxy rows entered: {_stock_rows(universe_summary)}.",
                "NASDAQ, NYSE proxy, Europe, Germany, UK, Turkey, Japan and China/HK sleeves are populated when sources are reachable.",
                "Crypto top-100 rows are market-cap API enriched; stable-like assets are excluded from investable risk-asset allocation.",
            ],
        ),
        (
            "Slide 3: Data Quality",
            [
                _one_line_table(_summarize_coverage(coverage)),
                _one_line_table(_summarize_fx(fx)),
                "Missing market caps are reported rather than fabricated.",
            ],
        ),
        (
            "Slide 4: Market-Cap Coverage",
            [
                _one_line_table(market_caps[["sleeve", "rows", "market_cap_rows"]]),
                "Only rows with sourced market-cap evidence can support exact top-100 market-cap claims.",
            ],
        ),
        (
            "Slide 5: Constraints",
            [
                "The policy candidate is long-only, sums to 1, applies single-name, asset-class, region and cluster caps.",
                _one_line_table(
                    constraint[["Model", "All_Constraints_Pass", "Failed_Constraints"]]
                ),
            ],
        ),
        (
            "Slide 6: Selected Weights",
            [
                f"Final model: {final_model}.",
                "Top holdings table is an excerpt; full weights are in data/processed/global_master_candidate_weights.csv.",
                _one_line_table(
                    final_weights.sort_values("Weight", ascending=False).head(8)
                ),
            ],
        ),
        (
            "Slide 7: Model Comparison",
            [
                _one_line_table(
                    model_comparison[
                        ["Model", "Status", "CAGR", "Sharpe", "Max_Drawdown"]
                    ].head(10)
                ),
                "Equal Weight remains a benchmark; random portfolios are robustness comparators.",
            ],
        ),
        (
            "Slide 8: Risk",
            [
                _one_line_table(risk.head(10)),
                "VaR/CVaR/drawdown are interpreted as historical and scenario diagnostics.",
            ],
        ),
        (
            "Slide 9: Projections",
            [
                _one_line_table(projection.head(12)),
                "Monte Carlo projections are assumption-sensitive and are not forecasts of guaranteed returns.",
            ],
        ),
        (
            "Slide 10: Decision",
            [
                f"Decision: {decision.get('promotion_decision', 'missing')}.",
                f"Reason: {decision.get('reason', 'missing')}",
                "Current result is an audited research candidate, not a promoted global USD master portfolio.",
            ],
        ),
        (
            "Slide 11: Blockers",
            [
                "Point-in-time market-cap-ranked stock universes are still missing.",
                "FX normalization is not complete for non-USD listings.",
                "Full global stock walk-forward promotion gate is future work.",
            ],
        ),
        (
            "Slide 12: Next Sprint",
            [
                "Add sourced market caps, dated membership, FX conversion, delisting/corporate-action handling, transaction-cost grid and global bootstrap robustness.",
            ],
        ),
    ]
    lines = ["# QuantVerse Real Global Stock Master Presentation", ""]
    for title, bullets in slides:
        lines.extend([f"## {title}", ""])
        lines.extend(f"- {bullet}" for bullet in bullets)
        lines.append("")
    return "\n".join(lines)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame({"status": [f"missing: {path}"]})
    try:
        return pd.read_csv(path)
    except Exception as exc:
        return pd.DataFrame({"status": [f"unreadable: {path}: {exc}"]})


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": f"missing: {path}"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": f"unreadable: {path}: {exc}"}


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows available._"
    clipped = frame.head(max_rows).copy()
    for column in clipped.columns:
        clipped[column] = clipped[column].map(_format_cell)
    columns = [str(column) for column in clipped.columns]
    rows = []
    rows.append("| " + " | ".join(_md_cell(column) for column in columns) + " |")
    rows.append("| " + " | ".join("---" for _ in columns) + " |")
    for record in clipped.itertuples(index=False):
        rows.append("| " + " | ".join(_md_cell(value) for value in record) + " |")
    return "\n".join(rows)


def _one_line_table(frame: pd.DataFrame, max_rows: int = 8) -> str:
    if frame.empty:
        return "No rows available."
    text = frame.head(max_rows).to_string(index=False)
    return " / ".join(text.splitlines())


def _format_cell(value: object) -> object:
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value)
    if len(text) > 80:
        return text[:77] + "..."
    return text


def _md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _stock_rows(universe_summary: pd.DataFrame) -> int:
    if "sleeve" not in universe_summary or "rows" not in universe_summary:
        return 0
    mask = universe_summary["sleeve"].astype(str).str.startswith("global_equity")
    return int(pd.to_numeric(universe_summary.loc[mask, "rows"], errors="coerce").sum())


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _summarize_coverage(coverage: pd.DataFrame) -> pd.DataFrame:
    if "included_in_returns" in coverage:
        return coverage.groupby("included_in_returns", as_index=False).agg(
            assets=(
                ("ticker", "count")
                if "ticker" in coverage
                else ("included_in_returns", "count")
            )
        )
    if "included" in coverage:
        return coverage.groupby("included", as_index=False).agg(
            assets=(
                ("ticker", "count") if "ticker" in coverage else ("included", "count")
            )
        )
    if "status" in coverage:
        return coverage
    return coverage.head(10)


def _summarize_fx(fx: pd.DataFrame) -> pd.DataFrame:
    if "fx_normalization_status" in fx:
        return fx.groupby("fx_normalization_status", as_index=False).agg(
            assets=(
                ("ticker", "count")
                if "ticker" in fx
                else ("fx_normalization_status", "count")
            )
        )
    if "status" in fx:
        return fx
    return fx.head(10)


def _normality_summary(normality: pd.DataFrame) -> str:
    if "normality_result" not in normality:
        return _table(normality, max_rows=10)
    summary = normality.groupby("normality_result", as_index=False).agg(
        assets=("ticker", "count")
    )
    return _table(summary, max_rows=10)


def _stationarity_summary(stationarity: pd.DataFrame) -> str:
    if "stationarity_result" not in stationarity:
        return _table(stationarity, max_rows=10)
    summary = stationarity.groupby("stationarity_result", as_index=False).agg(
        assets=("ticker", "count")
    )
    return _table(summary, max_rows=10)


def _cluster_summary(membership: pd.DataFrame) -> str:
    if "cluster" not in membership:
        return _table(membership, max_rows=10)
    summary = membership.groupby("cluster", as_index=False).agg(
        holdings=("ticker", "count")
    )
    return _table(summary, max_rows=30)


def _summarize_applicability(applicability: pd.DataFrame) -> pd.DataFrame:
    if "current_status" not in applicability:
        return applicability
    return applicability.groupby("current_status", as_index=False).agg(
        models=("model", "count")
    )


def _summarize_capability(capability: pd.DataFrame) -> pd.DataFrame:
    if "status" not in capability:
        return capability
    return capability.groupby("status", as_index=False).agg(items=("item", "count"))


def _summarize_random_benchmark(random_benchmark: pd.DataFrame) -> pd.DataFrame:
    metric_columns = [
        column
        for column in [
            "CAGR",
            "Annual_Return",
            "Volatility",
            "Sharpe",
            "Sortino",
            "Max_Drawdown",
            "CVaR_95",
            "Total_Return",
        ]
        if column in random_benchmark
    ]
    if not metric_columns:
        return random_benchmark.head(10)
    return random_benchmark[metric_columns].describe().reset_index()


def _final_weights(weights: pd.DataFrame, final_model: str) -> pd.DataFrame:
    if weights.empty or "Model" not in weights:
        return weights
    selected = weights.loc[weights["Model"].astype(str).eq(final_model)].copy()
    return selected if not selected.empty else weights.head(0).copy()


def _markdown_to_pdf(
    markdown: str,
    path: Path,
    title: str,
    pagesize=A4,
    page_break_on_h2: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=title,
    )
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#102f45")
    styles["Heading1"].textColor = colors.HexColor("#102f45")
    styles["Heading2"].textColor = colors.HexColor("#244c5a")
    story: list[Any] = []
    in_code = False
    code_lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["Code"]))
                story.append(Spacer(1, 6))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("# "):
            story.append(Paragraph(_safe(line[2:]), styles["Title"]))
            story.append(Spacer(1, 12))
        elif line.startswith("## "):
            if page_break_on_h2 and story:
                story.append(PageBreak())
            story.append(Paragraph(_safe(line[3:]), styles["Heading2"]))
            story.append(Spacer(1, 8))
        elif line.startswith("- "):
            story.append(Paragraph(_safe(line), styles["BodyText"]))
            story.append(Spacer(1, 4))
        elif line.startswith("|"):
            wrapped = "\n".join(textwrap.wrap(line, width=120)) or line
            story.append(Preformatted(_safe(wrapped), styles["Code"]))
        elif not line:
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(_safe(line), styles["BodyText"]))
            story.append(Spacer(1, 5))
    if code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["Code"]))
    doc.build(story)


def _safe(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "")
    )


if __name__ == "__main__":
    raise SystemExit(main())
