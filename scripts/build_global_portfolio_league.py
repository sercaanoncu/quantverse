"""Build QuantVerse v2 global portfolio model league."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_portfolio_league import (
    build_portfolio_league,
    write_portfolio_league_outputs,
)  # noqa: E402
from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.global_portfolio_core import policy_from_mapping  # noqa: E402
from project.research.risk_free import read_risk_free_series  # noqa: E402
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config)
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    scores_path = output / "global_stock_scores.csv"
    forecasts_path = output / "global_stock_return_forecasts.csv"
    metadata_path = output / "global_current_selected_securities.csv"
    risk_free_path = output / "global_risk_free_series.csv"
    if not returns_path.exists() or not scores_path.exists():
        print("Missing returns or scores; portfolio league not built.")
        return 0
    if not metadata_path.exists() or not risk_free_path.exists():
        raise RuntimeError(
            "Canonical metadata and market risk-free evidence are required."
        )
    v2 = config.get("v2", {})
    risk_free = read_risk_free_series(risk_free_path)
    risk_free_daily = risk_free.set_index("Date")["daily_hurdle"]
    league, weights, status = build_portfolio_league(
        _read_returns(returns_path),
        pd.read_csv(scores_path),
        pd.read_csv(forecasts_path) if forecasts_path.exists() else None,
        pd.read_csv(metadata_path),
        max_assets=int(v2.get("target_holdings", 20)),
        max_weight=float(v2.get("max_weight", 0.10)),
        risk_free_rate_annual=float(risk_free["annual_rate"].mean()),
        risk_free_policy=str(
            v2.get(
                "risk_free_policy",
                "time_aligned_market_proxy_compounded_daily_hurdle",
            )
        ),
        risk_free_daily=risk_free_daily,
        constraint_policy=policy_from_mapping(v2),
    )
    run_metadata = read_run_manifest(output)
    league = attach_run_metadata(league, run_metadata)
    weights = attach_run_metadata(weights, run_metadata)
    status = attach_run_metadata(status, run_metadata)
    write_portfolio_league_outputs(league, weights, status, output)
    register_artifacts(
        output,
        [
            output / "global_portfolio_league.csv",
            output / "global_portfolio_league_weights.csv",
            output / "global_portfolio_model_status.csv",
        ],
        run_metadata,
    )
    print(f"Global portfolio league written: {len(league)} models")
    return 0


def _config(path: str) -> dict:
    config_path = Path(path)
    return (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )


def _read_returns(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame


if __name__ == "__main__":
    sys.exit(main())
