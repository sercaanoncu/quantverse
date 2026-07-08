"""Validate QuantVerse v2 forecast diagnostics against random-walk baselines."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_forecast_validation import (
    build_forecast_validation,
    write_forecast_validation_outputs,
)  # noqa: E402

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    del args
    forecasts = _read_csv(PROCESSED / "global_stock_return_forecasts.csv")
    validation = build_forecast_validation(forecasts)
    write_forecast_validation_outputs(validation, PROCESSED)
    status = (
        validation["by_horizon"]["forecast_validation_status"]
        .astype(str)
        .mode()
        .iloc[0]
        if not validation["by_horizon"].empty
        else "not_run"
    )
    print(f"Global forecast validation written: {status}")
    return 0


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


if __name__ == "__main__":
    sys.exit(main())
