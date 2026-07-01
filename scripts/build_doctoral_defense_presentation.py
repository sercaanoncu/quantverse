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
OUTPUT_DIR = ROOT / "output" / "thesis"
OUTPUT_PDF = OUTPUT_DIR / "quantverse_doctoral_defense_presentation.pdf"
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


def build_pdf(slides: list[dict[str, str]]) -> bool:
    try:
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        print(f"PDF dependency unavailable: {exc}")
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font = _register_font()
    deck = canvas.Canvas(str(OUTPUT_PDF), pagesize=landscape(letter))
    deck.setTitle("QuantVerse Doctoral Defense Presentation")
    deck.setAuthor("Sercan Öncü")
    for slide in slides:
        _draw_slide(deck, slide, font, len(slides))
    deck.save()
    return True


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
    write_slide_inventory(slides)
    print(f"Defense slide count: {len(slides)}")
    if pdf_ok:
        print(f"Defense PDF written: {OUTPUT_PDF}")
    else:
        print("Defense PDF was not generated.")
    if importlib.util.find_spec("pptx") and PPTX_PATH.exists():
        print(f"Defense PPTX written: {PPTX_PATH}")
    else:
        print("Defense PPTX not generated; local PPTX package/workflow unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
