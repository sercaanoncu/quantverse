"""Run global statistical diagnostics on the global returns matrix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from project.research.global_statistical_diagnostics import diagnostics_bundle
from project.research.model_applicability import model_applicability_matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--returns",
        default="data/processed/global_security_log_returns.csv",
        help="Path to global log-return CSV for statistical diagnostics.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory for diagnostic outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    returns_path = Path(args.returns)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not returns_path.exists():
        print(f"Returns file not found: {returns_path}")
        return 0
    returns = _load_returns(returns_path)
    if returns.empty:
        print("Returns file is empty; diagnostics skipped.")
        return 0
    bundle = diagnostics_bundle(returns)
    file_map = {
        "summary_statistics": "global_summary_statistics.csv",
        "normality_tests": "global_normality_tests.csv",
        "stationarity_tests": "global_stationarity_tests.csv",
        "correlation_matrix": "global_correlation_matrix.csv",
        "high_correlation_pairs": "global_high_correlation_pairs.csv",
        "pca_summary": "global_pca_summary.csv",
        "covariance_estimator_comparison": "global_covariance_estimator_comparison.csv",
        "cluster_diagnostics": "global_cluster_diagnostics.csv",
        "cluster_membership": "global_cluster_membership.csv",
    }
    for key, filename in file_map.items():
        bundle[key].to_csv(
            output_dir / filename,
            index=key != "correlation_matrix",
        )
    model_applicability_matrix().to_csv(
        output_dir / "model_applicability_matrix.csv",
        index=False,
    )
    print(f"Global statistical diagnostics assets: {returns.shape[1]}")
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


if __name__ == "__main__":
    sys.exit(main())
