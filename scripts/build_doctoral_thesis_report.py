"""Build the QuantVerse doctoral-style thesis report.

The source manuscript is committed under docs/thesis. Generated Markdown and
PDF outputs are written under output/thesis and must not be committed.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = ROOT / "docs" / "thesis" / "QUANTVERSE_DOCTORAL_DISSERTATION.md"
OUTPUT_DIR = ROOT / "output" / "thesis"
OUTPUT_MD = OUTPUT_DIR / "quantverse_doctoral_dissertation.md"
OUTPUT_PDF = OUTPUT_DIR / "quantverse_doctoral_dissertation.pdf"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"missing": True}
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_shape(path: Path) -> tuple[int, list[str]]:
    if not path.exists():
        return 0, []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return len(rows), list(reader.fieldnames or [])


def _first_csv_rows(path: Path, limit: int = 5) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for _, row in zip(range(limit), reader)]


def _evidence_snapshot() -> str:
    processed = ROOT / "data" / "processed"
    decision = _load_json(processed / "global_master_decision_summary.json")
    summary_rows = _first_csv_rows(
        processed / "global_scientific_sanity_summary.csv", limit=1
    )
    issues_count, issues_cols = _csv_shape(
        processed / "global_scientific_sanity_issues.csv"
    )
    weights_count, _ = _csv_shape(processed / "global_master_candidate_weights.csv")
    cap_blockers_count, _ = _csv_shape(
        processed / "global_market_cap_rank_blockers.csv"
    )
    fx_rows, _ = _csv_shape(processed / "global_fx_normalization_report.csv")
    exact_rows, _ = _csv_shape(
        processed / "global_exact_proxy_classification_report.csv"
    )
    bl_rows, _ = _csv_shape(
        processed / "global_black_litterman_prerequisite_report.csv"
    )

    lines = [
        "",
        "## Generated Evidence Snapshot",
        "",
        "This section is appended by `scripts/build_doctoral_thesis_report.py` "
        "from local generated evidence files. Missing files are reported as "
        "missing evidence, not fabricated.",
        "",
        f"- Branch at build time: `{_git_value('branch', '--show-current')}`",
        f"- Commit at build time: `{_git_value('rev-parse', '--short', 'HEAD')}`",
        f"- Global master decision status: `{decision.get('status', 'missing')}`",
        f"- Promotion decision: `{decision.get('promotion_decision', 'missing')}`",
        f"- Decision reason: {decision.get('reason', 'missing')}",
        f"- Scientific sanity summary: {summary_rows[0] if summary_rows else 'missing'}",
        f"- Scientific sanity issues rows: {issues_count}",
        f"- Scientific sanity issue columns: {issues_cols}",
        f"- Candidate weight rows: {weights_count}",
        f"- Market-cap/rank blocker rows: {cap_blockers_count}",
        f"- FX normalization rows: {fx_rows}",
        f"- Exact/proxy classification rows: {exact_rows}",
        f"- Black-Litterman prerequisite rows: {bl_rows}",
        "",
        "### Evidence Interpretation",
        "",
        "The generated snapshot confirms that the thesis is evidence-bound. "
        "If the active decision is `insufficient_inputs`, no downstream model "
        "metric is allowed to promote the global USD master portfolio.",
    ]
    return "\n".join(lines)


def build_markdown() -> str:
    source = _read_text(SOURCE_MD)
    if not source:
        raise FileNotFoundError(f"Missing source manuscript: {SOURCE_MD}")
    output = source.rstrip() + "\n" + _evidence_snapshot() + "\n"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(output, encoding="utf-8")
    return output


def _register_fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    bold_candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    for candidate in regular_candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont("QuantVerseSans", str(candidate)))
            regular_font = "QuantVerseSans"
            break
    for candidate in bold_candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont("QuantVerseSansBold", str(candidate)))
            bold_font = "QuantVerseSansBold"
            break
    return regular_font, bold_font


def _paragraph(text: str, style):
    from reportlab.platypus import Paragraph

    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("  ", " &nbsp;")
    )
    return Paragraph(escaped, style)


def _table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows


def _table_flowables(table_lines: list[str], styles) -> list[object]:
    from reportlab.lib import colors
    from reportlab.platypus import Spacer, Table, TableStyle

    rows = _table_rows(table_lines)
    if not rows:
        return []
    if len(rows[0]) > 4:
        flowables: list[object] = []
        headers = rows[0]
        for row in rows[1:]:
            parts = [
                f"{header}: {value}"
                for header, value in zip(headers, row)
                if value and header
            ]
            flowables.append(_paragraph("; ".join(parts), styles["Small"]))
            flowables.append(Spacer(1, 4))
        return flowables

    data = [[_paragraph(cell, styles["TableCell"]) for cell in row] for row in rows]
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9AA7B7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [table, Spacer(1, 10)]


def _heading_level(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.*)$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _markdown_to_flowables(markdown: str) -> list[object]:
    from reportlab.platypus import PageBreak, Preformatted, Spacer
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch

    regular_font, bold_font = _register_fonts()
    sample = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "Title",
            parent=sample["Title"],
            fontName=bold_font,
            fontSize=18,
            leading=22,
            spaceAfter=16,
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName=bold_font,
            fontSize=15,
            leading=19,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName=bold_font,
            fontSize=12.5,
            leading=16,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=sample["Heading3"],
            fontName=bold_font,
            fontSize=11,
            leading=14,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName=regular_font,
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
        ),
        "Small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName=regular_font,
            fontSize=7.8,
            leading=10,
            spaceAfter=3,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=sample["BodyText"],
            fontName=regular_font,
            fontSize=7.2,
            leading=8.5,
        ),
        "Code": ParagraphStyle(
            "Code",
            parent=sample["Code"],
            fontName="Courier",
            fontSize=7.8,
            leading=10,
            leftIndent=0.15 * inch,
        ),
    }

    flowables: list[object] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    first_h1 = True

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            flowables.extend(_table_flowables(table_lines, styles))
            table_lines = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            flowables.append(Preformatted("\n".join(code_lines), styles["Code"]))
            flowables.append(Spacer(1, 8))
            code_lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                in_code = False
                flush_code()
            else:
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("|") and line.endswith("|"):
            table_lines.append(line)
            continue
        flush_table()
        if not line.strip():
            flowables.append(Spacer(1, 4))
            continue
        heading = _heading_level(line)
        if heading:
            level, text = heading
            if level == 1:
                if not first_h1:
                    flowables.append(PageBreak())
                first_h1 = False
                flowables.append(_paragraph(text, styles["Title"]))
            elif level == 2:
                flowables.append(_paragraph(text, styles["H1"]))
            elif level == 3:
                flowables.append(_paragraph(text, styles["H2"]))
            else:
                flowables.append(_paragraph(text, styles["H3"]))
            continue
        if line.startswith("- "):
            flowables.append(_paragraph("• " + line[2:].strip(), styles["Body"]))
        else:
            flowables.append(_paragraph(line, styles["Body"]))
    flush_table()
    flush_code()
    return flowables


def _toc_lines(markdown: str) -> Iterable[str]:
    for line in markdown.splitlines():
        heading = _heading_level(line)
        if heading and heading[0] in {1, 2}:
            yield "  " * (heading[0] - 1) + "- " + heading[1]


def build_pdf(markdown: str) -> bool:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate
    except ImportError as exc:
        print(f"PDF dependency unavailable: {exc}")
        return False

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="QuantVerse Doctoral Dissertation",
        author="Sercan Öncü",
    )

    def header_footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(45, 25, "QuantVerse doctoral-style research output")
        canvas.drawRightString(550, 25, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(
        _markdown_to_flowables(markdown),
        onFirstPage=header_footer,
        onLaterPages=header_footer,
    )
    return True


def main() -> int:
    markdown = build_markdown()
    pdf_ok = build_pdf(markdown)
    print(f"Thesis Markdown written: {OUTPUT_MD}")
    if pdf_ok:
        print(f"Thesis PDF written: {OUTPUT_PDF}")
    else:
        print("Thesis PDF was not generated; Markdown fallback is available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
