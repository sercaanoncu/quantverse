"""Build QuantVerse v2 global stock scores."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_stock_scoring import (
    build_global_stock_scores,
    write_global_stock_scores,
)  # noqa: E402
from project.data_pipeline.security_identity import (  # noqa: E402
    attach_run_metadata,
    build_feature_history_eligibility,
)
from project.research.global_portfolio_core import (  # noqa: E402
    build_canonical_security_metadata,
    policy_from_mapping,
    select_canonical_securities,
)
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config)
    paths = _paths(config)
    if not paths["universe"].exists() or not paths["returns"].exists():
        print("Missing universe or returns; global stock scores not built.")
        return 0
    v2 = config.get("v2", {})
    run_metadata = read_run_manifest(paths["output"])
    returns = _read_returns(paths["returns"])
    identity_audit = _read_optional_csv(paths["identity_audit"])
    minimum_history = int(v2.get("minimum_standard_history_observations", 252))
    feature_eligibility = build_feature_history_eligibility(
        returns,
        identity_audit,
        minimum_standard_observations=minimum_history,
    )
    feature_eligibility = attach_run_metadata(feature_eligibility, run_metadata)
    scores = build_global_stock_scores(
        returns,
        pd.read_csv(paths["universe"]),
        _read_optional_csv(paths["coverage"]),
        max_selected=int(v2.get("max_selected_stocks", v2.get("target_holdings", 20))),
        default_scope=str(v2.get("default_scope", "equity_only")),
        include_crypto=bool(v2.get("include_crypto", False)),
        feature_history_eligibility=feature_eligibility,
        minimum_standard_observations=minimum_history,
        run_metadata=run_metadata,
    )
    policy = policy_from_mapping(v2)
    metadata = build_canonical_security_metadata(
        pd.read_csv(paths["universe"]),
        identity_audit if identity_audit is not None else pd.DataFrame(),
        returns,
        metadata_cache_dir=ROOT
        / str(
            config.get(
                "exposure_metadata_cache_dir",
                "data/cache/exposure_metadata/yfinance_profiles",
            )
        ),
        allow_network=bool(config.get("allow_yfinance_metadata", True)),
    )
    selected, selection_audit = select_canonical_securities(scores, metadata, policy)
    selected_tickers = set(selected["ticker"].astype(str))
    reason_map = selection_audit.set_index("ticker")["selection_reason"].to_dict()
    scores["selection_flag"] = scores["ticker"].astype(str).isin(selected_tickers)
    scores["selection_reason"] = scores["ticker"].astype(str).map(reason_map)
    metadata = attach_run_metadata(metadata, run_metadata)
    selected = attach_run_metadata(selected, run_metadata)
    selection_audit = attach_run_metadata(selection_audit, run_metadata)
    rejected = selection_audit.loc[~selection_audit["selected"].map(bool)].head(20)
    metadata.to_csv(
        paths["output"] / "global_canonical_security_metadata.csv", index=False
    )
    selected.to_csv(
        paths["output"] / "global_current_selected_securities.csv", index=False
    )
    selection_audit.to_csv(
        paths["output"] / "global_canonical_selection_audit.csv", index=False
    )
    rejected.to_csv(paths["output"] / "global_rejected_candidates.csv", index=False)
    sensitivity_rows = []
    for holdings in v2.get("holdings_sensitivity", [15, 20, 25]):
        sensitivity_policy = policy.__class__(
            **{
                **policy.__dict__,
                "target_holdings": int(holdings),
            }
        )
        try:
            sensitivity_selected, _ = select_canonical_securities(
                scores,
                metadata,
                sensitivity_policy,
            )
            status = "feasible"
            tickers = ";".join(sensitivity_selected["ticker"].astype(str))
        except ValueError as exc:
            status = f"infeasible: {exc}"
            tickers = ""
        requested_product = (
            int(holdings) * sensitivity_policy.requested_max_issuer_weight
        )
        sensitivity_rows.append(
            {
                "target_holdings": int(holdings),
                "selection_constraint_status": status,
                "selected_tickers": tickers,
                "requested_5pct_cap_total_capacity": requested_product,
                "requested_5pct_cap_status": (
                    "infeasible_weight_sum_below_one"
                    if requested_product < 1.0 - 1e-12
                    else (
                        "singleton_equal_weight_solution"
                        if abs(requested_product - 1.0) <= 1e-12
                        else "nondegenerate_feasible_capacity"
                    )
                ),
            }
        )
    sensitivity = attach_run_metadata(pd.DataFrame(sensitivity_rows), run_metadata)
    sensitivity.to_csv(
        paths["output"] / "global_holdings_count_sensitivity.csv", index=False
    )
    feature_eligibility.to_csv(
        paths["output"] / "global_feature_history_eligibility.csv", index=False
    )
    write_global_stock_scores(scores, paths["output"] / "global_stock_scores.csv")
    register_artifacts(
        paths["output"],
        [
            paths["output"] / "global_feature_history_eligibility.csv",
            paths["output"] / "global_stock_scores.csv",
            paths["output"] / "global_canonical_security_metadata.csv",
            paths["output"] / "global_current_selected_securities.csv",
            paths["output"] / "global_canonical_selection_audit.csv",
            paths["output"] / "global_rejected_candidates.csv",
            paths["output"] / "global_holdings_count_sensitivity.csv",
        ],
        run_metadata,
    )
    print(f"Global stock scores written: {len(scores)} rows")
    return 0


def _config(path: str) -> dict:
    config_path = Path(path)
    return (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )


def _paths(config: dict) -> dict[str, Path]:
    output = Path("data/processed")
    return {
        "output": output,
        "universe": Path("data/universe/current_global_equity_universe.csv"),
        "returns": output / "global_security_simple_returns_usd.csv",
        "coverage": output / "global_returns_coverage_report.csv",
        "identity_audit": output / "global_security_identity_audit.csv",
    }


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
