"""Build an explainable Excel workbook for global exact/proxy audit outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

WORKBOOK_PATH = Path("output/excel/quantverse_explainable_global_stock_output.xlsx")


def main() -> int:
    output_dir = Path("data/processed")
    WORKBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    classification = _read_csv(
        output_dir / "global_exact_proxy_classification_report.csv"
    )
    issues = _read_csv(output_dir / "global_scientific_sanity_issues.csv")
    bl_report = _read_csv(output_dir / "global_black_litterman_prerequisite_report.csv")
    blockers = _read_csv(output_dir / "global_market_cap_rank_blockers.csv")
    decision = _read_json(output_dir / "global_master_decision_summary.json")

    start_here = pd.DataFrame(
        [
            {
                "item": "Decision",
                "value": decision.get("promotion_decision", "not available"),
                "explanation": "Global master portfolio is not promoted unless source, FX, market-cap/rank and validation gates pass.",
            },
            {
                "item": "First sheet to inspect",
                "value": "EXACT_PROXY_STATUS",
                "explanation": "This sheet shows which sleeves are exact, proxy, manual-review or blocked.",
            },
            {
                "item": "Critical rule",
                "value": "Exact top-100 market-cap claim is not supported for incomplete sleeves.",
                "explanation": "Missing market cap, rank, source URL/provider or as-of date blocks exact status.",
            },
            {
                "item": "Black-Litterman",
                "value": "blocked_by_data unless valid priors exist",
                "explanation": "Positive market cap alone is not enough; source-backed priors are required.",
            },
        ]
    )

    try:
        with pd.ExcelWriter(WORKBOOK_PATH) as writer:
            start_here.to_excel(writer, sheet_name="START_HERE", index=False)
            _safe_sheet(classification, writer, "EXACT_PROXY_STATUS")
            _safe_sheet(issues, writer, "RED_FLAGS")
            _safe_sheet(bl_report, writer, "BLACK_LITTERMAN")
            _safe_sheet(blockers, writer, "BLOCKERS")
        print(f"Excel workbook written: {WORKBOOK_PATH}")
    except ImportError as exc:
        fallback = WORKBOOK_PATH.with_suffix(".start_here.csv")
        start_here.to_csv(fallback, index=False)
        print(f"Excel dependency unavailable ({exc}); CSV fallback written: {fallback}")
    return 0


def _safe_sheet(frame: pd.DataFrame, writer: pd.ExcelWriter, sheet_name: str) -> None:
    if frame.empty:
        frame = pd.DataFrame([{"status": "not available"}])
    frame.to_excel(writer, sheet_name=sheet_name, index=False)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    sys.exit(main())
