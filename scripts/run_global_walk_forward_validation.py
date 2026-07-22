"""Run QuantVerse v2 public-data global walk-forward validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_walk_forward import (
    build_transaction_cost_sensitivity,
    run_public_data_walk_forward,
    write_walk_forward_outputs,
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
    config = _config(args.config).get("v2", {})
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    universe_path = Path("data/universe/current_global_equity_universe.csv")
    metadata_path = output / "global_canonical_security_metadata.csv"
    risk_free_path = output / "global_risk_free_series.csv"
    if not returns_path.exists() or not universe_path.exists():
        print("Missing returns or universe; walk-forward not run.")
        return 0
    if not metadata_path.exists() or not risk_free_path.exists():
        raise RuntimeError(
            "Canonical metadata and market risk-free evidence are required."
        )
    returns = _read_returns(returns_path)
    risk_free = read_risk_free_series(risk_free_path)
    risk_free_daily = risk_free.set_index("Date")["daily_hurdle"]
    configured_max_folds = config.get("walk_forward_max_folds")
    result = run_public_data_walk_forward(
        returns,
        pd.read_csv(universe_path),
        train_window_days=int(config.get("walk_forward_train_days", 252)),
        test_window_days=int(config.get("walk_forward_test_days", 21)),
        step_days=int(config.get("walk_forward_step_days", 21)),
        max_assets=int(config.get("walk_forward_max_assets", 20)),
        max_weight=float(config.get("max_weight", 0.10)),
        transaction_cost_bps=float(config.get("transaction_cost_bps", 10.0)),
        max_folds=(None if configured_max_folds is None else int(configured_max_folds)),
        default_scope=str(config.get("default_scope", "equity_only")),
        include_crypto=bool(config.get("include_crypto", False)),
        random_state=int(config.get("random_state", 42)),
        security_identity_audit=_read_optional_csv(
            output / "global_security_identity_audit.csv"
        ),
        minimum_standard_observations=int(
            config.get(
                "minimum_walk_forward_history_observations",
                config.get("minimum_standard_history_observations", 252),
            )
        ),
        risk_free_rate_annual=float(risk_free["annual_rate"].mean()),
        risk_free_policy=str(
            config.get(
                "risk_free_policy",
                "time_aligned_market_proxy_compounded_daily_hurdle",
            )
        ),
        random_benchmark_portfolios=int(config.get("random_portfolio_samples", 1000)),
        uncertainty_bootstrap_samples=int(
            config.get("uncertainty_bootstrap_samples", 1000)
        ),
        uncertainty_block_length=int(config.get("uncertainty_block_length", 21)),
        uncertainty_confidence_level=float(
            config.get("uncertainty_confidence_level", 0.95)
        ),
        security_metadata=pd.read_csv(metadata_path),
        constraint_policy=policy_from_mapping(config),
        risk_free_daily=risk_free_daily,
    )
    run_metadata = read_run_manifest(output)
    for key in [
        "validation",
        "returns",
        "weights",
        "turnover",
        "leakage_audit",
        "window_summary",
        "model_comparison",
        "random_distribution",
        "random_returns",
        "random_weights",
        "uncertainty",
    ]:
        result[key] = attach_run_metadata(result[key], run_metadata)
    result["random_benchmark_provenance"].update(run_metadata)
    result["summary"].update(run_metadata)
    write_walk_forward_outputs(result, output)
    cost_sensitivity = build_transaction_cost_sensitivity(
        result["returns"],
        result["turnover"],
        primary_cost_bps=float(config.get("transaction_cost_bps", 10.0)),
        cost_scenarios_bps=[
            float(value)
            for value in config.get(
                "transaction_cost_sensitivity_bps",
                [5.0, 10.0, 25.0],
            )
        ],
        risk_free_daily=risk_free_daily,
    )
    cost_sensitivity = attach_run_metadata(cost_sensitivity, run_metadata)
    cost_sensitivity.to_csv(
        output / "global_walk_forward_cost_sensitivity.csv", index=False
    )
    register_artifacts(
        output,
        [
            output / "global_walk_forward_validation.csv",
            output / "global_walk_forward_returns.csv",
            output / "global_walk_forward_weights.csv",
            output / "global_walk_forward_turnover.csv",
            output / "global_walk_forward_leakage_audit.csv",
            output / "global_walk_forward_window_summary.csv",
            output / "global_walk_forward_model_comparison.csv",
            output / "global_walk_forward_random_distribution.csv",
            output / "global_walk_forward_random_returns.csv",
            output / "global_walk_forward_random_weights.csv",
            output / "global_walk_forward_random_benchmark_provenance.json",
            output / "global_walk_forward_uncertainty.csv",
            output / "global_walk_forward_summary.json",
            output / "global_walk_forward_cost_sensitivity.csv",
        ],
        run_metadata,
    )
    print(result["summary"].get("walk_forward_status", "not_run"))
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


def _read_optional_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


if __name__ == "__main__":
    sys.exit(main())
