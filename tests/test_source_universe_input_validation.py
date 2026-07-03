import json
import subprocess
import sys

import pandas as pd

from scripts.validate_source_universe_inputs import validate_source_inputs


def _valid_source_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "name": ["Alpha A", "Beta B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "region": ["North America", "North America"],
            "exchange": ["NYSE", "NYSE"],
            "country": ["United States", "United States"],
            "currency": ["USD", "USD"],
            "asset_type": ["equity", "equity"],
            "source": ["Unit Source", "Unit Source"],
            "source_url": ["https://example.com/a", "https://example.com/b"],
            "as_of_date": ["2026-01-31", "2026-01-31"],
            "data_provider": ["unit", "unit"],
            "market_cap_usd": [1000.0, None],
            "market_cap_rank": [1, None],
            "sector": ["Technology", "Industrials"],
            "industry": ["Software", "Machinery"],
            "investable": [True, True],
            "benchmark_only": [False, False],
            "signal_only": [False, False],
            "include": [True, True],
            "proxy_type": ["direct_listing", "direct_listing"],
            "source_method": ["exact_market_cap_rank", "exact_market_cap_rank"],
            "notes": ["unit test", "unit test"],
        }
    )


def test_source_validator_reports_missing_inputs_without_failure(tmp_path):
    config = {
        "source_dir": str(tmp_path / "sources"),
        "files": {"global_equity_us": "us_candidates.csv"},
        "allowed_currencies": ["USD"],
    }
    summary, issues, status = validate_source_inputs(config)

    assert status["status"] == "source_inputs_missing"
    assert summary["status"].tolist() == ["missing"]
    assert issues["issue"].tolist() == ["file_missing"]


def test_source_validator_reports_missing_caps_ranks_and_duplicates(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    frame = _valid_source_frame()
    frame.loc[1, "ticker"] = "AAA"
    frame.to_csv(source_dir / "us_candidates.csv", index=False)
    config = {
        "source_dir": str(source_dir),
        "files": {"global_equity_us": "us_candidates.csv"},
        "allowed_currencies": ["USD"],
    }
    _, issues, status = validate_source_inputs(config)
    issue_set = set(issues["issue"])

    assert status["status"] == "validated_with_issues"
    assert "duplicate_ticker_in_sleeve" in issue_set
    assert "market_cap_usd_missing" in issue_set
    assert "market_cap_rank_missing" in issue_set


def test_source_validator_cli_writes_outputs_and_schema_errors_fail(tmp_path):
    source_dir = tmp_path / "sources"
    output_dir = tmp_path / "processed"
    source_dir.mkdir()
    pd.DataFrame({"ticker": ["AAA"]}).to_csv(
        source_dir / "us_candidates.csv", index=False
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                f"source_dir: {source_dir.as_posix()}",
                f"output_dir: {output_dir.as_posix()}",
                "files:",
                "  global_equity_us: us_candidates.csv",
                "allowed_currencies: [USD]",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_source_universe_inputs.py",
            "--config",
            str(config_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    status = json.loads(
        (output_dir / "source_universe_validation_status.json").read_text(
            encoding="utf-8"
        )
    )

    assert result.returncode == 1
    assert status["status"] == "schema_error"
    assert (output_dir / "source_universe_validation_issues.csv").exists()


def test_context_summary_script_runs_without_downloads():
    result = subprocess.run(
        [sys.executable, "scripts/quantverse_context_summary.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "branch:" in result.stdout
    assert "codex_context_pack:" in result.stdout
