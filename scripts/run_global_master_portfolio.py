"""Run the global master portfolio research allocator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.global_returns import load_global_universe
from project.data_pipeline.market_cap_rank_evidence import (
    write_market_cap_rank_outputs,
)
from project.research.global_master_portfolio import (
    run_master_portfolio_research,
    write_master_portfolio_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_master_portfolio.yaml",
        help="Path to global master portfolio YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = Path(config.get("output_dir", "data/processed"))
    output_dir.mkdir(parents=True, exist_ok=True)
    if not _has_investable_global_equity(config.get("universe_paths", []) or []):
        _write_insufficient_inputs(output_dir)
        print(
            "Global master portfolio not promoted: sourced global equity universe is missing."
        )
        return 0
    returns_path = Path(config.get("returns_path", ""))
    if not returns_path.exists():
        _write_status(output_dir, "missing_returns", "Global returns CSV is required.")
        print("Missing returns matrix; master portfolio not run.")
        return 0
    metadata = load_global_universe(config.get("universe_paths", []) or [])
    if metadata.empty:
        _write_status(
            output_dir, "missing_universe", "Global universe metadata is required."
        )
        print("Missing universe metadata; master portfolio not run.")
        return 0
    write_market_cap_rank_outputs(metadata, output_dir)
    returns = _load_returns(returns_path)
    selection = config.get("selection", {}) or {}
    random_cfg = config.get("random_portfolios", {}) or {}
    result = run_master_portfolio_research(
        returns,
        metadata,
        min_holdings=int(selection.get("min_holdings", 10)),
        max_holdings=int(selection.get("max_holdings", 40)),
        max_weight=float(selection.get("max_weight", 0.10)),
        n_random_portfolios=int(random_cfg.get("n_portfolios", 10000)),
        random_state=int(selection.get("random_state", 42)),
    )
    write_master_portfolio_outputs(result, output_dir)
    print(result["decision_summary"]["promotion_decision"])
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def _write_status(output_dir: Path, status: str, message: str) -> None:
    (output_dir / "global_master_decision_summary.json").write_text(
        json.dumps({"status": status, "message": message}, indent=2),
        encoding="utf-8",
    )


def _has_investable_global_equity(universe_paths: list[str]) -> bool:
    equity_frames = []
    for raw_path in universe_paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if "sleeve" in frame:
            equity_frames.append(
                frame.loc[frame["sleeve"].astype(str).str.startswith("global_equity")]
            )
    if not equity_frames:
        return False
    equity = pd.concat(equity_frames, ignore_index=True)
    if equity.empty:
        return False
    flags = _boolean_series(equity, "include") & _boolean_series(equity, "investable")
    if "benchmark_only" in equity:
        flags &= ~_boolean_series(equity, "benchmark_only")
    if "signal_only" in equity:
        flags &= ~_boolean_series(equity, "signal_only")
    return bool(flags.any())


def _boolean_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes", "y"}
    )


def _write_insufficient_inputs(output_dir: Path) -> None:
    decision = {
        "status": "insufficient_global_equity_universe",
        "run_type": "insufficient_inputs",
        "promotion_decision": "insufficient_inputs",
        "reason": "Sourced current global equity universe is missing or has zero investable equity rows.",
    }
    (output_dir / "global_master_decision_summary.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "Promotion_Decision": "insufficient_inputs",
                "Promoted": False,
                "Run_Type": "insufficient_inputs",
                "Reason": decision["reason"],
            }
        ]
    ).to_csv(output_dir / "global_master_promotion_gate.csv", index=False)


if __name__ == "__main__":
    sys.exit(main())
