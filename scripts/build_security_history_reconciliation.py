"""Build QuantVerse v2 security-history and cross-artifact reconciliation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)
from project.data_pipeline.security_identity import (  # noqa: E402
    attach_run_metadata,
)
from project.research.security_history_reconciliation import (  # noqa: E402
    build_cross_artifact_count_reconciliation,
)
from project.reporting.selected_stock_report_view import (  # noqa: E402
    write_selected_stock_report_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    config_path = Path(args.config)
    config = (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    ) or {}
    v2 = config.get("v2", {})
    output = Path("data/processed")
    run_metadata = read_run_manifest(output)
    scores_path = output / "global_stock_scores.csv"
    top_holdings_path = output / "global_top_holdings_explanation.csv"
    universe_path = Path("data/universe/current_global_equity_universe.csv")
    if scores_path.exists() and top_holdings_path.exists() and universe_path.exists():
        write_selected_stock_report_artifacts(
            pd.read_csv(scores_path),
            pd.read_csv(top_holdings_path),
            output,
            pd.read_csv(universe_path),
            run_metadata=run_metadata,
        )
    reconciliation = build_cross_artifact_count_reconciliation(
        output,
        max_selected_stocks=int(v2.get("max_selected_stocks", 40)),
        walk_forward_max_assets=int(v2.get("walk_forward_max_assets", 20)),
    )
    reconciliation = attach_run_metadata(reconciliation, run_metadata)
    path = output / "global_cross_artifact_count_reconciliation.csv"
    reconciliation.to_csv(path, index=False)
    register_artifacts(
        output,
        [
            path,
            output / "global_selected_stocks_report_view.csv",
            output / "global_selected_stocks_report_view_quality.csv",
        ],
        run_metadata,
    )
    failed = reconciliation.loc[reconciliation["status"].astype(str).eq("failed")]
    print(
        "Cross-artifact reconciliation: "
        f"{'passed' if failed.empty else 'failed'}; rows={len(reconciliation)}"
    )
    return 0 if failed.empty else 1


if __name__ == "__main__":
    sys.exit(main())
