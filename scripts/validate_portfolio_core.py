"""Validate the canonical QuantVerse working portfolio before publication."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.portfolio_core_validation import (  # noqa: E402
    validate_working_portfolio_core,
)
from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8")) or {}
    result = validate_working_portfolio_core(ROOT, config)
    processed = ROOT / "data" / "processed"
    run_metadata = read_run_manifest(processed)
    result.update(run_metadata)
    checks_path = processed / "global_portfolio_core_acceptance.csv"
    summary_path = processed / "global_portfolio_core_acceptance.json"
    attach_run_metadata(pd.DataFrame(result["checks"]), run_metadata).to_csv(
        checks_path, index=False
    )
    summary_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    register_artifacts(processed, [checks_path, summary_path], run_metadata)
    print(
        "portfolio_core_acceptance="
        f"{result['overall_status']} ({result['check_count'] - result['failed_check_count']}/"
        f"{result['check_count']})"
    )
    return 0 if result["overall_status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
