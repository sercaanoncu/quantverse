import subprocess
import sys
from pathlib import Path

import pandas as pd

from scripts.build_current_global_universe import build_current_global_universe


def _source_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "name": ["A Corp", "B Corp", "C Corp"],
            "exchange": ["NYSE", "NYSE", "NYSE"],
            "country": ["United States", "United States", "United States"],
            "currency": ["USD", "USD", "USD"],
            "source": ["unit", "unit", "unit"],
            "source_url": [
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
            ],
            "as_of_date": ["2026-01-31", "2026-01-31", "2026-01-31"],
            "data_provider": ["unit", "unit", "unit"],
            "notes": ["current candidate", "current candidate", "current candidate"],
            "market_cap_usd": [300.0, 100.0, None],
        }
    )


def test_current_universe_builder_ranks_market_caps_and_reports_missing(tmp_path):
    source = tmp_path / "us_candidates.csv"
    _source_frame().to_csv(source, index=False)
    universe, missing = build_current_global_universe(
        {"source_files": {"global_equity_us": str(source)}, "top_n_per_sleeve": 2}
    )

    ranked = universe.loc[universe["include"].astype(bool)]
    assert ranked["ticker"].tolist() == ["AAA", "BBB"]
    assert ranked["market_cap_rank"].astype(int).tolist() == [1, 2]
    assert set(missing["ticker"]) == {"CCC"}


def test_current_universe_cli_exits_zero_when_sources_missing(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        "\n".join(
            [
                "mode: csv",
                "source_files:",
                "  global_equity_us: missing.csv",
                f"output_universe_path: {(tmp_path / 'universe.csv').as_posix()}",
                f"summary_path: {(tmp_path / 'summary.csv').as_posix()}",
                f"missing_market_caps_path: {(tmp_path / 'missing.csv').as_posix()}",
                f"bias_warnings_path: {(tmp_path / 'bias.csv').as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_current_global_universe.py",
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "sourced CSV inputs are required" in result.stdout
