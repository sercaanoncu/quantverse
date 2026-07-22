"""Build the time-aligned market risk-free hurdle for QuantVerse equity research."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.risk_free import fetch_market_risk_free_series  # noqa: E402
from project.research.run_identity import (
    read_run_manifest,
    register_artifacts,
)  # noqa: E402

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    config = _read_config(ROOT / args.config).get("v2", {})
    returns_path = PROCESSED / "global_security_simple_returns_usd.csv"
    if not returns_path.exists():
        print("Missing return matrix; risk-free series not built.")
        return 0
    returns = pd.read_csv(returns_path)
    date_column = returns.columns[0]
    dates = pd.to_datetime(returns[date_column], errors="coerce")
    risk_free = fetch_market_risk_free_series(
        dates,
        proxy=str(config.get("risk_free_proxy", "^IRX")),
        fill_limit_days=int(config.get("risk_free_fill_limit_days", 5)),
    )
    run_metadata = read_run_manifest(PROCESSED)
    risk_free = attach_run_metadata(risk_free, run_metadata)
    output = PROCESSED / "global_risk_free_series.csv"
    risk_free.to_csv(output, index=False)
    register_artifacts(PROCESSED, [output], run_metadata)
    print(
        "Global risk-free series written: "
        f"{len(risk_free)} observations; proxy={risk_free['proxy'].iloc[0]}"
    )
    return 0


def _read_config(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


if __name__ == "__main__":
    sys.exit(main())
