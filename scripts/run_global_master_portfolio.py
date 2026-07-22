"""Run the global master portfolio research allocator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.data_pipeline.global_returns import load_global_universe
from project.data_pipeline.market_cap_rank_evidence import (
    write_market_cap_rank_outputs,
)
from project.data_pipeline.security_identity import (
    filter_standard_history_eligible_inputs,
)
from project.research.global_master_portfolio import (
    run_master_portfolio_research,
    write_master_portfolio_outputs,
)
from project.research.run_identity import read_run_manifest, register_artifacts

MASTER_PORTFOLIO_ARTIFACTS = (
    "global_market_cap_rank_evidence_report.csv",
    "global_exact_proxy_classification_report.csv",
    "global_market_cap_rank_blockers.csv",
    "global_black_litterman_prerequisite_report.csv",
    "global_master_selected_assets.csv",
    "global_master_candidate_weights.csv",
    "global_master_model_comparison.csv",
    "global_master_equal_weight_comparison.csv",
    "global_master_random_portfolio_benchmark.csv",
    "global_master_promotion_gate.csv",
    "global_master_constraint_audit.csv",
    "global_master_asset_class_weights.csv",
    "global_master_region_weights.csv",
    "global_master_cluster_weights.csv",
    "global_master_risk_report.csv",
    "global_master_projection_summary.csv",
    "global_master_stress_test_results.csv",
    "global_correlation_matrix.csv",
    "global_high_correlation_pairs.csv",
    "global_cluster_diagnostics.csv",
    "global_estimator_comparison.csv",
    "global_master_exact_proxy_classification.csv",
    "global_master_black_litterman_prerequisites.csv",
    "global_master_monte_carlo_projection.csv",
    "global_master_decision_summary.json",
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
    eligibility_path = Path(
        config.get(
            "feature_history_eligibility_path",
            "data/processed/global_feature_history_eligibility.csv",
        )
    )
    if not eligibility_path.exists():
        _write_status(
            output_dir,
            "missing_history_eligibility",
            "Current feature-history eligibility audit is required.",
        )
        print(
            "Global master portfolio not run: feature-history eligibility audit is missing."
        )
        return 0
    feature_eligibility = _load_optional_csv(eligibility_path)
    run_metadata = read_run_manifest(output_dir)
    if feature_eligibility is None or not _eligibility_matches_run(
        feature_eligibility, run_metadata
    ):
        _write_status(
            output_dir,
            "stale_history_eligibility",
            "Feature-history eligibility does not match the current run identity.",
        )
        print(
            "Global master portfolio not run: feature-history eligibility is stale "
            "or invalid."
        )
        return 0
    try:
        returns, metadata, excluded = filter_standard_history_eligible_inputs(
            returns,
            metadata,
            feature_eligibility,
        )
    except ValueError as exc:
        _write_status(output_dir, "invalid_history_eligibility", str(exc))
        print(f"Global master portfolio not run: {exc}")
        return 0
    fx_report = _load_optional_csv(
        Path(
            config.get(
                "fx_report_path", "data/processed/global_fx_normalization_report.csv"
            )
        )
    )
    selection = config.get("selection", {}) or {}
    random_cfg = config.get("random_portfolios", {}) or {}
    constraints = config.get("portfolio_constraints", {}) or {}
    promotion_gate = config.get("promotion_gate", {}) or {}
    minimum_holdings = int(selection.get("min_holdings", 10))
    if returns.shape[1] < minimum_holdings:
        message = (
            f"Only {returns.shape[1]} standard-history-eligible assets remain; "
            f"{minimum_holdings} are required."
        )
        _write_status(output_dir, "insufficient_history_eligible_assets", message)
        print(f"Global master portfolio not run: {message}")
        return 0
    result = run_master_portfolio_research(
        returns,
        metadata,
        min_holdings=minimum_holdings,
        max_holdings=int(selection.get("max_holdings", 40)),
        max_weight=float(selection.get("max_weight", 0.10)),
        n_random_portfolios=int(random_cfg.get("n_portfolios", 10000)),
        random_state=int(selection.get("random_state", 42)),
        portfolio_constraints=constraints,
        promotion_gate_config=promotion_gate,
        fx_report=fx_report,
    )
    result["decision_summary"].update(
        {
            **run_metadata,
            "history_eligibility_gate": "passed",
            "history_ineligible_assets_excluded": excluded,
        }
    )
    write_master_portfolio_outputs(result, output_dir)
    register_artifacts(
        output_dir,
        [output_dir / name for name in MASTER_PORTFOLIO_ARTIFACTS],
        run_metadata,
        root=ROOT,
    )
    if excluded:
        print(
            "Excluded from global master portfolio inputs by history gate: "
            + ", ".join(excluded)
        )
    decision = result["decision_summary"]
    print(
        "Global master portfolio "
        f"{decision['promotion_decision']}: {decision['reason']}"
    )
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def _load_optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None


def _eligibility_matches_run(
    feature_eligibility: pd.DataFrame,
    run_metadata: dict[str, str],
) -> bool:
    required = {"ticker", "standard_composite_score_eligible", "run_id"}
    if feature_eligibility.empty or not required.issubset(feature_eligibility):
        return False
    expected = str(run_metadata.get("run_id", "")).strip()
    observed = set(feature_eligibility["run_id"].dropna().astype(str))
    return bool(expected and observed == {expected})


def _write_status(output_dir: Path, status: str, message: str) -> None:
    (output_dir / "global_master_decision_summary.json").write_text(
        json.dumps(
            {
                "status": status,
                "promotion_decision": "not promoted",
                "message": message,
            },
            indent=2,
        ),
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
