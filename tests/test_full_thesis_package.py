from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_full_thesis_and_defense_sources_exist_after_generation():
    thesis = ROOT / "docs" / "thesis" / "QUANTVERSE_DOCTORAL_DISSERTATION_FULL.md"
    defense = (
        ROOT / "docs" / "thesis" / "QUANTVERSE_DOCTORAL_DEFENSE_PRESENTATION_FULL.md"
    )

    assert thesis.exists()
    assert defense.exists()
    thesis_text = thesis.read_text(encoding="utf-8")
    defense_text = defense.read_text(encoding="utf-8")
    assert "Formula:" in thesis_text
    assert "Promotion decision" in thesis_text
    assert thesis_text.count("Formula:") >= 20
    assert "not investment advice" in thesis_text.lower()
    assert defense_text.count("|") > 100
    assert "Decision implication" in defense_text


def test_thesis_builder_exposes_required_full_output_paths():
    script = (ROOT / "scripts" / "build_doctoral_thesis_report.py").read_text(
        encoding="utf-8"
    )
    assert "quantverse_doctoral_dissertation_full.md" in script
    assert "quantverse_doctoral_dissertation_full.pdf" in script
    assert "Full thesis word count" in script
    assert "Full thesis formula count" in script
