"""QuantVerse v2 model league for public-data portfolio research."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.optimization.black_litterman import black_litterman_weights
from project.optimization.constraints import PortfolioConstraints
from project.optimization.hierarchical import HRPOptimizer
from project.optimization.risk_parity import RiskParityOptimizer
from project.research.global_portfolio_risk import evaluate_return_series
from project.research.global_stock_selection import (
    build_equal_weight_portfolio,
    build_inverse_volatility_portfolio,
    build_min_cvar_portfolio,
    build_shrinkage_max_sharpe_portfolio,
)

REQUIRED_MODELS = [
    "Equal Weight",
    "Random Portfolios",
    "Inverse Volatility",
    "GMV",
    "Max Sharpe",
    "Min CVaR",
    "HRP",
    "Risk Parity",
    "Black-Litterman",
    "ML Forecast",
    "Ensemble Forecast",
    "Forecast-Enhanced Constrained Portfolio",
    "Policy Constrained",
]

LEAGUE_COLUMNS = [
    "model_name",
    "model_family",
    "objective",
    "actual_status",
    "prerequisites",
    "prerequisites_satisfied",
    "expected_return_source",
    "covariance_source",
    "uses_forecast",
    "uses_market_cap_prior",
    "weight_sum",
    "negative_weight_count",
    "max_weight",
    "effective_holdings",
    "concentration_warning",
    "cagr",
    "annualized_return",
    "volatility",
    "sharpe",
    "sortino",
    "max_drawdown",
    "var_95",
    "cvar_95",
    "turnover",
    "transaction_cost_assumption",
    "constraints_pass",
    "promotion_eligible",
    "rejection_reason",
    "interpretation",
]


def build_portfolio_league(
    returns: pd.DataFrame,
    scores: pd.DataFrame,
    forecasts: pd.DataFrame | None = None,
    metadata: pd.DataFrame | None = None,
    *,
    max_assets: int = 40,
    max_weight: float = 0.10,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the v2 model league and long-form model weights."""
    clean = _clean_returns(returns)
    selected = _selected_tickers(scores, clean, max_assets=max_assets)
    if not selected:
        return (
            pd.DataFrame(columns=LEAGUE_COLUMNS),
            pd.DataFrame(columns=["model_name", "ticker", "weight"]),
            pd.DataFrame(columns=["model_name", "actual_status", "reason"]),
        )
    selected_returns = clean[selected]
    forecast_mu = _forecast_expected_returns(forecasts, selected)
    caps = _market_caps(metadata, selected)
    weights: dict[str, pd.Series] = {}
    statuses: dict[str, dict[str, object]] = {}

    _try_add(
        weights,
        statuses,
        "Equal Weight",
        lambda: build_equal_weight_portfolio(selected_returns, selected),
        "benchmark_only",
        "Transparent 1/N benchmark.",
    )
    random_metrics = _random_portfolio_row(
        selected_returns, max_weight=max_weight, random_state=random_state
    )
    _try_add(
        weights,
        statuses,
        "Inverse Volatility",
        lambda: build_inverse_volatility_portfolio(
            selected_returns, selected, max_weight=max_weight
        ),
        "actually_run",
        "Risk-scaled long-only allocation.",
    )
    _try_add(
        weights,
        statuses,
        "GMV",
        lambda: _gmv_weights(selected_returns, max_weight=max_weight),
        "actually_run",
        "Global minimum variance allocation.",
    )
    _try_add(
        weights,
        statuses,
        "Max Sharpe",
        lambda: build_shrinkage_max_sharpe_portfolio(
            selected_returns, selected, max_weight=max_weight
        ),
        "diagnostic_only",
        "Expected-return optimizer; diagnostic until walk-forward evidence supports it.",
    )
    _try_add(
        weights,
        statuses,
        "Min CVaR",
        lambda: build_min_cvar_portfolio(
            selected_returns, selected, max_weight=max_weight
        ),
        "actually_run",
        "Tail-risk-aware long-only allocation.",
    )
    _try_add(
        weights,
        statuses,
        "HRP",
        lambda: HRPOptimizer(selected_returns).optimize(
            constraints=PortfolioConstraints.default_long_only(max_weight=max_weight)
        )["weights"],
        "actually_run",
        "Hierarchical risk allocation.",
    )
    _try_add(
        weights,
        statuses,
        "Risk Parity",
        lambda: RiskParityOptimizer(selected_returns.cov() * 252).optimize(
            constraints=PortfolioConstraints.default_long_only(max_weight=max_weight)
        )["weights"],
        "actually_run",
        "Equal-risk-contribution allocation.",
    )
    if caps.notna().all() and (caps > 0).all():
        _try_add(
            weights,
            statuses,
            "Black-Litterman",
            lambda: black_litterman_weights(
                selected_returns.cov() * 252, caps, max_weight=max_weight
            ),
            "diagnostic_only",
            "Uses public-provider current market caps; not promotion-grade PIT priors.",
        )
    else:
        statuses["Black-Litterman"] = _status(
            "blocked_by_data",
            "Positive market-cap priors are missing for at least one selected asset.",
        )
    statuses["ML Forecast"] = _status(
        (
            "diagnostic_only"
            if forecasts is not None and not forecasts.empty
            else "blocked_by_data"
        ),
        "Forecast diagnostics are available but are not a standalone allocation model.",
    )
    statuses["Ensemble Forecast"] = _status(
        "diagnostic_only" if forecast_mu.notna().any() else "blocked_by_data",
        "Ensemble expected returns require generated forecasts.",
    )
    if forecast_mu.notna().all():
        _try_add(
            weights,
            statuses,
            "Forecast-Enhanced Constrained Portfolio",
            lambda: _forecast_enhanced_weights(
                selected_returns, forecast_mu, max_weight=max_weight
            ),
            "diagnostic_only",
            "Uses forecast ensemble under long-only cap constraints.",
        )
    else:
        statuses["Forecast-Enhanced Constrained Portfolio"] = _status(
            "blocked_by_data",
            "Forecasts are missing for at least one selected asset.",
        )
    _try_add(
        weights,
        statuses,
        "Policy Constrained",
        lambda: _policy_constrained(scores, selected, max_weight=max_weight),
        "actually_run",
        "Composite-score allocation projected onto long-only capped simplex.",
    )

    league_rows = [random_metrics]
    weight_rows = []
    for model in REQUIRED_MODELS:
        if model == "Random Portfolios":
            continue
        status = statuses.get(model, _status("blocked_by_implementation", "Not run."))
        model_weights = weights.get(model)
        league_rows.append(
            _league_row(model, selected_returns, model_weights, status, max_weight)
        )
        if model_weights is not None:
            weight_rows.extend(
                {
                    "model_name": model,
                    "ticker": ticker,
                    "weight": float(weight),
                }
                for ticker, weight in model_weights.items()
            )
    league = pd.DataFrame(league_rows).reindex(columns=LEAGUE_COLUMNS)
    model_status = pd.DataFrame(
        [
            {
                "model_name": model,
                "actual_status": (
                    statuses.get(model, {}).get("actual_status", "benchmark_only")
                    if model != "Random Portfolios"
                    else "benchmark_only"
                ),
                "reason": (
                    statuses.get(model, {}).get("reason", "Benchmark distribution.")
                    if model != "Random Portfolios"
                    else "Random benchmark distribution."
                ),
            }
            for model in REQUIRED_MODELS
        ]
    )
    return league, pd.DataFrame(weight_rows), model_status


