"""Run the QuantVerse v2 public-data quant research demo."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
SUMMARY_PATH = PROCESSED / "quantverse_v2_demo_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
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
    decision = _read_json(PROCESSED / "global_master_decision_summary.json")
    selected = (
        scores.loc[scores["selection_flag"].astype(bool)]
        if "selection_flag" in scores
        else scores.head(0)
    )
    final_model = _final_model(league)
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
    return {
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
        "final_selected_holdings": (
            int((final_weights["weight"].abs() > 1e-8).sum())
            if "weight" in final_weights
            else 0
        ),
        "weight_sum": (
            float(final_weights["weight"].sum()) if "weight" in final_weights else 0.0
        ),
        "expected_portfolio_return": _float(risk_row.get("annualized_return")),
        "expected_portfolio_volatility": _float(risk_row.get("annualized_volatility")),
        "expected_portfolio_cvar": _float(risk_row.get("cvar_95")),
        "walk_forward_status": walk_summary.get("walk_forward_status", "missing"),
        "walk_forward_best_model": walk_summary.get("best_model", "missing"),
        "walk_forward_equal_weight_comparison": walk_summary.get(
            "equal_weight_comparison", {}
        ),
        "random_portfolio_percentile": _random_percentile(final_model),
        "promotion_decision": decision.get("promotion_decision", "not promoted"),
        "promotion_reason": _promotion_reason(
            decision.get("reason", "Public-data research output."),
            final_model,
        ),
        "main_limitations": [
            "Official exact top-100 support remains unavailable.",
            "Point-in-time historical membership remains unavailable.",
            "Delisting/corporate-action institutional evidence remains unavailable.",
            "Walk-forward is current-universe public-data research, not institutional PIT backtest.",
        ],
        "report_paths": {
            "pdf": "output/pdf/quantverse_v2_research_report.pdf",
            "html": "output/html/quantverse_v2_research_report.html",
            "excel": "output/excel/quantverse_v2_research_output.xlsx",
        },
    }


def _final_model(league: pd.DataFrame) -> str:
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


def _random_percentile(model: str) -> float | None:
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


def _promotion_reason(reason: object, final_model: str) -> str:
    base = str(reason or "Public-data research output.")
    return (
        "Existing global master promotion gate remains not promoted. "
        f"Gate reason: {base} "
        f"QuantVerse v2 model league selected {final_model} as the public-data "
        "research final model; this is not a promoted institutional global USD "
        "master portfolio."
    )


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
