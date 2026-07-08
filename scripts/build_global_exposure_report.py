"""Build economic exposure interpretation for the QuantVerse v2 final model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_exposure_analysis import (
    build_exposure_analysis,
    write_exposure_outputs,
)

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    del args
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    universe = _read_csv(
        ROOT / "data" / "universe" / "current_global_equity_universe.csv"
    )
    risk_contributions = _read_csv(PROCESSED / "global_risk_contribution_report.csv")
    forecasts = _read_csv(PROCESSED / "global_stock_return_forecasts.csv")
    if weights.empty or universe.empty:
        print("Missing weights or universe; exposure report not built.")
        return 0
    final_model = _final_model()
    exposure = build_exposure_analysis(
        weights,
        universe,
        final_model=final_model,
        risk_contributions=risk_contributions,
        forecasts=forecasts,
    )
    write_exposure_outputs(exposure, PROCESSED)
    print(f"Global exposure report written for final model: {final_model}")
    return 0


def _final_model() -> str:
    decision_path = PROCESSED / "global_final_model_decision.json"
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        return str(decision.get("final_selected_model", "Equal Weight"))
    summary_path = PROCESSED / "quantverse_v2_demo_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return str(summary.get("final_selected_model", "Equal Weight"))
    return "Equal Weight"


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


if __name__ == "__main__":
    sys.exit(main())