def write_portfolio_league_outputs(
    league: pd.DataFrame,
    weights: pd.DataFrame,
    status: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    """Write league outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    league.to_csv(path / "global_portfolio_league.csv", index=False)
    weights.to_csv(path / "global_portfolio_league_weights.csv", index=False)
    status.to_csv(path / "global_portfolio_model_status.csv", index=False)


def _try_add(
    weights: dict[str, pd.Series],
    statuses: dict[str, dict[str, object]],
    model: str,
    builder,
    status: str,
    reason: str,
) -> None:
    try:
        built = pd.Series(builder(), dtype=float)
        if built.sum() > 0:
            weights[model] = built / built.sum()
            statuses[model] = _status(status, reason)
        else:
            statuses[model] = _status("blocked_by_implementation", "Zero-sum weights.")
    except Exception as exc:
        statuses[model] = _status("blocked_by_implementation", str(exc))


def _league_row(
    model: str,
    returns: pd.DataFrame,
    weights: pd.Series | None,
    status: dict[str, object],
    max_weight: float,
) -> dict[str, object]:
    if weights is None:
        return {
            "model_name": model,
            "model_family": _family(model),
            "objective": _objective(model),
            **status,
            "prerequisites": _prerequisites(model),
            "prerequisites_satisfied": False,
            "expected_return_source": _expected_return_source(model),
            "covariance_source": "daily USD returns covariance",
            "uses_forecast": model
            in {
                "ML Forecast",
                "Ensemble Forecast",
                "Forecast-Enhanced Constrained Portfolio",
            },
            "uses_market_cap_prior": model == "Black-Litterman",
            "promotion_eligible": False,
            "rejection_reason": status["reason"],
            "interpretation": "Model is listed for governance but not executable under current inputs.",
        }
    aligned = weights.reindex(returns.columns).fillna(0.0)
    portfolio_returns = returns @ aligned
    metrics = evaluate_return_series(portfolio_returns)
    weight_sum = float(aligned.sum())
    negative = int((aligned < -1e-10).sum())
    max_observed = float(aligned.max()) if len(aligned) else 0.0
    constraints_pass = (
        abs(weight_sum - 1.0) <= 1e-6
        and negative == 0
        and max_observed <= max_weight + 1e-6
    )
    status_name = str(status["actual_status"])
    promotion_eligible = bool(
        constraints_pass and status_name in {"actually_run", "benchmark_only"}
    )
    return {
        "model_name": model,
        "model_family": _family(model),
        "objective": _objective(model),
        **status,
        "prerequisites": _prerequisites(model),
        "prerequisites_satisfied": status_name
        not in {"blocked_by_data", "blocked_by_implementation", "future_candidate"},
        "expected_return_source": _expected_return_source(model),
        "covariance_source": "daily USD returns covariance",
        "uses_forecast": model
        in {
            "ML Forecast",
            "Ensemble Forecast",
            "Forecast-Enhanced Constrained Portfolio",
        },
        "uses_market_cap_prior": model == "Black-Litterman",
        "weight_sum": weight_sum,
        "negative_weight_count": negative,
        "max_weight": max_observed,
        "effective_holdings": _effective_holdings(aligned),
        "concentration_warning": (
            "high_concentration" if (aligned**2).sum() > 0.20 else "none"
        ),
        "cagr": metrics["cagr"],
        "annualized_return": metrics["annualized_return"],
        "volatility": metrics["annualized_volatility"],
        "sharpe": metrics["sharpe"],
        "sortino": metrics["sortino"],
        "max_drawdown": metrics["max_drawdown"],
        "var_95": metrics["var_95"],
        "cvar_95": metrics["cvar_95"],
        "turnover": np.nan,
        "transaction_cost_assumption": "10 bps placeholder in v2 demo",
        "constraints_pass": constraints_pass,
        "promotion_eligible": promotion_eligible,
        "rejection_reason": "not promotion grade" if not promotion_eligible else "",
        "interpretation": status["reason"],
    }


def _random_portfolio_row(
    returns: pd.DataFrame,
    *,
    max_weight: float,
    random_state: int,
    n_portfolios: int = 500,
) -> dict[str, object]:
    rng = np.random.default_rng(random_state)
    rows = []
    for _ in range(n_portfolios):
        raw = pd.Series(rng.random(returns.shape[1]), index=returns.columns)
        weights = _cap_and_normalize(raw, max_weight)
        rows.append(evaluate_return_series(returns @ weights))
    frame = pd.DataFrame(rows)
    return {
        "model_name": "Random Portfolios",
        "model_family": "benchmark_distribution",
        "objective": "Random constrained portfolio benchmark.",
        "actual_status": "benchmark_only",
        "reason": "Reproducible random portfolios under the same cap.",
        "prerequisites": "returns and max-weight constraint",
        "prerequisites_satisfied": True,
        "expected_return_source": "none",
        "covariance_source": "not optimized",
        "uses_forecast": False,
        "uses_market_cap_prior": False,
        "weight_sum": 1.0,
        "negative_weight_count": 0,
        "max_weight": max_weight,
        "effective_holdings": np.nan,
        "concentration_warning": "benchmark_distribution",
        "cagr": float(frame["cagr"].median()),
        "annualized_return": float(frame["annualized_return"].median()),
        "volatility": float(frame["annualized_volatility"].median()),
        "sharpe": float(frame["sharpe"].median()),
        "sortino": float(frame["sortino"].median()),
        "max_drawdown": float(frame["max_drawdown"].median()),
        "var_95": float(frame["var_95"].median()),
        "cvar_95": float(frame["cvar_95"].median()),
        "turnover": np.nan,
        "transaction_cost_assumption": "not applied",
        "constraints_pass": True,
        "promotion_eligible": False,
        "rejection_reason": "Benchmark distribution, not a candidate.",
        "interpretation": "Used to contextualize optimized portfolios.",
    }


def _selected_tickers(
    scores: pd.DataFrame,
    returns: pd.DataFrame,
    *,
    max_assets: int,
) -> list[str]:
    if scores is None or scores.empty:
        return list(returns.columns[:max_assets])
    frame = scores.copy()
    frame["ticker"] = frame["ticker"].astype(str)
    if "selection_flag" in frame:
        selected = frame.loc[frame["selection_flag"].astype(bool), "ticker"].tolist()
    else:
        selected = []
    if not selected:
        selected = frame.sort_values("composite_quant_score", ascending=False)[
            "ticker"
        ].tolist()
    selected = [ticker for ticker in selected if ticker in returns.columns]
    return selected[:max_assets]


def _forecast_expected_returns(
    forecasts: pd.DataFrame | None,
    selected: list[str],
) -> pd.Series:
    if forecasts is None or forecasts.empty:
        return pd.Series(np.nan, index=selected)
    frame = forecasts.copy()
    frame["ticker"] = frame["ticker"].astype(str)
    horizon = frame.loc[frame["horizon"].astype(str).eq("12M")]
    if horizon.empty:
        horizon = frame
    values = (
        horizon.drop_duplicates("ticker")
        .set_index("ticker")["ensemble_expected_return"]
        .astype(float)
    )
    return values.reindex(selected)


def _market_caps(metadata: pd.DataFrame | None, selected: list[str]) -> pd.Series:
    if metadata is None or metadata.empty or "market_cap_usd" not in metadata:
        return pd.Series(np.nan, index=selected)
    caps = pd.to_numeric(
        metadata.drop_duplicates("ticker").set_index("ticker")["market_cap_usd"],
        errors="coerce",
    )
    return caps.reindex(selected)


def _gmv_weights(returns: pd.DataFrame, max_weight: float) -> pd.Series:
    cov = returns.cov().to_numpy(dtype=float)
    inv_diag = 1.0 / np.clip(np.diag(cov), 1e-12, None)
    return _cap_and_normalize(pd.Series(inv_diag, index=returns.columns), max_weight)


def _forecast_enhanced_weights(
    returns: pd.DataFrame,
    expected_returns: pd.Series,
    *,
    max_weight: float,
) -> pd.Series:
    vol = returns.std(ddof=1).replace(0.0, np.nan)
    raw = (expected_returns.clip(lower=0.0) / vol).replace([np.inf, -np.inf], np.nan)
    if raw.fillna(0.0).sum() <= 0:
        raw = expected_returns.rank(pct=True).fillna(0.5)
    return _cap_and_normalize(raw.reindex(returns.columns).fillna(0.0), max_weight)


def _policy_constrained(
    scores: pd.DataFrame,
    selected: list[str],
    *,
    max_weight: float,
) -> pd.Series:
    score = (
        scores.drop_duplicates("ticker")
        .set_index("ticker")["composite_quant_score"]
        .reindex(selected)
    )
    shifted = score - score.min() + 1e-6
    return _cap_and_normalize(shifted, max_weight)


def _cap_and_normalize(weights: pd.Series, max_weight: float) -> pd.Series:
    raw = pd.Series(weights, dtype=float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    raw = raw.clip(lower=0.0)
    if max_weight * len(raw) < 1.0 - 1e-12:
        raise ValueError("max_weight is infeasible for selected assets.")
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
    return (capped / capped.sum()).rename("weight")


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


def _status(actual_status: str, reason: str) -> dict[str, object]:
    return {"actual_status": actual_status, "reason": reason}


def _effective_holdings(weights: pd.Series) -> float:
    hhi = float((weights**2).sum())
    return float(1.0 / hhi) if hhi > 0 else 0.0


def _family(model: str) -> str:
    if model in {"Equal Weight", "Random Portfolios"}:
        return "benchmark"
    if model in {"GMV", "Inverse Volatility", "HRP", "Risk Parity", "Min CVaR"}:
        return "risk_allocation"
    if model in {"Max Sharpe", "Black-Litterman"}:
        return "expected_return_optimization"
    if "Forecast" in model or model in {"ML Forecast", "Ensemble Forecast"}:
        return "forecast_overlay"
    return "policy_constraint"


def _objective(model: str) -> str:
    return {
        "Equal Weight": "Transparent diversification baseline.",
        "Random Portfolios": "Benchmark distribution.",
        "Inverse Volatility": "Lower volatility concentration.",
        "GMV": "Minimize variance.",
        "Max Sharpe": "Maximize in-sample expected return per unit risk.",
        "Min CVaR": "Reduce empirical tail loss.",
        "HRP": "Allocate through correlation hierarchy.",
        "Risk Parity": "Equalize risk contribution.",
        "Black-Litterman": "Market-cap prior allocation diagnostic.",
        "ML Forecast": "Forecast diagnostic, not direct allocation.",
        "Ensemble Forecast": "Expected return diagnostic.",
        "Forecast-Enhanced Constrained Portfolio": "Use forecast under strict caps.",
        "Policy Constrained": "Use composite score under caps.",
    }.get(model, "Research model.")


def _prerequisites(model: str) -> str:
    if model == "Black-Litterman":
        return "positive market caps, covariance, documented views for promotion"
    if "Forecast" in model or model == "ML Forecast":
        return "generated return forecasts and chronological validation"
    if model in {"HRP", "Risk Parity", "GMV", "Max Sharpe", "Min CVaR"}:
        return "sufficient returns and feasible long-only cap constraints"
    return "returns and selected universe"


def _expected_return_source(model: str) -> str:
    if model in {"Max Sharpe"}:
        return "historical mean with shrinkage covariance"
    if model == "Black-Litterman":
        return "public-provider market-cap prior diagnostic"
    if "Forecast" in model or model == "ML Forecast":
        return "forecast engine ensemble"
    return "none or historical risk model"
