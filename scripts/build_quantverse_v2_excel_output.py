"""Build QuantVerse v2 explainable Excel workbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "excel" / "quantverse_v2_research_output.xlsx"


SHEETS = {
    "UNIVERSE": "data/universe/current_global_equity_universe.csv",
    "STOCK_SCORES": "data/processed/global_stock_scores.csv",
    "SELECTED_STOCKS": "data/processed/global_stock_scores.csv",
    "RETURN_FORECASTS": "data/processed/global_stock_return_forecasts.csv",
    "MODEL_LEAGUE": "data/processed/global_portfolio_league.csv",
    "FINAL_WEIGHTS": "data/processed/global_portfolio_league_weights.csv",
    "RISK_REPORT": "data/processed/global_portfolio_risk_report.csv",
    "RISK_CONTRIBUTIONS": "data/processed/global_risk_contribution_report.csv",
    "STRESS_TESTS": "data/processed/global_stress_test_results.csv",
    "WALK_FORWARD": "data/processed/global_walk_forward_model_comparison.csv",
    "RANDOM_BENCHMARK": "data/processed/global_master_random_portfolio_benchmark.csv",
    "AUDIT_RED_FLAGS": "data/processed/global_scientific_sanity_issues.csv",
    "CLAIM_CONTROL": "data/processed/global_exact_proxy_classification_report.csv",
}


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    summary = _summary_rows()
    with pd.ExcelWriter(OUTPUT, engine="xlsxwriter") as writer:
        pd.DataFrame(_start_here()).to_excel(
            writer, sheet_name="START_HERE", index=False
        )
        pd.DataFrame(summary).to_excel(
            writer, sheet_name="EXECUTIVE_SUMMARY", index=False
        )
        for sheet, raw_path in SHEETS.items():
            frame = _read_csv(ROOT / raw_path)
            if (
                sheet == "SELECTED_STOCKS"
                and not frame.empty
                and "selection_flag" in frame
            ):
                frame = frame.loc[frame["selection_flag"].astype(bool)]
            frame.to_excel(writer, sheet_name=sheet[:31], index=False)
        pd.DataFrame(_appendix()).to_excel(
            writer, sheet_name="APPENDIX_RAW_TABLES", index=False
        )
    print(f"QuantVerse v2 Excel written: {OUTPUT}")
    return 0


def _start_here() -> list[dict[str, str]]:
    return [
        {
            "section": "What to inspect first",
            "message": "Read EXECUTIVE_SUMMARY, MODEL_LEAGUE, FINAL_WEIGHTS and WALK_FORWARD before raw tables.",
        },
        {
            "section": "Trust status",
            "message": "This is public-data research output, not investment advice or institutional PIT evidence.",
        },
        {
            "section": "Blocked claims",
            "message": "Official exact top-100 and institutional point-in-time claims remain unsupported.",
        },
        {
            "section": "Weights",
            "message": "Full model weights are in FINAL_WEIGHTS; final model is reported in EXECUTIVE_SUMMARY.",
        },
    ]


def _summary_rows() -> list[dict[str, object]]:
    summary = _read_json(PROCESSED / "quantverse_v2_demo_summary.json")
    return [{"metric": key, "value": value} for key, value in summary.items()]


def _appendix() -> list[dict[str, str]]:
    return [
        {
            "artifact": path.name,
            "path": str(path),
            "note": "Generated local evidence; not committed.",
        }
        for path in sorted(PROCESSED.glob("global_*.csv"))
    ]


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
