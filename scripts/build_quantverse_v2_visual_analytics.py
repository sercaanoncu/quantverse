"""Build QuantVerse v2 chart-ready visual portfolio analytics outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_visual_analytics import (  # noqa: E402
    VISUAL_ANALYTICS_FILES,
    build_visual_analytics_outputs,
)
from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()

    outputs = build_visual_analytics_outputs(PROCESSED)
    run_metadata = read_run_manifest(PROCESSED)
    for key, frame in outputs.items():
        outputs[key] = attach_run_metadata(frame, run_metadata)
        outputs[key].to_csv(PROCESSED / VISUAL_ANALYTICS_FILES[key], index=False)
    register_artifacts(
        PROCESSED,
        [PROCESSED / filename for filename in VISUAL_ANALYTICS_FILES.values()],
        run_metadata,
    )
    print(f"config={args.config}")
    for key, filename in VISUAL_ANALYTICS_FILES.items():
        frame = outputs[key]
        print(f"{key}={PROCESSED / filename}; rows={len(frame)}")
    validation = outputs["validation"]
    failed = validation.loc[~validation["passed"].astype(bool)]
    if failed.empty:
        print("visual_analytics_status=passed")
        return 0
    print("visual_analytics_status=failed")
    for _, row in failed.iterrows():
        print(f"failed_check={row['check']}; details={row['details']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
