import subprocess
import sys

import pandas as pd

from project.data_pipeline.global_returns import (
    build_returns_matrix,
    coverage_report,
    fx_normalization_report,
)
from project.data_pipeline.security_universe import REQUIRED_UNIVERSE_COLUMNS


def _universe(tickers: list[str]) -> pd.DataFrame:
    rows = []
    for idx, ticker in enumerate(tickers):
        rows.append(
            {
                "ticker": ticker,
                "name": ticker,
                "sleeve": "global_equity_us",
                "region": "North America",
                "country": "United States",
                "exchange": "NYSE",
                "currency": "USD" if idx == 0 else "EUR",
                "asset_type": "equity",
                "sector": "",
                "industry": "",
                "market_cap_usd": 1000 - idx,
                "market_cap_rank": idx + 1,
                "as_of_date": "2026-01-31",
                "source": "unit",
                "data_provider": "unit",
                "investable": True,
                "benchmark_only": False,
                "signal_only": False,
                "include": True,
                "proxy_type": "direct_listing",
                "notes": "unit",
            }
        )
    return pd.DataFrame(rows, columns=REQUIRED_UNIVERSE_COLUMNS)


def test_returns_matrix_coverage_and_fx_reports_are_stable():
    prices = pd.DataFrame(
        {
            "AAA": [100, 101, 103, 104],
            "BBB": [50, None, None, None],
        },
        index=pd.date_range("2024-01-01", periods=4),
    )
    universe = _universe(["AAA", "BBB"])
    returns = build_returns_matrix(prices)
    coverage = coverage_report(prices, universe, min_observations=3)
    fx = fx_normalization_report(universe, base_currency="USD")

    assert "AAA" in returns.columns
    assert coverage.loc[coverage["ticker"].eq("BBB"), "drop_reason"].iloc[0]
    assert set(fx["fx_normalization_status"]) == {"native_base", "fx_missing"}


def test_global_returns_matrix_cli_uses_synthetic_prices(tmp_path):
    universe_path = tmp_path / "universe.csv"
    price_path = tmp_path / "prices.csv"
    output_dir = tmp_path / "processed"
    config = tmp_path / "config.yaml"
    _universe(["AAA", "BBB"]).to_csv(universe_path, index=False)
    pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=5),
            "AAA": [100, 101, 102, 103, 104],
            "BBB": [50, 51, 52, 53, 54],
        }
    ).to_csv(price_path, index=False)
    config.write_text(
        "\n".join(
            [
                f"equity_universe_path: {universe_path.as_posix()}",
                "additional_universe_paths: []",
                f"local_price_csv: {price_path.as_posix()}",
                f"output_dir: {output_dir.as_posix()}",
                "min_price_observations: 3",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_global_returns_matrix.py",
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (output_dir / "global_security_returns.csv").exists()
    assert (output_dir / "global_security_simple_returns_local.csv").exists()
    assert (output_dir / "global_security_simple_returns_usd.csv").exists()
    assert (output_dir / "global_fx_rate_coverage_report.csv").exists()
    assert (output_dir / "global_returns_coverage_report.csv").exists()
