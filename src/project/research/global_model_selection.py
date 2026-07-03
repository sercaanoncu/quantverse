"""Robust model-selection and random-benchmark utilities for QuantVerse v2.

This layer does not create new allocation models. It reads existing model
league, walk-forward, risk and benchmark evidence, then decides what can be
called a defensible public-data final model. The decision is deliberately
conservative: a diagnostic or blocked model cannot become the final selected
model, and an active model must improve on Equal Weight after risk and cost
checks before it can displace the benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_portfolio_risk import evaluate_return_series

ELIGIBLE_FINAL_STATUSES = {"actually_run", "benchmark_only"}
EXCLUDED_FINAL_STATUSES = {
    "diagnostic_only",
    "blocked_by_data",
    "blocked_by_implementation",
    "future_candidate",
}

MODEL_SELECTION_COLUMNS = [
    "model_name",
    "model_status",
    "eligible_final_model",
    "constraint_pass",
    "walk_forward_supported",
    "walk_forward_annualized_return",
    "walk_forward_volatility",
    "walk_forward_sharpe",
    "walk_forward_sortino",
    "walk_forward_max_drawdown",
    "walk_forward_cvar_95",
    "transaction_cost_adjusted_return",
    "turnover",
    "effective_holdings",
    "concentration_warning",
    "league_cagr",
    "league_annualized_return",
    "league_sharpe",
    "league_max_drawdown",
    "league_cvar_95",
    "random_return_percentile",
    "random_volatility_percentile",
    "random_sharpe_percentile",
    "random_max_drawdown_percentile",
    "random_cvar_percentile",
    "beats_equal_weight_return_after_costs",
    "beats_equal_weight_sharpe",
    "drawdown_not_materially_worse_than_equal_weight",
    "cvar_not_materially_worse_than_equal_weight",
    "extreme_metric_warning",
    "data_limitation_warning",
    "selection_score",
    "selection_label",
    "rejection_reason",
]

RANDOM_DISTRIBUTION_COLUMNS = [
    "portfolio_id",
    "weight_sum",
    "max_weight_observed",
    "cagr",
    "annualized_return",
    "volatility",
    "sharpe",
    "sortino",
    "max_drawdown",
    "var_95",
    "cvar_95",
    "calmar",
    "total_return",
]

RANDOM_PERCENTILE_COLUMNS = [
    "model_name",
    "return_percentile",
    "volatility_percentile",
    "sharpe_percentile",
    "max_drawdown_percentile",
    "cvar_percentile",
    "better_than_random_median_sharpe",
    "better_than_random_75th_sharpe",
    "better_than_random_90th_sharpe",
    "benchmark_interpretation",
]


def simulate_constrained_random_distribution(
    returns: pd.DataFrame,
    *,
    n_portfolios: int = 1000,
    max_weight: float = 0.10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Simulate capped long-only random portfolios on the same return matrix."""
    clean = _clean_returns(returns)
    if clean.empty:
        return pd.DataFrame(columns=RANDOM_DISTRIBUTION_COLUMNS)
    if float(max_weight) * clean.shape[1] < 1.0 - 1e-12:
        raise ValueError("max_weight is infeasible for the selected universe.")

    rng = np.random.default_rng(int(random_state))
    rows: list[dict[str, float | int]] = []
    for portfolio_id in range(int(n_portfolios)):
        raw = pd.Series(rng.random(clean.shape[1]), index=clean.columns)
        weights = _cap_and_normalize(raw, float(max_weight))
        metrics = evaluate_return_series(clean @ weights)
        rows.append(
            {
                "portfolio_id": portfolio_id,
                "weight_sum": float(weights.sum()),
                "max_weight_observed": float(weights.max()),
                "cagr": float(metrics["cagr"]),
                "annualized_return": float(metrics["annualized_return"]),
                "volatility": float(metrics["annualized_volatility"]),
                "sharpe": float(metrics["sharpe"]),
                "sortino": float(metrics["sortino"]),
                "max_drawdown": float(metrics["max_drawdown"]),
                "var_95": float(metrics["var_95"]),
                "cvar_95": float(metrics["cvar_95"]),
                "calmar": float(metrics["calmar"]),
                "total_return": float(metrics["total_return"]),
            }
        )
    return pd.DataFrame(rows, columns=RANDOM_DISTRIBUTION_COLUMNS)


