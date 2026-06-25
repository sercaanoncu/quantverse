import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from project.reporting.pdf_report import InvestmentPDFReport, generate_pdf_report


def test_pdf_report_public_functions_importable():
    assert InvestmentPDFReport is not None
    assert callable(generate_pdf_report)


def test_static_html_report_can_be_generated_without_absolute_path_leak(tmp_path):
    from project.pipeline import _write_static_html_report

    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    (output_dir / "run_metadata.json").write_text(
        json.dumps(
            {"data_as_of": "2026-01-01", "html_report": "output/html/report.html"}
        ),
        encoding="utf-8",
    )
    (output_dir / "decision_summary.json").write_text(
        json.dumps({"primary_research_candidate": "HRP"}),
        encoding="utf-8",
    )
    pd.DataFrame({"Ticker": ["AAA"], "Decision": ["Included"]}).to_csv(
        output_dir / "data_quality_report.csv", index=False
    )
    pd.DataFrame({"Ticker": ["AAA"], "Equal Weight": [1.0]}).to_csv(
        output_dir / "portfolio_weights_matrix.csv", index=False
    )
    pd.DataFrame({"Strategy": ["HRP"], "Exceptions": [1]}).to_csv(
        output_dir / "var_exception_tests.csv", index=False
    )

    html_path = tmp_path / "report.html"
    _write_static_html_report(output_dir, html_path)
    html = html_path.read_text(encoding="utf-8")

    assert "QuantVerse Research Report" in html
    assert "VaR Exception Tests" in html
    assert str(tmp_path) not in html
    assert "C:\\Users\\" not in html


def test_cli_help_runs_without_live_data_access():
    env = os.environ.copy()
    src_path = str(Path.cwd() / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "scripts/run_full_pipeline.py", "--help"],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--config" in result.stdout
    assert "--skip-pdf" in result.stdout


def test_readme_mentions_reproducible_pdf_and_html_outputs():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "python scripts/run_full_pipeline.py --config configs/base.yaml" in text
    assert "output/html/quantverse_report.html" in text
    assert "output/pdf/quantverse_analysis_report.pdf" in text
