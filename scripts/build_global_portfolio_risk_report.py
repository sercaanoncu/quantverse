"""Build QuantVerse v2 global portfolio risk reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_portfolio_risk import (
    build_portfolio_risk_report,
    build_stock_risk_metrics,
    write_risk_outputs,
)  # noqa: E402
from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
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
    run_metadata = read_run_manifest(output)
    stock_metrics = attach_run_metadata(stock_metrics, run_metadata)
    portfolio_report = attach_run_metadata(portfolio_report, run_metadata)
    contributions = attach_run_metadata(contributions, run_metadata)
    stress = attach_run_metadata(stress, run_metadata)
    tail = attach_run_metadata(tail, run_metadata)
    write_risk_outputs(
        stock_metrics, portfolio_report, contributions, stress, tail, output
    )
    register_artifacts(
        output,
        [
            output / "global_stock_risk_metrics.csv",
            output / "global_portfolio_risk_report.csv",
            output / "global_risk_contribution_report.csv",
            output / "global_stress_test_results.csv",
            output / "global_tail_risk_report.csv",
        ],
        run_metadata,
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
