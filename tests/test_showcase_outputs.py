from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "docs" / "showcase"


def test_showcase_package_exists_and_is_project_specific():
    expected = [
        "README_GITHUB_SHOWCASE.md",
        "CV_BULLETS.md",
        "LINKEDIN_PROJECT_POST.md",
        "BANK_INTERVIEW_TALK_TRACK.md",
        "PROJECT_SCREENSHOT_GUIDE.md",
    ]
    for filename in expected:
        path = SHOWCASE / filename
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "QuantVerse" in text
        assert "public-data" in text or "public-provider" in text


def test_showcase_guides_point_to_real_v2_outputs():
    guide = (SHOWCASE / "PROJECT_SCREENSHOT_GUIDE.md").read_text(encoding="utf-8")
    github = (SHOWCASE / "README_GITHUB_SHOWCASE.md").read_text(encoding="utf-8")

    assert "global_stock_scores.csv" in guide
    assert "global_portfolio_league.csv" in guide
    assert "quantverse_v2_demo_summary.json" in github
    assert "quantverse_v2_research_output.xlsx" in github
