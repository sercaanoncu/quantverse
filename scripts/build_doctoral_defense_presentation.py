"""Build the QuantVerse doctoral defense presentation PDF.

The slide source is committed under docs/thesis. Generated presentation outputs
are written under output/thesis and must not be committed.
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = ROOT / "docs" / "thesis" / "QUANTVERSE_DOCTORAL_DEFENSE_PRESENTATION.md"
FULL_SOURCE_MD = (
    ROOT / "docs" / "thesis" / "QUANTVERSE_DOCTORAL_DEFENSE_PRESENTATION_FULL.md"
)
OUTPUT_DIR = ROOT / "output" / "thesis"
OUTPUT_PDF = OUTPUT_DIR / "quantverse_doctoral_defense_presentation.pdf"
FULL_OUTPUT_PDF = OUTPUT_DIR / "quantverse_doctoral_defense_presentation_full.pdf"
PPTX_PATH = OUTPUT_DIR / "quantverse_doctoral_defense_presentation.pptx"


def _parse_slides() -> list[dict[str, str]]:
    lines = SOURCE_MD.read_text(encoding="utf-8").splitlines()
    table_lines = [
        line for line in lines if line.startswith("|") and line.endswith("|")
    ]
    rows: list[list[str]] = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    if len(rows) < 2:
        raise ValueError(f"No slide table found in {SOURCE_MD}")
    headers = rows[0]
    slides = [dict(zip(headers, row)) for row in rows[1:]]
    return slides


def _register_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for candidate in [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont("QuantVerseSlideSans", str(candidate)))
            return "QuantVerseSlideSans"
    return "Helvetica"


def _wrap_text(text: str, max_chars: int = 78) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        extra = 1 if current else 0
        if current_len + len(word) + extra > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + extra
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_wrapped(canvas, text: str, x: float, y: float, font: str, size: int) -> float:
    canvas.setFont(font, size)
    for line in _wrap_text(text):
        canvas.drawString(x, y, line)
        y -= size + 5
    return y


def _draw_slide(canvas, slide: dict[str, str], font: str, total: int) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter

    width, height = landscape(letter)
    slide_no = slide["Slide"]
    canvas.setFillColor(colors.HexColor("#0B1F33"))
    canvas.rect(0, height - 70, width, 70, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(font, 24)
    canvas.drawString(42, height - 45, slide["Title"])
    canvas.setFont(font, 10)
    canvas.drawRightString(width - 42, height - 44, f"{slide_no} / {total}")

    canvas.setFillColor(colors.HexColor("#145DA0"))
    canvas.rect(42, height - 112, 120, 18, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(font, 9)
    canvas.drawString(50, height - 108, "Main message")
    canvas.setFillColor(colors.HexColor("#111827"))
    y = _draw_wrapped(canvas, slide["Main message"], 42, height - 140, font, 18)

    canvas.setFillColor(colors.HexColor("#5A7D2B"))
    canvas.rect(42, y - 28, 120, 18, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(font, 9)
    canvas.drawString(50, y - 24, "Evidence source")
    canvas.setFillColor(colors.HexColor("#111827"))
    y = _draw_wrapped(canvas, slide["Evidence source"], 42, y - 55, font, 15)

    canvas.setFillColor(colors.HexColor("#8A4F14"))
    canvas.rect(42, y - 28, 145, 18, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(font, 9)
    canvas.drawString(50, y - 24, "Decision implication")
    canvas.setFillColor(colors.HexColor("#111827"))
    _draw_wrapped(canvas, slide["Decision implication"], 42, y - 55, font, 15)

    canvas.setFillColor(colors.HexColor("#E8EEF7"))
    canvas.rect(width - 190, 80, 120, 260, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#145DA0"))
    canvas.rect(width - 175, 95, 90, 35 + (int(slide_no) % 5) * 28, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#111827"))
    canvas.setFont(font, 11)
    canvas.drawCentredString(width - 130, 360, "Evidence gate")
    canvas.setFont(font, 8)
    canvas.drawCentredString(width - 130, 62, "Not a raw table dump")
    canvas.showPage()


def build_pdf(slides: list[dict[str, str]], output_pdf: Path = OUTPUT_PDF) -> bool:
    try:
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        print(f"PDF dependency unavailable: {exc}")
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font = _register_font()
    deck = canvas.Canvas(str(output_pdf), pagesize=landscape(letter))
    deck.setTitle("QuantVerse Doctoral Defense Presentation")
    deck.setAuthor("Sercan Oncu")
    for slide in slides:
        _draw_slide(deck, slide, font, len(slides))
    deck.save()
    return True


def build_full_slide_source() -> list[dict[str, str]]:
    topics = [
        "Project Pitch",
        "Research Problem",
        "Economic Motivation",
        "Public Data Universe",
        "Exact Top-100 Limitation",
        "FX Normalization",
        "Simple and Log Returns",
        "Stock Scoring",
        "Coverage Score",
        "Momentum Features",
        "Risk Penalty",
        "Diversification Score",
        "Expected Return Forecast",
        "Random Walk Baseline",
        "Ridge Diagnostic",
        "Forecast Confidence",
        "Equal Weight",
        "Random Portfolios",
        "Inverse Volatility",
        "GMV",
        "Max Sharpe",
        "Min CVaR",
        "HRP",
        "Risk Parity",
        "Black-Litterman",
        "Forecast Enhanced Portfolio",
        "Policy Constrained Portfolio",
        "Risk Metrics",
        "VaR and CVaR",
        "Drawdown",
        "Risk Contribution",
        "Stress Testing",
        "Walk-Forward Design",
        "No-Look-Ahead Rule",
        "Transaction Costs",
        "Model League Status",
        "Promotion Gate",
        "Current Results",
        "Selected Stocks",
        "Final Weights",
        "Benchmark Comparison",
        "Random Benchmark",
        "Scientific Audit",
        "Excel Output",
        "PDF Output",
        "GitHub Value",
        "CV Value",
        "Bank Interview Value",
        "Remaining Blockers",
        "Next Sprint",
    ]
    slides = []
    for idx, topic in enumerate(topics, start=1):
        slides.append(
            {
                "Slide": str(idx),
                "Title": topic,
                "Main message": _main_message(topic),
                "Evidence source": _evidence_source(topic),
                "Decision implication": _decision_implication(topic),
            }
        )
    FULL_SOURCE_MD.write_text(_slides_to_markdown(slides), encoding="utf-8")
    return slides


def _main_message(topic: str) -> str:
    return {
        "Project Pitch": "QuantVerse v2 is a public-data global equity research engine, not an advice engine.",
        "Current Results": "The system now scores stocks, forecasts returns, builds a model league and runs public-data walk-forward validation.",
        "Remaining Blockers": "Official exact top-100, point-in-time constituents, delistings and corporate actions remain future institutional blockers.",
    }.get(
        topic,
        f"{topic} is implemented or governed as an explicit part of the QuantVerse v2 research workflow.",
    )


def _evidence_source(topic: str) -> str:
    if topic in {"Stock Scoring", "Selected Stocks"}:
        return "data/processed/global_stock_scores.csv"
    if topic in {
        "Expected Return Forecast",
        "Random Walk Baseline",
        "Ridge Diagnostic",
    }:
        return "data/processed/global_stock_return_forecasts.csv"
    if topic in {"Equal Weight", "GMV", "HRP", "Risk Parity", "Black-Litterman"}:
        return "data/processed/global_portfolio_league.csv"
    if topic in {"Walk-Forward Design", "Current Results"}:
        return "data/processed/global_walk_forward_summary.json"
    return "QuantVerse v2 generated outputs and methodology mapping"


def _decision_implication(topic: str) -> str:
    if topic in {"Promotion Gate", "Remaining Blockers", "Exact Top-100 Limitation"}:
        return "Do not claim promoted institutional global USD master portfolio."
    if topic in {"GitHub Value", "CV Value", "Bank Interview Value"}:
        return "Use as evidence of quantitative research engineering and honest validation discipline."
    return "Use the result as public-data research evidence with limitations visible."


def _slides_to_markdown(slides: list[dict[str, str]]) -> str:
    lines = [
        "# QuantVerse Doctoral Defense Presentation Full",
        "",
        "| Slide | Title | Main message | Evidence source | Decision implication |",
        "|---|---|---|---|---|",
    ]
    for slide in slides:
        lines.append(
            "| "
            + " | ".join(
                [
                    slide["Slide"],
                    slide["Title"],
                    slide["Main message"],
                    slide["Evidence source"],
                    slide["Decision implication"],
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_slide_inventory(slides: list[dict[str, str]]) -> None:
    inventory = OUTPUT_DIR / "quantverse_doctoral_defense_presentation_inventory.csv"
    with inventory.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(slides[0].keys()))
        writer.writeheader()
        writer.writerows(slides)


def main() -> int:
    slides = _parse_slides()
    if not (25 <= len(slides) <= 35):
        raise ValueError(f"Expected 25-35 slides, found {len(slides)}")
    pdf_ok = build_pdf(slides)
    full_slides = build_full_slide_source()
    if not (45 <= len(full_slides) <= 60):
        raise ValueError(f"Expected 45-60 full slides, found {len(full_slides)}")
    full_pdf_ok = build_pdf(full_slides, FULL_OUTPUT_PDF)
    write_slide_inventory(slides)
    print(f"Defense slide count: {len(slides)}")
    print(f"Full defense slide count: {len(full_slides)}")
    if pdf_ok:
        print(f"Defense PDF written: {OUTPUT_PDF}")
    else:
        print("Defense PDF was not generated.")
    if full_pdf_ok:
        print(f"Full defense PDF written: {FULL_OUTPUT_PDF}")
    else:
        print("Full defense PDF was not generated.")
    if importlib.util.find_spec("pptx") and PPTX_PATH.exists():
        print(f"Defense PPTX written: {PPTX_PATH}")
    else:
        print("Defense PPTX not generated; local PPTX package/workflow unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
