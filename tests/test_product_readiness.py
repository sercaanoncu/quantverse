import subprocess
import sys
from pathlib import Path


def _run_script(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, script],
        check=False,
        capture_output=True,
        text=True,
    )


def test_healthcheck_script_exists_and_runs_from_repo_root():
    script = Path("scripts/quantverse_healthcheck.py")
    assert script.exists()

    result = _run_script(str(script))

    assert result.returncode == 0
    assert "PASS:" in result.stdout
    assert "Healthcheck completed" in result.stdout


def test_latest_run_summary_script_exists_and_runs_from_repo_root():
    script = Path("scripts/quantverse_latest_run_summary.py")
    assert script.exists()

    result = _run_script(str(script))

    assert result.returncode == 0
    assert "QuantVerse Latest Run Summary" in result.stdout
    assert "not investment advice" in result.stdout


def test_product_user_guide_exists():
    assert Path("docs/product_user_guide.md").exists()


def test_readme_mentions_professional_product_commands():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "python scripts/quantverse_healthcheck.py" in readme
    assert "python scripts/quantverse_latest_run_summary.py" in readme
    assert "python scripts/run_full_pipeline.py --config configs/base.yaml" in readme
    assert "python -m pytest -q" in readme


def test_personal_learning_and_scorecard_artifacts_are_not_public():
    removed_paths = [
        "docs/learning/quantverse_learning_path.md",
        "docs/learning/interview_answer_bank.md",
        "docs/audit/PROJECT_10_10_SCORECARD.md",
    ]
    for path in removed_paths:
        assert not Path(path).exists()

    readme = Path("README.md").read_text(encoding="utf-8")
    banned = [
        "interview_answer_bank",
        "quantverse_learning_path",
        "PROJECT_10_10_SCORECARD",
        "Interview Preparation Files",
        "10/10",
        "CV score",
    ]
    for phrase in banned:
        assert phrase not in readme


def test_product_docs_do_not_claim_live_trading_readiness():
    docs = [
        Path("README.md"),
        Path("docs/product_user_guide.md"),
    ]
    banned = [
        "production/live trading readiness: 10/10",
        "is a complete production trading platform",
        "guarantees returns",
        "investment advice",
    ]
    for doc in docs:
        text = " ".join(doc.read_text(encoding="utf-8").lower().split())
        assert "not investment advice" in text
        for phrase in banned[:-1]:
            assert phrase not in text