def build_random_percentile_report(
    league: pd.DataFrame,
    random_distribution: pd.DataFrame,
) -> pd.DataFrame:
    """Compare each executable model with the random portfolio distribution."""
    if league.empty or random_distribution.empty:
        return pd.DataFrame(columns=RANDOM_PERCENTILE_COLUMNS)
    randoms = random_distribution.copy()
    rows: list[dict[str, object]] = []
    for _, row in league.iterrows():
        model = str(row.get("model_name", ""))
        sharpe = _float(row.get("sharpe"))
        annualized_return = _float(row.get("annualized_return"))
        volatility = _float(row.get("volatility"))
        drawdown = _float(row.get("max_drawdown"))
        cvar = _float(row.get("cvar_95"))
        sharpe_percentile = _higher_is_better_percentile(randoms["sharpe"], sharpe)
        rows.append(
            {
                "model_name": model,
                "return_percentile": _higher_is_better_percentile(
                    randoms["annualized_return"], annualized_return
                ),
                "volatility_percentile": _lower_is_better_percentile(
                    randoms["volatility"], volatility
                ),
                "sharpe_percentile": sharpe_percentile,
                "max_drawdown_percentile": _higher_is_better_percentile(
                    randoms["max_drawdown"], drawdown
                ),
                "cvar_percentile": _higher_is_better_percentile(
                    randoms["cvar_95"], cvar
                ),
                "better_than_random_median_sharpe": bool(sharpe_percentile >= 0.50),
                "better_than_random_75th_sharpe": bool(sharpe_percentile >= 0.75),
                "better_than_random_90th_sharpe": bool(sharpe_percentile >= 0.90),
                "benchmark_interpretation": (
                    "Random percentile is a benchmark context, not proof of future superiority."
                ),
            }
        )
    return pd.DataFrame(rows, columns=RANDOM_PERCENTILE_COLUMNS)


def build_model_selection_report(
    league: pd.DataFrame,
    walk_forward: pd.DataFrame | None = None,
    risk_report: pd.DataFrame | None = None,
    turnover: pd.DataFrame | None = None,
    random_percentiles: pd.DataFrame | None = None,
    *,
    drawdown_tolerance: float = 0.05,
    cvar_tolerance: float = 0.01,
) -> pd.DataFrame:
    """Score final model candidates using risk, cost and validation evidence."""
    if league.empty:
        return pd.DataFrame(columns=MODEL_SELECTION_COLUMNS)

    walk_map = _index_by_model(walk_forward)
    risk_map = _index_by_model(risk_report)
    random_map = _index_by_model(random_percentiles)
    turnover_map = _turnover_by_model(turnover)
    equal_weight = _evidence_row(
        "Equal Weight",
        league,
        walk_map,
        risk_map,
        random_map,
        turnover_map,
        drawdown_tolerance=drawdown_tolerance,
        cvar_tolerance=cvar_tolerance,
    )
    rows = []
    for _, _row in league.iterrows():
        model = str(_row.get("model_name", ""))
        rows.append(
            _evidence_row(
                model,
                league,
                walk_map,
                risk_map,
                random_map,
                turnover_map,
                equal_weight=equal_weight,
                drawdown_tolerance=drawdown_tolerance,
                cvar_tolerance=cvar_tolerance,
            )
        )
    frame = pd.DataFrame(rows, columns=MODEL_SELECTION_COLUMNS)
    return frame.sort_values(
        ["eligible_final_model", "selection_score"], ascending=[False, False]
    ).reset_index(drop=True)


