"""Build a compact visual scientific audit PDF and presentation PDF."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

TITLE = "QuantVerse Scientific Audit"
REPORT_PATH = Path("output/pdf/quantverse_visual_scientific_audit_report.pdf")
PRESENTATION_PATH = Path(
    "output/pdf/quantverse_visual_scientific_audit_presentation.pdf"
)


def main() -> int:
    output_dir = Path("data/processed")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    classification = _read_csv(
        output_dir / "global_exact_proxy_classification_report.csv"
    )
    issues = _read_csv(output_dir / "global_scientific_sanity_issues.csv")
    decision = _read_json(output_dir / "global_master_decision_summary.json")

    sections = _report_sections(classification, issues, decision)
    try:
        _write_pdf(REPORT_PATH, TITLE, sections)
        _write_pdf(PRESENTATION_PATH, "QuantVerse Audit Presentation", sections[:6])
        print(f"PDF reports written: {REPORT_PATH}, {PRESENTATION_PATH}")
    except ImportError:
        fallback = REPORT_PATH.with_suffix(".md")
        fallback.write_text(_markdown(TITLE, sections), encoding="utf-8")
        print(f"reportlab unavailable; markdown fallback written: {fallback}")
    return 0


def _report_sections(
    classification: pd.DataFrame,
    issues: pd.DataFrame,
    decision: dict[str, object],
) -> list[dict[str, object]]:
    unsupported = (
        classification.loc[
            ~classification["classification"]
            .astype(str)
            .eq("exact_market_cap_rank_supported")
        ]
        if not classification.empty and "classification" in classification
        else pd.DataFrame()
    )
    blockers = (
        int(issues["promotion_blocker"].fillna(False).astype(bool).sum())
        if not issues.empty and "promotion_blocker" in issues
        else 0
    )
    promoted = str(decision.get("promotion_decision", "not available"))
    universe = str(
        decision.get("promotion_universe", "current global proxy research candidate")
    )
    exact_supported = (
        int(
            classification["classification"]
            .astype(str)
            .eq("exact_market_cap_rank_supported")
            .sum()
        )
        if not classification.empty and "classification" in classification
        else 0
    )
    return [
        {
            "heading": "Decision",
            "body": [
                f"Promotion decision: {promoted}",
                f"Universe label: {universe}",
                "Global stock master portfolio is not promoted unless sourced equity universe, FX, market-cap/rank and validation gates pass.",
            ],
        },
        {
            "heading": "Visual Decision Dashboard",
            "body": [
                "Chart: exact-supported sleeves, unsupported sleeves and promotion blockers.",
                "The intended reading is conservative: zero exact-supported sleeves and many blockers means no global master promotion.",
            ],
            "chart": {
                "labels": [
                    "Exact-supported sleeves",
                    "Unsupported sleeves",
                    "Promotion blockers",
                ],
                "values": [exact_supported, len(unsupported), blockers],
            },
        },
        {
            "heading": "Exact / Proxy Status",
            "body": [
                f"Sleeves reviewed: {len(classification)}",
                f"Unsupported exact top-100 sleeves: {len(unsupported)}",
                "Exact top-100 market-cap claim is not supported for these sleeves.",
            ],
            "table": (
                classification.head(12) if not classification.empty else pd.DataFrame()
            ),
        },
        {
            "heading": "Ne goruyorum?",
            "body": [
                "Her sleeve icin exact/proxy/manual-review durumu ve blocker sayisi goruluyor.",
                "Neden onemli? Top-100 iddiasi market-cap/rank/source kaniti olmadan bilimsel degildir.",
                "Kirmizi bayrak: source URL, provider, as-of date, market cap veya rank eksikse promotion bloke edilir.",
                "Hangi karari destekliyor? Global master portfolio not promoted veya insufficient_inputs kalmalidir.",
                "Kaynak dosya: data/processed/global_exact_proxy_classification_report.csv",
            ],
        },
        {
            "heading": "Scientific Red Flags",
            "body": [
                f"Scientific sanity issues: {len(issues)}",
                f"Promotion blockers: {blockers}",
                "Black-Litterman remains diagnostic/governance-sensitive unless official point-in-time market-cap priors and documented views exist.",
            ],
        },
        {
            "heading": "Required Next Fix",
            "body": [
                "Reconcile current public-provider candidate CSV files against official or vendor-grade top-100 sources.",
                "Add point-in-time membership, delisting/corporate-action evidence and global walk-forward validation before promotion.",
            ],
        },
    ]


def _write_pdf(path: Path, title: str, sections: list[dict[str, object]]) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for section in sections:
        story.append(Paragraph(str(section["heading"]), styles["Heading2"]))
        for line in section.get("body", []):
            story.append(Paragraph(str(line), styles["BodyText"]))
        chart = section.get("chart")
        if isinstance(chart, dict):
            story.append(Spacer(1, 6))
            story.append(_bar_chart(chart))
        table = section.get("table")
        if isinstance(table, pd.DataFrame) and not table.empty:
            cols = [
                column
                for column in ["sleeve", "classification", "blocking_rows", "reason"]
                if column in table
            ]
            values = [cols] + table[cols].astype(str).values.tolist()
            rendered = Table(values, repeatRows=1)
            rendered.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(Spacer(1, 6))
            story.append(rendered)
        story.append(Spacer(1, 12))
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36)
    doc.build(story)


def _bar_chart(config: dict[str, object]):
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors

    labels = [str(value) for value in config.get("labels", [])]
    values = [float(value) for value in config.get("values", [])]
    max_value = max(values) if values else 1.0

    drawing = Drawing(470, 170)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 45
    chart.height = 90
    chart.width = 380
    chart.data = [values]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(1.0, max_value * 1.25)
    chart.valueAxis.valueStep = max(1.0, round(max_value / 4) or 1.0)
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 25
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.bars[0].fillColor = colors.HexColor("#1f77b4")
    drawing.add(chart)

    for index, value in enumerate(values):
        x = 58 + index * (380 / max(1, len(values)))
        drawing.add(String(x, 140, f"{value:g}", fontSize=8))
    return drawing


def _markdown(title: str, sections: list[dict[str, object]]) -> str:
    lines = [f"# {title}", ""]
    for section in sections:
        lines.append(f"## {section['heading']}")
        lines.extend(f"- {line}" for line in section.get("body", []))
        lines.append("")
    return "\n".join(lines)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    sys.exit(main())
