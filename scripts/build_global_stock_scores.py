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
        max_selected=int(v2.get("max_selected_stocks", 40)),
        default_scope=str(v2.get("default_scope", "equity_only")),
        include_crypto=bool(v2.get("include_crypto", False)),
        feature_history_eligibility=feature_eligibility,
        minimum_standard_observations=minimum_history,
        run_metadata=run_metadata,
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
