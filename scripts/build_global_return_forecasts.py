"""Build QuantVerse v2 global return forecasts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from project.research.global_return_forecasting import (
    build_return_forecasts,
    write_return_forecasts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    del args
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    if not returns_path.exists():
        print("Missing returns; global return forecasts not built.")
        return 0
    forecasts = build_return_forecasts(_read_returns(returns_path))
    write_return_forecasts(forecasts, output / "global_stock_return_forecasts.csv")
    print(f"Global return forecasts written: {len(forecasts)} rows")
    return 0


def _read_returns(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame


if __name__ == "__main__":
    sys.exit(main())
