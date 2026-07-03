"""Build QuantVerse v2 global return forecasts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_return_forecasting import (
    build_return_forecasts,
    write_return_forecasts,
)  # noqa: E402
from project.research.global_stock_scoring import (
    build_global_stock_scores,
)  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config)
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    scores_path = output / "global_stock_scores.csv"
    universe_path = Path("data/universe/current_global_equity_universe.csv")
    if not returns_path.exists():
        print("Missing returns; global return forecasts not built.")
        return 0
    returns = _read_returns(returns_path)
    tickers = _forecast_tickers(scores_path, universe_path, returns, config)
    if tickers:
        returns = returns[tickers]
    forecasts = build_return_forecasts(returns)
    write_return_forecasts(forecasts, output / "global_stock_return_forecasts.csv")
    print(f"Global return forecasts written: {len(forecasts)} rows")
    return 0


def _config(path: str) -> dict:
    config_path = Path(path)
    return (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )


def _forecast_tickers(
    scores_path: Path,
    universe_path: Path,
    returns: pd.DataFrame,
    config: dict,
) -> list[str]:
    if scores_path.exists():
        scores = pd.read_csv(scores_path)
        if "ticker" in scores:
            if "selection_flag" in scores:
                scores = scores.loc[scores["selection_flag"].astype(bool)]
            return [
                ticker
                for ticker in scores["ticker"].dropna().astype(str).drop_duplicates()
                if ticker in returns.columns
            ]
    if universe_path.exists():
        v2 = config.get("v2", {})
        scores = build_global_stock_scores(
            returns,
            pd.read_csv(universe_path),
            max_selected=int(v2.get("max_selected_stocks", 40)),
            default_scope=str(v2.get("default_scope", "equity_only")),
            include_crypto=bool(v2.get("include_crypto", False)),
        )
        return [
            ticker
            for ticker in scores["ticker"].dropna().astype(str).drop_duplicates()
            if ticker in returns.columns
        ]
    return []


def _read_returns(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame


if __name__ == "__main__":
    sys.exit(main())
