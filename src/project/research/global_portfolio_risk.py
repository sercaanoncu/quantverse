"""QuantVerse v2 portfolio and single-name risk diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR


def build_stock_risk_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute per-asset risk metrics from daily USD simple returns."""
    clean = _clean_returns(returns)
    rows = []
    for ticker in clean.columns:
        series = clean[ticker].dropna().astype(float)
        rows.append(
            {
                "ticker": ticker,
                "observations": int(series.shape[0]),
                "annualized_volatility": _annualized_volatility(series),
                "downside_volatility": _downside_volatility(series),
                "max_drawdown": _max_drawdown(series),
                "var_95": _var_95(series),
                "cvar_95": _cvar_95(series),
                "skewness": float(series.skew()) if len(series) > 2 else 0.0,
                "kurtosis": float(series.kurt()) if len(series) > 3 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def build_portfolio_risk_report(
    returns: pd.DataFrame,
    weights: pd.DataFrame | pd.Series,
    *,
    model_column: str = "Model",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build portfolio risk, contribution, stress and tail-risk reports."""
    clean = _clean_returns(returns)
    weight_map = _weights_by_model(weights)
    risk_rows: list[dict[str, object]] = []
    contribution_rows: list[dict[str, object]] = []
    stress_rows: list[dict[str, object]] = []
    tail_rows: list[dict[str, object]] = []
    for model, model_weights in weight_map.items():
        aligned = model_weights.reindex(clean.columns).fillna(0.0)
        if aligned.sum() <= 0:
            continue
        aligned = aligned / aligned.sum()
        portfolio_returns = clean @ aligned
        metrics = evaluate_return_series(portfolio_returns)
        risk_rows.append({"model_name": model, **metrics})
        contribution_rows.extend(_risk_contributions(clean, aligned, model))
        stress_rows.extend(_stress_tests(aligned, model))
        tail_rows.append(
            {
                "model_name": model,
                "var_95": metrics["var_95"],
                "cvar_95": metrics["cvar_95"],
                "worst_daily_return": float(portfolio_returns.min()),
                "best_daily_return": float(portfolio_returns.max()),
            }
        )
    return (
        pd.DataFrame(risk_rows),
        pd.DataFrame(contribution_rows),
        pd.DataFrame(stress_rows),
        pd.DataFrame(tail_rows),
    )


def evaluate_return_series(series: pd.Series) -> dict[str, float]:
    """Evaluate a daily return series with portfolio risk metrics."""
    clean = pd.Series(series).dropna().astype(float)
    if clean.empty:
        return _empty_metrics()
    total_return = float((1.0 + clean).prod() - 1.0)
    years = max(len(clean) / TRADING_DAYS_PER_YEAR, 1e-12)
    cagr = float((1.0 + total_return) ** (1.0 / years) - 1.0)
    annual_return = float(clean.mean() * TRADING_DAYS_PER_YEAR)
    volatility = _annualized_volatility(clean)
    downside = _downside_volatility(clean)
    max_drawdown = _max_drawdown(clean)
    cvar = _cvar_95(clean)
    return {
        "cagr": cagr,
        "annualized_return": annual_return,
        "annualized_volatility": volatility,
        "sharpe": annual_return / volatility if volatility > 0 else 0.0,
        "sortino": annual_return / downside if downside > 0 else 0.0,
        "max_drawdown": max_drawdown,
        "var_95": _var_95(clean),
        "cvar_95": cvar,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0 else 0.0,
        "ulcer_index": _ulcer_index(clean),
        "total_return": total_return,
    }


def write_risk_outputs(
    stock_metrics: pd.DataFrame,
    portfolio_report: pd.DataFrame,
    risk_contributions: pd.DataFrame,
    stress_tests: pd.DataFrame,
    tail_risk: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    """Write v2 risk outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    stock_metrics.to_csv(path / "global_stock_risk_metrics.csv", index=False)
    portfolio_report.to_csv(path / "global_portfolio_risk_report.csv", index=False)
    risk_contributions.to_csv(path / "global_risk_contribution_report.csv", index=False)
    stress_tests.to_csv(path / "global_stress_test_results.csv", index=False)
    tail_risk.to_csv(path / "global_tail_risk_report.csv", index=False)


def _weights_by_model(weights: pd.DataFrame | pd.Series) -> dict[str, pd.Series]:
    if isinstance(weights, pd.Series):
        return {"Portfolio": pd.Series(weights, dtype=float)}
    frame = weights.copy()
    if {"Ticker", "Weight"}.issubset(frame.columns):
        model_col = "Model" if "Model" in frame.columns else "model_name"
        if model_col not in frame:
            frame[model_col] = "Portfolio"
        return {
            str(model): group.set_index("Ticker")["Weight"].astype(float)
            for model, group in frame.groupby(model_col)
        }
    if {"ticker", "weight"}.issubset(frame.columns):
        model_col = "model_name" if "model_name" in frame.columns else "Model"
        if model_col not in frame:
            frame[model_col] = "Portfolio"
        return {
            str(model): group.set_index("ticker")["weight"].astype(float)
            for model, group in frame.groupby(model_col)
        }
    raise ValueError("Weights must include ticker/weight columns or be a Series.")


def _risk_contributions(
    returns: pd.DataFrame,
    weights: pd.Series,
    model: str,
) -> list[dict[str, object]]:
    cov = returns.cov().reindex(index=weights.index, columns=weights.index).fillna(0.0)
    sigma = cov.to_numpy(dtype=float) * TRADING_DAYS_PER_YEAR
    w = weights.to_numpy(dtype=float)
    variance = float(w @ sigma @ w)
    if variance <= 0:
        marginal = np.zeros_like(w)
        component = np.zeros_like(w)
    else:
        vol = np.sqrt(variance)
        marginal = sigma @ w / vol
        component = w * marginal
    total = float(component.sum())
    rows = []
    for ticker, weight, mrc, crc in zip(weights.index, w, marginal, component):
        rows.append(
            {
                "model_name": model,
                "ticker": ticker,
                "weight": float(weight),
                "marginal_risk_contribution": float(mrc),
                "component_risk_contribution": float(crc),
                "risk_contribution_pct": float(crc / total) if total else 0.0,
            }
        )
    return rows


def _stress_tests(weights: pd.Series, model: str) -> list[dict[str, object]]:
    shocks = {
        "equity_selloff": -0.15,
        "fx_shock": -0.05,
        "high_volatility_regime": -0.08,
        "crypto_crash": -0.25,
        "turkey_specific_shock": -0.20,
        "rate_shock": -0.06,
    }
    exposure = float(weights.abs().sum())
    return [
        {
            "model_name": model,
            "scenario": scenario,
            "assumed_shock": shock,
            "portfolio_loss_estimate": float(exposure * shock),
            "interpretation": "Scenario diagnostic, not a forecast.",
        }
        for scenario, shock in shocks.items()
    ]


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


def _annualized_volatility(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.shape[0] < 2:
        return 0.0
    return float(clean.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def _downside_volatility(series: pd.Series) -> float:
    downside = series.dropna()
    downside = downside[downside < 0]
    if downside.shape[0] < 2:
        return 0.0
    return float(downside.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def _max_drawdown(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.empty:
        return 0.0
    wealth = (1.0 + clean).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(drawdown.min())


def _var_95(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.empty:
        return 0.0
    return float(clean.quantile(0.05))


def _cvar_95(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.empty:
        return 0.0
    var = _var_95(clean)
    tail = clean[clean <= var]
    return float(tail.mean()) if not tail.empty else var


def _ulcer_index(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.empty:
        return 0.0
    wealth = (1.0 + clean).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(np.sqrt((drawdown.clip(upper=0.0) ** 2).mean()))


def _empty_metrics() -> dict[str, float]:
    return {
        "cagr": 0.0,
        "annualized_return": 0.0,
        "annualized_volatility": 0.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "max_drawdown": 0.0,
        "var_95": 0.0,
        "cvar_95": 0.0,
        "calmar": 0.0,
        "ulcer_index": 0.0,
        "total_return": 0.0,
    }
