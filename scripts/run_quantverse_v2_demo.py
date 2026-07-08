"""Run the QuantVerse v2 public-data quant research demo."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_numerical_integrity import (
    validate_v2_numerical_integrity,
)  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
SUMMARY_PATH = PROCESSED / "quantverse_v2_demo_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_equity_research.yaml")
    args = parser.parse_args()
    config = args.config
    steps = [
        [
            "scripts/validate_source_universe_inputs.py",
            "--config",
            "configs/source_universe_validation.yaml",
        ],
        [
            "scripts/build_current_global_universe.py",
            "--config",
            "configs/current_global_universe.yaml",
        ],
        ["scripts/validate_real_global_universe.py"],
        [
            "scripts/build_global_returns_matrix.py",
            "--config",
            "configs/global_returns_matrix.yaml",
        ],
        ["scripts/build_global_stock_scores.py", "--config", config],
        ["scripts/build_global_return_forecasts.py", "--config", config],
        ["scripts/build_global_portfolio_league.py", "--config", config],
        ["scripts/build_global_portfolio_risk_report.py", "--config", config],
        ["scripts/run_global_walk_forward_validation.py", "--config", config],
        [
            "scripts/run_global_master_portfolio.py",
            "--config",
            "configs/global_master_portfolio.yaml",
        ],
        ["scripts/build_global_model_selection_report.py", "--config", config],
        ["scripts/run_global_robustness_analysis.py", "--config", config],
        ["scripts/build_global_exposure_report.py", "--config", config],
        ["scripts/validate_global_forecasts.py", "--config", config],
        ["scripts/audit_global_scientific_sanity.py"],
        ["scripts/build_visual_scientific_audit_report.py"],
        ["scripts/build_explainable_excel_output.py"],
    ]
    for step in steps:
        result = subprocess.run([sys.executable, *step], cwd=ROOT, check=False)
        if result.returncode != 0:
            _write_summary({"run_status": "failed", "failed_step": " ".join(step)})
            return int(result.returncode)
    summary = build_demo_summary()
    _write_summary(summary)
    for report_step in [
        ["scripts/build_quantverse_v2_visual_analytics.py", "--config", config],
        ["scripts/build_quantverse_v2_research_report.py"],
        ["scripts/build_quantverse_v2_excel_output.py"],
    ]:
        result = subprocess.run([sys.executable, *report_step], cwd=ROOT, check=False)
        if result.returncode != 0:
            return int(result.returncode)
    print(f"QuantVerse v2 demo summary written: {SUMMARY_PATH}")
    return 0


def build_demo_summary() -> dict[str, object]:
    universe = _read_csv(
        ROOT / "data" / "universe" / "current_global_equity_universe.csv"
    )
    returns = _read_csv(PROCESSED / "global_security_simple_returns_usd.csv")
    scores = _read_csv(PROCESSED / "global_stock_scores.csv")
    forecasts = _read_csv(PROCESSED / "global_stock_return_forecasts.csv")
    league = _read_csv(PROCESSED / "global_portfolio_league.csv")
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    risk = _read_csv(PROCESSED / "global_portfolio_risk_report.csv")
    walk_summary = _read_json(PROCESSED / "global_walk_forward_summary.json")
    risk_sanity = _read_csv(PROCESSED / "global_risk_metric_sanity_checks.csv")
    turnover = _read_csv(PROCESSED / "global_walk_forward_turnover.csv")
    decision = _read_json(PROCESSED / "global_master_decision_summary.json")
    model_decision = _read_json(PROCESSED / "global_final_model_decision.json")
    model_selection = _read_csv(PROCESSED / "global_model_selection_report.csv")
    robustness = _read_json(PROCESSED / "global_parameter_sensitivity_summary.json")
    forecast_validation = _read_csv(
        PROCESSED / "global_forecast_validation_by_horizon.csv"
    )
    exposure_warnings = _read_csv(PROCESSED / "global_exposure_warnings.csv")
    exposure_metadata = _read_csv(PROCESSED / "global_exposure_metadata_quality.csv")
    selected = (
        scores.loc[scores["selection_flag"].astype(bool)]
        if "selection_flag" in scores
        else scores.head(0)
    )
    final_model = _final_model(league, model_decision)
    final_weights = (
        weights.loc[weights["model_name"].astype(str).eq(final_model)]
        if not weights.empty and "model_name" in weights
        else pd.DataFrame()
    )
    risk_row = (
        risk.loc[risk["model_name"].astype(str).eq(final_model)].iloc[0].to_dict()
        if not risk.empty
        and "model_name" in risk
        and risk["model_name"].astype(str).eq(final_model).any()
        else {}
    )
    summary = {
        "run_status": "completed",
        "universe_rows": int(len(universe)),
        "assets_with_returns": (
            int(max(returns.shape[1] - 1, 0)) if not returns.empty else 0
        ),
        "stocks_scored": int(len(scores)),
        "stocks_selected": int(len(selected)),
        "forecast_horizons": (
            sorted(forecasts["horizon"].dropna().astype(str).unique().tolist())
            if "horizon" in forecasts
            else []
        ),
        "models_in_league": int(len(league)),
        "models_actually_run": (
            int(league["actual_status"].astype(str).eq("actually_run").sum())
            if "actual_status" in league
            else 0
        ),
        "models_blocked": (
            int(league["actual_status"].astype(str).str.startswith("blocked").sum())
            if "actual_status" in league
            else 0
        ),
        "final_selected_model": final_model,
        "final_public_data_research_model": final_model,
        "institutional_global_master_promotion": "not_promoted",
        "final_selected_holdings": (
            int((final_weights["weight"].abs() > 1e-8).sum())
            if "weight" in final_weights
            else 0
        ),
        "weight_sum": (
            float(final_weights["weight"].sum()) if "weight" in final_weights else 0.0
        ),
        "expected_portfolio_return": _float(risk_row.get("annualized_return")),
        "expected_portfolio_return_label": (
            "annualized arithmetic mean daily simple return from realized "
            "public-data sample; not guaranteed and not personal investment advice"
        ),
        "expected_portfolio_return_warning": str(
            risk_row.get("extreme_metric_warning", "not available")
        ),
        "expected_portfolio_volatility": _float(risk_row.get("annualized_volatility")),
        "expected_portfolio_volatility_label": "annualized volatility of daily simple returns",
        "expected_portfolio_cvar": _float(risk_row.get("cvar_95")),
        "expected_portfolio_cvar_label": "daily historical 95% CVaR; negative values are losses",
        "walk_forward_status": walk_summary.get("walk_forward_status", "missing"),
        "walk_forward_leakage_audit_passed": walk_summary.get(
            "leakage_audit_passed", False
        ),
        "walk_forward_best_model": walk_summary.get("best_model", "missing"),
        "walk_forward_equal_weight_comparison": walk_summary.get(
            "equal_weight_comparison", {}
        ),
        "final_model_selection_method": model_decision.get(
            "final_model_selection_method", "legacy_sharpe_cagr_sort"
        ),
        "final_model_selection_score": model_decision.get(
            "final_model_selection_score"
        ),
        "final_model_selection_decision": model_decision.get(
            "final_decision", "not promoted"
        ),
        "final_model_selection_reason": model_decision.get(
            "final_decision_reason", "Model-selection report is not available."
        ),
        "equal_weight_comparison": model_decision.get(
            "equal_weight_comparison",
            walk_summary.get("equal_weight_comparison", {}),
        ),
        "random_portfolio_percentile": _random_percentile(
            final_model, model_selection=model_selection
        ),
        "robustness_status": robustness.get("robustness_status", "missing"),
        "sensitivity_status": robustness.get("sensitivity_status", "missing"),
        "forecast_validation_status": _forecast_validation_status(forecast_validation),
        "numerical_integrity_status": "pending",
        "numerical_integrity_failed_checks": None,
        "exposure_warnings": _exposure_warnings(exposure_warnings),
        "exposure_metadata_status": _exposure_metadata_status(exposure_metadata),
        "sector_coverage_ratio": _exposure_metadata_float(
            exposure_metadata, "sector_coverage_ratio"
        ),
        "issuer_country_coverage_ratio": _exposure_metadata_float(
            exposure_metadata, "issuer_country_coverage_ratio"
        ),
        "listing_country_vs_issuer_country_warning": _exposure_metadata_bool(
            exposure_metadata, "listing_country_vs_issuer_country_warning"
        ),
        "publish_readiness_status": model_decision.get(
            "publish_readiness_status", "research_with_limitations"
        ),
        "risk_metric_sanity_passed": _all_checks_passed(risk_sanity),
        "transaction_cost_status": _transaction_cost_status(turnover),
        "promotion_decision": decision.get("promotion_decision", "not promoted"),
        "promotion_reason": _promotion_reason(final_model),
        "main_limitations": [
            "Official exact top-100 support remains unavailable.",
            "Point-in-time historical membership remains unavailable.",
            "Delisting/corporate-action institutional evidence remains unavailable.",
            "Walk-forward is current-universe public-data research, not institutional PIT backtest.",
            "Model selection is publish-ready research evidence, not a promoted institutional allocation.",
        ],
        "report_paths": {
            "pdf": "output/pdf/quantverse_v2_research_report.pdf",
            "html": "output/html/quantverse_v2_research_report.html",
            "excel": "output/excel/quantverse_v2_research_output.xlsx",
        },
    }
    numerical_integrity = validate_v2_numerical_integrity(
        ROOT, summary_override=summary
    )
    summary["numerical_integrity_status"] = numerical_integrity["overall_status"]
    summary["numerical_integrity_failed_checks"] = numerical_integrity[
        "failed_check_count"
    ]
    return summary


def _final_model(
    league: pd.DataFrame, model_decision: dict[str, object] | None = None
) -> str:
    if model_decision:
        final = str(model_decision.get("final_selected_model", "")).strip()
        if final:
            return final
    if league.empty:
        return "Policy Constrained"
    constraints_pass = league["constraints_pass"].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes"}
    )
    candidates = league.loc[
        constraints_pass
        & league["actual_status"].astype(str).isin(["actually_run", "benchmark_only"])
    ].copy()
    if candidates.empty:
        return "Equal Weight"
    candidates = candidates.sort_values(["sharpe", "cagr"], ascending=False)
    return str(candidates.iloc[0]["model_name"])


def _random_percentile(
    model: str,
    *,
    model_selection: pd.DataFrame | None = None,
) -> float | None:
    if (
        model_selection is not None
        and not model_selection.empty
        and {"model_name", "random_sharpe_percentile"}.issubset(model_selection)
    ):
        row = model_selection.loc[model_selection["model_name"].astype(str).eq(model)]
        if not row.empty:
            return _float(row["random_sharpe_percentile"].iloc[0])
    league = _read_csv(PROCESSED / "global_portfolio_league.csv")
    if league.empty or "model_name" not in league:
        return None
    model_row = league.loc[league["model_name"].astype(str).eq(model)]
    if model_row.empty or "sharpe" not in model_row:
        return None
    model_sharpe = _float(model_row["sharpe"].iloc[0])
    if model_sharpe is None:
        return None
    random_benchmark = _read_csv(
        PROCESSED / "global_master_random_portfolio_benchmark.csv"
    )
    if not random_benchmark.empty and "Sharpe" in random_benchmark:
        random_sharpes = pd.to_numeric(random_benchmark["Sharpe"], errors="coerce")
        random_sharpes = random_sharpes.dropna()
        if not random_sharpes.empty:
            return float((random_sharpes <= model_sharpe).mean())
    random_row = league.loc[league["model_name"].astype(str).eq("Random Portfolios")]
    if random_row.empty or "sharpe" not in random_row:
        return None
    random_sharpe = _float(random_row["sharpe"].iloc[0])
    if random_sharpe is None:
        return None
    return float(model_sharpe >= random_sharpe)


def _promotion_reason(final_model: str) -> str:
    return (
        f"Final public-data research model: {final_model}. "
        "Institutional/global master promotion: not_promoted. "
        "The current public-data evidence supports the research model label only; "
        "it does not promote an institutional global USD master portfolio or "
        "investment recommendation."
    )


def _all_checks_passed(frame: pd.DataFrame) -> bool:
    if frame.empty or "passed" not in frame:
        return False
    return bool(frame["passed"].map(lambda value: str(value).lower() == "true").all())


def _transaction_cost_status(turnover: pd.DataFrame) -> str:
    if turnover.empty or "transaction_cost_decimal" not in turnover:
        return "not_available"
    total_cost = pd.to_numeric(
        turnover["transaction_cost_decimal"], errors="coerce"
    ).fillna(0.0)
    if float(total_cost.sum()) > 0:
        return "applied_in_walk_forward_net_returns"
    return "no_turnover_cost_observed"


def _forecast_validation_status(frame: pd.DataFrame) -> str:
    if frame.empty or "forecast_validation_status" not in frame:
        return "missing"
    statuses = frame["forecast_validation_status"].dropna().astype(str)
    if statuses.empty:
        return "missing"
    if statuses.eq("failed_scale_sanity").any():
        return "failed_scale_sanity"
    if statuses.eq("diagnostic_only").any():
        return "diagnostic_only"
    return str(statuses.mode().iloc[0])


def _exposure_warnings(frame: pd.DataFrame) -> list[str]:
    if frame.empty or "warning_type" not in frame:
        return ["missing"]
    return frame["warning_type"].dropna().astype(str).head(10).tolist()


def _exposure_metadata_status(frame: pd.DataFrame) -> str:
    if frame.empty or "exposure_metadata_status" not in frame:
        return "missing"
    values = frame["exposure_metadata_status"].dropna().astype(str)
    return str(values.iloc[0]) if not values.empty else "missing"


def _exposure_metadata_float(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return _float(frame[column].iloc[0]) or 0.0


def _exposure_metadata_bool(frame: pd.DataFrame, column: str) -> bool:
    if frame.empty or column not in frame:
        return True
    return str(frame[column].iloc[0]).strip().lower() in {"1", "true", "yes"}


def _write_summary(summary: dict[str, object]) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _float(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main())
