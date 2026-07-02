"""Build QuantVerse v2 global portfolio risk reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from project.research.global_portfolio_risk import (
    build_portfolio_risk_report,
    build_stock_risk_metrics,
    write_risk_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    del args
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    weights_path = output / "global_portfolio_league_weights.csv"
    fallback_weights_path = output / "global_master_candidate_weights.csv"
    if not returns_path.exists():
        print("Missing returns; risk report not built.")
        return 0
    weights_source = weights_path if weights_path.exists() else fallback_weights_path
    if not weights_source.exists():
        print("Missing weights; risk report not built.")
        return 0
    returns = _read_returns(returns_path)
    weights = pd.read_csv(weights_source)
    stock_metrics = build_stock_risk_metrics(returns)
    portfolio_report, contributions, stress, tail = build_portfolio_risk_report(
        returns,
        weights,
    )
    write_risk_outputs(
        stock_metrics, portfolio_report, contributions, stress, tail, output
    )
    print(f"Global risk report written: {len(portfolio_report)} portfolios")
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
