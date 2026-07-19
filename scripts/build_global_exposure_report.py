"""Build economic exposure interpretation for the QuantVerse v2 final model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_exposure_analysis import (
    build_exposure_analysis,
    write_exposure_outputs,
)
from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _read_config(ROOT / args.config)
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    universe = _read_csv(
        ROOT / "data" / "universe" / "current_global_equity_universe.csv"
    )
    risk_contributions = _read_csv(PROCESSED / "global_risk_contribution_report.csv")
    forecasts = _read_csv(PROCESSED / "global_stock_return_forecasts.csv")
    if weights.empty or universe.empty:
        print("Missing weights or universe; exposure report not built.")
        return 0
    final_model = _final_model()
    available_models = set(weights.get("model_name", pd.Series(dtype=str)).astype(str))
    if final_model == "not_available" or final_model not in available_models:
        print(
            "No explicit final-model decision with matching weights; "
            "exposure report not built."
        )
        return 0
    metadata_cache_dir = config.get(
        "exposure_metadata_cache_dir",
        "data/cache/exposure_metadata/yfinance_profiles",
    )
    metadata_cache_path = Path(str(metadata_cache_dir))
    if not metadata_cache_path.is_absolute():
        metadata_cache_path = ROOT / metadata_cache_path
    exposure = build_exposure_analysis(
        weights,
        universe,
        final_model=final_model,
        risk_contributions=risk_contributions,
        forecasts=forecasts,
        metadata_cache_dir=metadata_cache_path,
        allow_yfinance_metadata=bool(config.get("allow_yfinance_metadata", True)),
        metadata_as_of_date=config.get("metadata_as_of_date"),
    )
    run_metadata = read_run_manifest(PROCESSED)
    exposure = {
        key: attach_run_metadata(frame, run_metadata) for key, frame in exposure.items()
    }
    write_exposure_outputs(exposure, PROCESSED)
    register_artifacts(
        PROCESSED,
        [
            PROCESSED / "global_region_exposure.csv",
            PROCESSED / "global_country_exposure.csv",
            PROCESSED / "global_listing_country_exposure.csv",
            PROCESSED / "global_issuer_country_exposure.csv",
            PROCESSED / "global_economic_country_exposure.csv",
            PROCESSED / "global_currency_exposure.csv",
            PROCESSED / "global_exchange_exposure.csv",
            PROCESSED / "global_sleeve_exposure.csv",
            PROCESSED / "global_sector_exposure.csv",
            PROCESSED / "global_industry_exposure.csv",
            PROCESSED / "global_top_holdings_explanation.csv",
            PROCESSED / "global_exposure_warnings.csv",
            PROCESSED / "global_exposure_metadata_quality.csv",
        ],
        run_metadata,
    )
    print(f"Global exposure report written for final model: {final_model}")
    return 0


def _final_model() -> str:
    decision_path = PROCESSED / "global_final_model_decision.json"
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        return str(decision.get("final_selected_model", "not_available"))
    summary_path = PROCESSED / "quantverse_v2_demo_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return str(summary.get("final_selected_model", "not_available"))
    return "not_available"


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_config(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
