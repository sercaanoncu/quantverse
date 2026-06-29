"""Run the offline global stock-selection research prototype."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.security_universe import (
    filter_included_investable_assets,
    load_security_universe,
    summarize_security_universe,
)
from project.research.global_stock_selection import (
    build_inverse_volatility_portfolio,
    build_stock_selection_promotion_gate,
    compare_candidate_to_equal_weight_and_random,
    evaluate_portfolio_return_series,
    score_assets_for_selection,
    select_assets_by_cluster,
    simulate_random_portfolios,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_stock_selection.yaml",
        help="Path to global stock-selection YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"FAIL: Config not found: {config_path}")
        return 1

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = Path(config.get("output_dir", "data/processed"))
    output_dir.mkdir(parents=True, exist_ok=True)

    universe_path = Path(config.get("universe_path", ""))
    universe = load_security_universe(universe_path)
    universe_summary = summarize_security_universe(universe)
    _write_frame_with_schema(
        universe_summary,
        output_dir / "global_stock_selection_universe_summary.csv",
        [
            "sleeve",
            "rows",
            "included",
            "investable",
            "benchmark_only",
            "signal_only",
            "missing_market_cap_rows",
            "stablecoin_like_rows",
        ],
    )

    investable = filter_included_investable_assets(universe)
    if investable.empty:
        message = (
            "No populated investable universe found. Populate a sourced universe "
            "CSV with real tickers, market caps, ranks, dates and sources before "
            "running stock-selection research."
        )
        print(message)
        _write_summary(
            output_dir,
            {
                "status": "universe_not_populated",
                "config_path": str(config_path),
                "universe_path": str(universe_path),
                "message": message,
            },
        )
        return 0

    returns_path = config.get("returns_path")
    if not returns_path:
        message = "No returns_path configured; stock-selection research not run."
        print(message)
        _write_summary(
            output_dir,
            {
                "status": "returns_missing",
                "config_path": str(config_path),
                "universe_path": str(universe_path),
                "investable_assets": int(len(investable)),
                "message": message,
            },
        )
        return 0

    returns = _load_returns(Path(returns_path))
    available = [
        ticker for ticker in investable["ticker"].astype(str) if ticker in returns
    ]
    if not available:
        message = "No investable universe tickers were found in the returns matrix."
        print(message)
        _write_summary(output_dir, {"status": "no_returns_overlap", "message": message})
        return 0
    returns = returns[available]

    selection_config = config.get("selection", {})
    random_config = config.get("random_portfolios", {})
    promotion_config = config.get("promotion_gate", {})
    max_weight = float(selection_config.get("max_weight", 0.10))
    selected = select_assets_by_cluster(
        returns,
        min_holdings=int(selection_config.get("min_holdings", 10)),
        max_holdings=int(selection_config.get("max_holdings", 40)),
        random_state=int(selection_config.get("random_state", 42)),
    )
    scores = score_assets_for_selection(
        returns,
        risk_free_rate=float(config.get("risk_free_rate", 0.0)),
    ).set_index("Ticker")
    selected_assets = scores.loc[selected].reset_index()
    selected_assets.to_csv(
        output_dir / "global_stock_selection_selected_assets.csv", index=False
    )

    weights = build_inverse_volatility_portfolio(returns, selected, max_weight)
    weights.rename_axis("Ticker").reset_index(name="Weight").to_csv(
        output_dir / "global_stock_selection_candidate_weights.csv", index=False
    )

    candidate_returns = returns[selected] @ weights
    equal_weight_returns = returns.mean(axis=1)
    randoms = simulate_random_portfolios(
        returns,
        n_portfolios=int(random_config.get("n_portfolios", 10000)),
        max_weight=max_weight,
        random_state=int(selection_config.get("random_state", 42)),
    )
    randoms.to_csv(
        output_dir / "global_stock_selection_random_portfolio_benchmark.csv",
        index=False,
    )
    comparison = compare_candidate_to_equal_weight_and_random(
        evaluate_portfolio_return_series(candidate_returns),
        evaluate_portfolio_return_series(equal_weight_returns),
        randoms,
    )
    estimated_turnover = float(promotion_config.get("estimated_initial_turnover", 1.0))
    transaction_cost_bps = float(promotion_config.get("transaction_cost_bps", 10.0))
    comparison.update(
        {
            "Turnover": estimated_turnover,
            "Transaction_Cost_Bps": transaction_cost_bps,
            "Transaction_Cost_Drag": estimated_turnover * transaction_cost_bps / 10_000,
        }
    )
    gate = build_stock_selection_promotion_gate(
        comparison,
        random_percentile_threshold=float(
            promotion_config.get(
                "random_percentile_threshold",
                random_config.get("percentile_threshold", 0.90),
            )
        ),
        volatility_relative_limit=float(
            promotion_config.get("volatility_relative_limit", 1.25)
        ),
        max_drawdown_penalty=float(promotion_config.get("max_drawdown_penalty", 0.05)),
        cvar_penalty=float(promotion_config.get("cvar_penalty", 0.05)),
        max_turnover=float(promotion_config.get("max_turnover", 1.0)),
        max_transaction_cost_drag=float(
            promotion_config.get("max_transaction_cost_drag", 0.0025)
        ),
    )
    pd.DataFrame([{**comparison, **gate}]).to_csv(
        output_dir / "global_stock_selection_promotion_gate.csv", index=False
    )
    _write_summary(
        output_dir,
        {
            "status": "completed",
            "config_path": str(config_path),
            "universe_path": str(universe_path),
            "returns_path": str(returns_path),
            "available_assets": int(len(available)),
            "selected_assets": selected,
            "promotion_decision": gate["Promotion_Decision"],
            "reason": gate["Reason"],
        },
    )
    print(f"Selected candidate assets: {len(selected)}")
    print(f"Promotion decision: {gate['Promotion_Decision']}")
    print("Outputs written to data/processed.")
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Returns CSV not found: {path}")
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def _write_summary(output_dir: Path, payload: dict[str, object]) -> None:
    (output_dir / "global_stock_selection_summary.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _write_frame_with_schema(
    frame: pd.DataFrame,
    path: Path,
    columns: list[str],
) -> None:
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    frame.to_csv(path, index=False)


if __name__ == "__main__":
    sys.exit(main())
