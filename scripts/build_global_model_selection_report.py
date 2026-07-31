"""Build robust QuantVerse v2 model-selection and random-benchmark reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
    build_random_percentile_report,
    simulate_constrained_random_distribution,
    write_model_selection_outputs,
)  # noqa: E402
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
    config = _config(args.config).get("v2", {})
    league = _read_csv(PROCESSED / "global_portfolio_league.csv")
    returns = _read_returns(PROCESSED / "global_security_simple_returns_usd.csv")
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    risk = _read_csv(PROCESSED / "global_portfolio_risk_report.csv")
    walk = _read_csv(PROCESSED / "global_walk_forward_model_comparison.csv")
    leakage_audit = _read_csv(PROCESSED / "global_walk_forward_leakage_audit.csv")
    turnover = _read_csv(PROCESSED / "global_walk_forward_turnover.csv")
    forecast_validation = _read_csv(
        PROCESSED / "global_forecast_validation_by_horizon.csv"
    )
    robustness = _read_json(PROCESSED / "global_parameter_sensitivity_summary.json")
    random_provenance = _read_json(
        PROCESSED / "global_walk_forward_random_benchmark_provenance.json"
    )
    run_metadata = read_run_manifest(PROCESSED)
    if league.empty or returns.empty:
        print("Missing league or returns; model selection report not built.")
        return 0
    oos_random = _read_csv(PROCESSED / "global_walk_forward_random_distribution.csv")
    if (
        not oos_random.empty
        and "benchmark_scope" in oos_random
        and oos_random["benchmark_scope"].astype(str).eq("walk_forward_oos_net").all()
    ):
        random_distribution = oos_random
        benchmark_model_metrics = _oos_model_metrics(league, walk)
    else:
        selected_tickers = _selected_tickers_from_weights(weights, returns)
        selected_returns = returns[selected_tickers] if selected_tickers else returns
        random_distribution = simulate_constrained_random_distribution(
            selected_returns,
            n_portfolios=int(config.get("random_portfolio_samples", 1000)),
            max_weight=float(config.get("max_weight", 0.10)),
            random_state=int(config.get("random_state", 42)),
        )
        random_distribution["benchmark_scope"] = "full_sample_static_weights_diagnostic"
        benchmark_model_metrics = league
    random_percentiles = build_random_percentile_report(
        benchmark_model_metrics,
        random_distribution,
    )
    selection = build_model_selection_report(
        league,
        walk_forward=walk,
        risk_report=risk,
        turnover=turnover,
        random_percentiles=random_percentiles,
        random_distribution=random_distribution,
        walk_forward_leakage_audit=leakage_audit,
        drawdown_tolerance=float(
            config.get("max_drawdown_worsening_vs_equal_weight", 0.05)
        ),
        cvar_tolerance=float(config.get("max_cvar_worsening_vs_equal_weight", 0.005)),
        min_sharpe_improvement_vs_equal_weight=float(
            config.get("min_sharpe_improvement_vs_equal_weight", 0.10)
        ),
        min_random_sharpe_percentile=float(
            config.get("min_random_sharpe_percentile", 0.60)
        ),
        max_turnover=float(config.get("max_turnover", 2.0)),
        forecast_validation_status=_forecast_validation_status(forecast_validation),
        robustness_evidence=robustness,
        random_benchmark_provenance=random_provenance,
        expected_run_identity=run_metadata,
        expected_random_protocol={
            "train_window_days": int(config.get("walk_forward_train_days", 504)),
            "test_window_days": int(config.get("walk_forward_test_days", 21)),
            "step_days": int(config.get("walk_forward_step_days", 21)),
            "max_assets": int(config.get("walk_forward_max_assets", 20)),
            "max_weight": float(config.get("max_weight", 0.10)),
            "transaction_cost_bps": float(config.get("transaction_cost_bps", 10.0)),
        },
    )
    decision = build_final_model_decision(selection)
    selection = attach_run_metadata(selection, run_metadata)
    random_distribution = attach_run_metadata(random_distribution, run_metadata)
    random_percentiles = attach_run_metadata(random_percentiles, run_metadata)
    decision.update(run_metadata)
    write_model_selection_outputs(
        selection,
        decision,
        random_distribution,
        random_percentiles,
        PROCESSED,
    )
    role_outputs = _write_portfolio_role_outputs(decision, weights, run_metadata)
    register_artifacts(
        PROCESSED,
        [
            PROCESSED / "global_model_selection_report.csv",
            PROCESSED / "global_model_selection_diagnostics.csv",
            PROCESSED / "global_final_model_decision.csv",
            PROCESSED / "global_final_model_decision.json",
            PROCESSED / "global_random_portfolio_distribution.csv",
            PROCESSED / "global_random_portfolio_percentile_report.csv",
            *role_outputs,
        ],
        run_metadata,
    )
    print(
        "Global model selection report written: "
        f"{len(selection)} models; final={decision['final_selected_model']}"
    )
    return 0


def _selected_tickers_from_weights(
    weights: pd.DataFrame, returns: pd.DataFrame
) -> list[str]:
    if weights.empty or "ticker" not in weights:
        return list(returns.columns)
    tickers = weights["ticker"].dropna().astype(str).drop_duplicates().tolist()
    selected = [ticker for ticker in tickers if ticker in returns.columns]
    return selected or list(returns.columns)


def _write_portfolio_role_outputs(
    decision: dict[str, object],
    weights: pd.DataFrame,
    run_metadata: dict[str, object],
) -> list[Path]:
    roles = [
        ("balanced_research_portfolio", decision.get("balanced_research_portfolio")),
        ("transparent_benchmark", decision.get("transparent_benchmark")),
        ("defensive_alternative", decision.get("defensive_alternative")),
    ]
    role_frame = pd.DataFrame(
        [{"portfolio_role": role, "model_name": str(model)} for role, model in roles]
    )
    selected = _read_csv(PROCESSED / "global_current_selected_securities.csv")
    rows = []
    for role, model in roles:
        model_name = str(model)
        model_weights = weights.loc[
            weights["model_name"].astype(str).eq(model_name),
            ["model_name", "ticker", "weight"],
        ].copy()
        if model_weights.empty:
            raise ValueError(f"Missing current weights for portfolio role {role}.")
        model_weights.insert(0, "portfolio_role", role)
        rows.append(model_weights)
    role_weights = pd.concat(rows, ignore_index=True)
    if not selected.empty:
        keep = [
            column
            for column in [
                "ticker",
                "name",
                "issuer_name",
                "issuer_key",
                "sector",
                "industry",
                "issuer_country",
                "currency",
                "composite_quant_score",
                "momentum_6m",
                "momentum_12m",
                "volatility_12m",
                "downside_volatility",
                "max_drawdown",
                "correlation_diversification_score",
                "selection_reason",
            ]
            if column in selected
        ]
        role_weights = role_weights.merge(
            selected[keep].drop_duplicates("ticker"),
            on="ticker",
            how="left",
            validate="many_to_one",
        )
    role_frame = attach_run_metadata(role_frame, run_metadata)
    role_weights = attach_run_metadata(role_weights, run_metadata)
    role_path = PROCESSED / "global_portfolio_roles.csv"
    weights_path = PROCESSED / "global_current_portfolio_weights.csv"
    decision_path = PROCESSED / "global_portfolio_decision_summary.csv"
    role_frame.to_csv(role_path, index=False)
    role_weights.to_csv(weights_path, index=False)
    decision_summary = pd.DataFrame(
        [
            {
                "evidence_status": decision.get("evidence_status"),
                "balanced_research_portfolio": decision.get(
                    "balanced_research_portfolio"
                ),
                "transparent_benchmark": decision.get("transparent_benchmark"),
                "defensive_alternative": decision.get("defensive_alternative"),
                "balanced_selection_reason": decision.get("final_decision_reason"),
                "defensive_selection_reason": decision.get(
                    "defensive_selection_reason"
                ),
                "institutional_live_trading_status": decision.get(
                    "institutional_live_trading_status"
                ),
            }
        ]
    )
    attach_run_metadata(decision_summary, run_metadata).to_csv(
        decision_path, index=False
    )
    return [role_path, weights_path, decision_path]


def _oos_model_metrics(
    league: pd.DataFrame,
    walk: pd.DataFrame,
) -> pd.DataFrame:
    if walk.empty or "model_name" not in walk:
        return league.iloc[0:0].copy()
    aliases = {
        "annualized_return": ["oos_annualized_return", "avg_annualized_return"],
        "volatility": ["oos_volatility", "avg_volatility"],
        "sharpe": ["oos_sharpe", "avg_sharpe"],
        "max_drawdown": ["oos_max_drawdown", "avg_max_drawdown"],
        "cvar_95": ["oos_cvar_95", "avg_cvar_95"],
    }
    output = pd.DataFrame({"model_name": walk["model_name"].astype(str)})
    for target, candidates in aliases.items():
        source = next((column for column in candidates if column in walk), None)
        output[target] = (
            pd.to_numeric(walk[source], errors="coerce") if source else float("nan")
        )
    return output.dropna(
        subset=[
            "annualized_return",
            "volatility",
            "sharpe",
            "max_drawdown",
            "cvar_95",
        ],
        how="any",
    )


def _config(path: str) -> dict:
    config_path = ROOT / path
    return (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_returns(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame


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


if __name__ == "__main__":
    sys.exit(main())