def build_final_model_decision(selection_report: pd.DataFrame) -> dict[str, object]:
    """Build a conservative final-model decision from a selection report."""
    if selection_report.empty:
        return {
            "final_selected_model": "Equal Weight",
            "final_model_selection_method": "robust_public_data_evidence_gate",
            "final_model_selection_score": 0.0,
            "final_decision": "not promoted",
            "final_decision_reason": "No model-selection evidence was available.",
            "equal_weight_comparison": {},
            "random_portfolio_percentile": None,
            "publish_readiness_status": "not ready",
        }

    candidates = selection_report.loc[
        selection_report["eligible_final_model"].astype(bool)
    ].copy()
    if candidates.empty:
        final = _equal_weight_or_first(selection_report)
        reason = "No eligible actually-run or benchmark model passed constraints."
        promoted = False
    else:
        active = candidates.loc[~candidates["model_name"].eq("Equal Weight")].copy()
        active["active_gate_pass"] = (
            active["beats_equal_weight_return_after_costs"].astype(bool)
            & active["beats_equal_weight_sharpe"].astype(bool)
            & active["drawdown_not_materially_worse_than_equal_weight"].astype(bool)
            & active["cvar_not_materially_worse_than_equal_weight"].astype(bool)
            & (active["random_sharpe_percentile"].fillna(0.0) >= 0.50)
            & ~active["extreme_metric_warning"]
            .astype(str)
            .str.contains("severe", case=False, na=False)
        )
        if active["active_gate_pass"].any():
            final = (
                active.loc[active["active_gate_pass"]]
                .sort_values("selection_score", ascending=False)
                .iloc[0]
            )
            reason = (
                f"{final['model_name']} is the strongest public-data final model "
                "under walk-forward, risk, cost and random-benchmark evidence. "
                "This is still not investment advice or institutional PIT evidence."
            )
            promoted = False
        else:
            final = _equal_weight_or_first(candidates)
            reason = (
                "Equal Weight remains the defensible benchmark; no active model is "
                "promoted because active candidates did not clearly beat Equal Weight "
                "after costs, drawdown, CVaR and random-benchmark checks."
            )
            promoted = False

    return {
        "final_selected_model": str(final["model_name"]),
        "final_model_selection_method": "robust_public_data_evidence_gate",
        "final_model_selection_score": float(final["selection_score"]),
        "final_decision": "not promoted" if not promoted else "promoted",
        "final_decision_reason": reason,
        "equal_weight_comparison": {
            "beats_equal_weight_return_after_costs": bool(
                final.get("beats_equal_weight_return_after_costs", False)
            ),
            "beats_equal_weight_sharpe": bool(
                final.get("beats_equal_weight_sharpe", False)
            ),
            "drawdown_not_materially_worse_than_equal_weight": bool(
                final.get("drawdown_not_materially_worse_than_equal_weight", False)
            ),
            "cvar_not_materially_worse_than_equal_weight": bool(
                final.get("cvar_not_materially_worse_than_equal_weight", False)
            ),
        },
        "random_portfolio_percentile": _none_if_nan(
            final.get("random_sharpe_percentile")
        ),
        "publish_readiness_status": (
            "research_publish_ready_with_limitations"
            if str(final["model_name"])
            else "not ready"
        ),
        "hard_limitations": [
            "Official exact top-100 support remains unavailable.",
            "Point-in-time historical membership remains unavailable.",
            "Delisting and corporate-action institutional evidence remains unavailable.",
            "Public-data walk-forward is not an institutional PIT backtest.",
        ],
    }


