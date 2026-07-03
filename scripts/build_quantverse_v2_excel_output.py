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
    "RISK_METRICS": "data/processed/global_portfolio_risk_report.csv",
    "RISK_CONTRIBUTIONS": "data/processed/global_risk_contribution_report.csv",
    "STRESS_TESTS": "data/processed/global_stress_test_results.csv",
    "WALK_FORWARD": "data/processed/global_walk_forward_model_comparison.csv",
    "BENCHMARK_COMPARISON": "data/processed/global_master_equal_weight_comparison.csv",
    "RANDOM_PORTFOLIOS": "data/processed/global_master_random_portfolio_benchmark.csv",
    "MODEL_SELECTION": "data/processed/global_model_selection_report.csv",
    "ROBUSTNESS": "data/processed/global_robustness_sensitivity.csv",
    "RANDOM_DISTRIBUTION": "data/processed/global_random_portfolio_distribution.csv",
    "RANDOM_PERCENTILES": "data/processed/global_random_portfolio_percentile_report.csv",
    "EXPOSURE_REGION": "data/processed/global_region_exposure.csv",
    "EXPOSURE_COUNTRY": "data/processed/global_country_exposure.csv",
    "EXPOSURE_CURRENCY": "data/processed/global_currency_exposure.csv",
    "EXPOSURE_SECTOR": "data/processed/global_sector_exposure.csv",
    "TOP_HOLDINGS_EXPLANATION": "data/processed/global_top_holdings_explanation.csv",
    "FORECAST_VALIDATION": "data/processed/global_forecast_validation_by_horizon.csv",
    "PUBLISH_READINESS": "data/processed/global_model_selection_report.csv",
    "WARNINGS": "data/processed/global_risk_metric_sanity_checks.csv",
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
        pd.DataFrame(_formula_dictionary()).to_excel(
            writer, sheet_name="APPENDIX_FORMULAS", index=False
        )
    print(f"QuantVerse v2 Excel written: {OUTPUT}")
    return 0


def _start_here() -> list[dict[str, str]]:
    return [
        {
            "section": "What to inspect first",
            "message": "Read EXECUTIVE_SUMMARY, MODEL_SELECTION, FINAL_WEIGHTS, RISK_METRICS, RANDOM_PERCENTILES, ROBUSTNESS, FORECAST_VALIDATION and TOP_HOLDINGS_EXPLANATION before raw tables.",
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
        {
            "section": "Return label",
            "message": "The v2 portfolio return field is an annualized arithmetic estimate from realized daily simple returns, not a guaranteed forecast.",
        },
        {
            "section": "Final model selection",
            "message": "MODEL_SELECTION explains why the final public-data model is chosen; blocked and diagnostic models are not eligible final models.",
        },
        {
            "section": "Publish readiness",
            "message": "PUBLISH_READINESS is evidence for GitHub/CV discussion only; it is not a promoted institutional portfolio approval.",
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


def _formula_dictionary() -> list[dict[str, str]]:
    return [
        {
            "metric": "portfolio daily return",
            "formula": "sum_i(weight_i * simple_return_i)",
            "interpretation": "Simple returns aggregate linearly across portfolio weights for one period.",
        },
        {
            "metric": "annualized_return",
            "formula": "mean(daily_simple_return) * 252",
            "interpretation": "Arithmetic annualized estimate, not a guaranteed future return.",
        },
        {
            "metric": "CAGR",
            "formula": "(1 + total_return) ** (252 / observations) - 1",
            "interpretation": "Compounded realized growth over the sample.",
        },
        {
            "metric": "volatility",
            "formula": "std(daily_simple_return) * sqrt(252)",
            "interpretation": "Annualized dispersion of daily simple returns.",
        },
        {
            "metric": "VaR/CVaR",
            "formula": "5th percentile and mean below that percentile",
            "interpretation": "Daily historical tail loss metrics; negative values indicate losses.",
        },
        {
            "metric": "walk-forward",
            "formula": "train on historical window, test on the next chronological window",
            "interpretation": "Public-data current-universe validation, not institutional point-in-time proof.",
        },
    ]


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