def write_model_selection_outputs(
    selection_report: pd.DataFrame,
    decision: dict[str, object],
    random_distribution: pd.DataFrame,
    random_percentiles: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    """Write model-selection and random-benchmark outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    selection_report.to_csv(path / "global_model_selection_report.csv", index=False)
    random_distribution.to_csv(
        path / "global_random_portfolio_distribution.csv", index=False
    )
    random_percentiles.to_csv(
        path / "global_random_portfolio_percentile_report.csv", index=False
    )
    (path / "global_final_model_decision.json").write_text(
        json.dumps(decision, indent=2, default=str), encoding="utf-8"
    )


def _evidence_row(
    model: str,
    league: pd.DataFrame,
    walk_map: dict[str, pd.Series],
    risk_map: dict[str, pd.Series],
    random_map: dict[str, pd.Series],
    turnover_map: dict[str, float],
    *,
    equal_weight: dict[str, object] | None = None,
    drawdown_tolerance: float,
    cvar_tolerance: float,
) -> dict[str, object]:
    league_row = league.loc[league["model_name"].astype(str).eq(model)]
    league_row = league_row.iloc[0] if not league_row.empty else pd.Series(dtype=object)
    walk = walk_map.get(model, pd.Series(dtype=object))
    risk = risk_map.get(model, pd.Series(dtype=object))
    random_row = random_map.get(model, pd.Series(dtype=object))

    status = str(league_row.get("actual_status", "blocked_by_implementation"))
    constraint_pass = _bool(league_row.get("constraints_pass", False))
    eligible = bool(
        status in ELIGIBLE_FINAL_STATUSES
        and constraint_pass
        and model != "Random Portfolios"
    )
    wf_supported = not walk.empty
    wf_return = _coalesce_float(
        walk.get("avg_annualized_return"),
        league_row.get("annualized_return"),
    )
    wf_vol = _coalesce_float(walk.get("avg_volatility"), league_row.get("volatility"))
    wf_sharpe = _coalesce_float(walk.get("avg_sharpe"), league_row.get("sharpe"))
    wf_sortino = _coalesce_float(walk.get("avg_sortino"), league_row.get("sortino"))
    wf_drawdown = _coalesce_float(
        walk.get("avg_max_drawdown"), league_row.get("max_drawdown")
    )
    wf_cvar = _coalesce_float(walk.get("avg_cvar_95"), league_row.get("cvar_95"))
    model_turnover = _coalesce_float(
        walk.get("avg_turnover"),
        turnover_map.get(model),
        league_row.get("turnover"),
        0.0,
    )
    random_sharpe = _float(random_row.get("sharpe_percentile"))
    if np.isnan(random_sharpe):
        random_sharpe = _float(random_row.get("random_sharpe_percentile"))

    if equal_weight is None:
        ew_return = wf_return
        ew_sharpe = wf_sharpe
        ew_drawdown = wf_drawdown
        ew_cvar = wf_cvar
    else:
        ew_return = _float(equal_weight["transaction_cost_adjusted_return"])
        ew_sharpe = _float(equal_weight["walk_forward_sharpe"])
        ew_drawdown = _float(equal_weight["walk_forward_max_drawdown"])
        ew_cvar = _float(equal_weight["walk_forward_cvar_95"])

    beats_return = (
        bool(wf_return > ew_return + 1e-12) if model != "Equal Weight" else True
    )
    beats_sharpe = (
        bool(wf_sharpe > ew_sharpe + 1e-12) if model != "Equal Weight" else True
    )
    drawdown_ok = (
        bool(wf_drawdown >= ew_drawdown - float(drawdown_tolerance))
        if model != "Equal Weight"
        else True
    )
    cvar_ok = (
        bool(wf_cvar >= ew_cvar - float(cvar_tolerance))
        if model != "Equal Weight"
        else True
    )
    warning = _warning_from_risk(risk)
    data_warning = (
        "public_data_current_universe_not_institutional_pit; "
        "official_exact_top100_and_delisting_evidence_missing"
    )
    score = _selection_score(
        eligible=eligible,
        walk_forward_supported=wf_supported,
        wf_return=wf_return,
        wf_vol=wf_vol,
        wf_sharpe=wf_sharpe,
        wf_drawdown=wf_drawdown,
        wf_cvar=wf_cvar,
        turnover=model_turnover,
        random_sharpe_percentile=random_sharpe,
        concentration_warning=str(league_row.get("concentration_warning", "none")),
        warning=warning,
    )
    rejection = _rejection_reason(
        model=model,
        status=status,
        eligible=eligible,
        constraint_pass=constraint_pass,
        beats_return=beats_return,
        beats_sharpe=beats_sharpe,
        drawdown_ok=drawdown_ok,
        cvar_ok=cvar_ok,
        random_sharpe=random_sharpe,
        warning=warning,
    )
    return {
        "model_name": model,
        "model_status": status,
        "eligible_final_model": eligible,
        "constraint_pass": constraint_pass,
        "walk_forward_supported": wf_supported,
        "walk_forward_annualized_return": wf_return,
        "walk_forward_volatility": wf_vol,
        "walk_forward_sharpe": wf_sharpe,
        "walk_forward_sortino": wf_sortino,
        "walk_forward_max_drawdown": wf_drawdown,
        "walk_forward_cvar_95": wf_cvar,
        "transaction_cost_adjusted_return": wf_return,
        "turnover": model_turnover,
        "effective_holdings": _float(league_row.get("effective_holdings")),
        "concentration_warning": str(league_row.get("concentration_warning", "none")),
        "league_cagr": _float(league_row.get("cagr")),
        "league_annualized_return": _float(league_row.get("annualized_return")),
        "league_sharpe": _float(league_row.get("sharpe")),
        "league_max_drawdown": _float(league_row.get("max_drawdown")),
        "league_cvar_95": _float(league_row.get("cvar_95")),
        "random_return_percentile": _float(random_row.get("return_percentile")),
        "random_volatility_percentile": _float(random_row.get("volatility_percentile")),
        "random_sharpe_percentile": random_sharpe,
        "random_max_drawdown_percentile": _float(
            random_row.get("max_drawdown_percentile")
        ),
        "random_cvar_percentile": _float(random_row.get("cvar_percentile")),
        "beats_equal_weight_return_after_costs": beats_return,
        "beats_equal_weight_sharpe": beats_sharpe,
        "drawdown_not_materially_worse_than_equal_weight": drawdown_ok,
        "cvar_not_materially_worse_than_equal_weight": cvar_ok,
        "extreme_metric_warning": warning,
        "data_limitation_warning": data_warning,
        "selection_score": score,
        "selection_label": _selection_label(model, eligible, status),
        "rejection_reason": rejection,
    }


def _selection_score(
    *,
    eligible: bool,
    walk_forward_supported: bool,
    wf_return: float,
    wf_vol: float,
    wf_sharpe: float,
    wf_drawdown: float,
    wf_cvar: float,
    turnover: float,
    random_sharpe_percentile: float,
    concentration_warning: str,
    warning: str,
) -> float:
    if not eligible:
        return -1_000_000.0
    score = 0.0
    score += 3.0 * np.nan_to_num(wf_sharpe, nan=0.0)
    score += 1.0 * np.nan_to_num(wf_return, nan=0.0)
    score -= 0.75 * np.nan_to_num(wf_vol, nan=0.0)
    score += 2.0 * np.nan_to_num(wf_drawdown, nan=0.0)
    score += 1.5 * np.nan_to_num(wf_cvar, nan=0.0)
    score -= 0.50 * np.nan_to_num(turnover, nan=0.0)
    score += 1.0 * np.nan_to_num(random_sharpe_percentile, nan=0.0)
    if walk_forward_supported:
        score += 0.50
    if "high_concentration" in concentration_warning:
        score -= 0.75
    if warning and warning != "none":
        score -= 1.00
    return float(score)


def _rejection_reason(
    *,
    model: str,
    status: str,
    eligible: bool,
    constraint_pass: bool,
    beats_return: bool,
    beats_sharpe: bool,
    drawdown_ok: bool,
    cvar_ok: bool,
    random_sharpe: float,
    warning: str,
) -> str:
    reasons: list[str] = []
    if not eligible:
        if model == "Random Portfolios":
            reasons.append(
                "excluded from final selection because it is a benchmark distribution"
            )
        if status in EXCLUDED_FINAL_STATUSES:
            reasons.append(f"excluded from final selection because status is {status}")
        if not constraint_pass:
            reasons.append("constraints did not pass")
    if model != "Equal Weight":
        if not beats_return:
            reasons.append("net annualized return is not greater than Equal Weight")
        if not beats_sharpe:
            reasons.append("Sharpe is not greater than Equal Weight")
        if not drawdown_ok:
            reasons.append("drawdown is materially worse than Equal Weight")
        if not cvar_ok:
            reasons.append("CVaR is materially worse than Equal Weight")
        if random_sharpe < 0.50:
            reasons.append("Sharpe is below random median benchmark")
    if warning and warning != "none":
        reasons.append(f"metric warning: {warning}")
    return "; ".join(reasons) if reasons else "passes conservative selection checks"


def _selection_label(model: str, eligible: bool, status: str) -> str:
    if not eligible:
        return "excluded_from_final_selection"
    if model == "Equal Weight":
        return "defensible_benchmark"
    if status == "benchmark_only":
        return "benchmark"
    return "active_candidate"


def _equal_weight_or_first(frame: pd.DataFrame) -> pd.Series:
    ew = frame.loc[frame["model_name"].eq("Equal Weight")]
    if not ew.empty:
        return ew.iloc[0]
    return frame.sort_values("selection_score", ascending=False).iloc[0]


def _warning_from_risk(risk: pd.Series) -> str:
    warning = str(risk.get("extreme_metric_warning", "none"))
    if warning.lower() in {"", "nan", "none"}:
        return "none"
    return warning


def _index_by_model(frame: pd.DataFrame | None) -> dict[str, pd.Series]:
    if frame is None or frame.empty or "model_name" not in frame:
        return {}
    return {
        str(model): group.iloc[0]
        for model, group in frame.groupby(frame["model_name"].astype(str), sort=False)
    }


def _turnover_by_model(frame: pd.DataFrame | None) -> dict[str, float]:
    if (
        frame is None
        or frame.empty
        or "model_name" not in frame
        or "turnover" not in frame
    ):
        return {}
    grouped = frame.copy()
    grouped["turnover"] = pd.to_numeric(grouped["turnover"], errors="coerce")
    return (
        grouped.groupby(grouped["model_name"].astype(str))["turnover"].mean().to_dict()
    )


def _higher_is_better_percentile(series: pd.Series, value: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or not np.isfinite(value):
        return float("nan")
    return float((clean <= value).mean())


def _lower_is_better_percentile(series: pd.Series, value: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or not np.isfinite(value):
        return float("nan")
    return float((clean >= value).mean())


def _cap_and_normalize(weights: pd.Series, max_weight: float) -> pd.Series:
    raw = pd.Series(weights, dtype=float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    raw = raw.clip(lower=0.0)
    if raw.sum() <= 0:
        raw = pd.Series(1.0, index=raw.index)
    remaining = list(raw.index)
    capped = pd.Series(0.0, index=raw.index, dtype=float)
    remaining_total = 1.0
    while remaining:
        base = raw.loc[remaining]
        provisional = base / base.sum() * remaining_total
        over = provisional[provisional > max_weight + 1e-12]
        if over.empty:
            capped.loc[remaining] = provisional
            break
        capped.loc[over.index] = max_weight
        remaining_total -= max_weight * len(over)
        remaining = [ticker for ticker in remaining if ticker not in set(over.index)]
    return capped / capped.sum()


def _clean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(clean.columns[0])
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.dropna(axis=1, how="all").dropna(how="all")


def _coalesce_float(*values: object) -> float:
    for value in values:
        converted = _float(value)
        if np.isfinite(converted):
            return converted
    return 0.0


def _float(value: object) -> float:
    try:
        if value is None or pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _none_if_nan(value: object) -> float | None:
    converted = _float(value)
    return None if not np.isfinite(converted) else converted


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}
