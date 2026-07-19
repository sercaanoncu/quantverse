"""QuantVerse v2 portfolio and single-name risk diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR
from project.data_pipeline.security_identity import resolve_security_master_rows
from project.research.global_numerical_integrity import (
    portfolio_return_series,
    return_series_diagnostics,
)

METRIC_REVIEW_THRESHOLDS = {
    # Operational red-flag thresholds, not statistical significance cutoffs.
    "short_sample_observations": 2 * TRADING_DAYS_PER_YEAR,
    "short_sample_annualized_return": 0.50,
    "short_sample_cagr": 0.75,
    "absolute_annualized_return": 1.00,
    "absolute_cagr": 2.00,
    "absolute_sharpe": 3.00,
    "absolute_sortino": 5.00,
    "annualized_volatility": 1.00,
}


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
    risk_free_rate_annual: float = 0.0,
    risk_free_policy: str = "zero_rate_labeled_research_assumption",
    metadata: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build portfolio risk, contribution, stress and tail-risk reports."""
    clean = _clean_returns(returns)
    weight_map = _weights_by_model(weights)
    risk_rows: list[dict[str, object]] = []
    contribution_rows: list[dict[str, object]] = []
    stress_rows: list[dict[str, object]] = []
    tail_rows: list[dict[str, object]] = []
    for model, model_weights in weight_map.items():
        portfolio_returns = portfolio_return_series(clean, model_weights)
        aligned = model_weights.reindex(clean.columns).fillna(0.0)
        aligned = aligned.loc[aligned.abs() > 1e-12]
        if aligned.sum() <= 0:
            continue
        aligned = aligned / aligned.sum()
        model_returns = clean.loc[:, aligned.index]
        metrics = evaluate_return_series(
            portfolio_returns,
            risk_free_rate_annual=risk_free_rate_annual,
        )
        diagnostics = return_series_diagnostics(portfolio_returns)
        risk_rows.append(
            {
                "model_name": model,
                **metrics,
                "portfolio_return_observations": diagnostics["observations"],
                "portfolio_return_nonzero_count": diagnostics["nonzero_count"],
                "risk_free_rate_annual": float(risk_free_rate_annual),
                "risk_free_policy": str(risk_free_policy),
                "missing_return_policy": "complete_selected_weight_required",
                "minimum_available_weight": 1.0,
                "annualized_return_label": "arithmetic annualized mean daily simple return",
                "cagr_label": "compound annual growth rate from realized daily simple returns",
                "var_cvar_label": "daily historical simple-return tail metrics; negative values are losses",
                "extreme_metric_warning": _extreme_metric_warning(metrics),
            }
        )
        contribution_rows.extend(_risk_contributions(model_returns, aligned, model))
        stress_rows.extend(_stress_tests(aligned, model, metadata))
        tail_rows.append(
            {
                "model_name": model,
                "var_95": metrics["var_95"],
                "cvar_95": metrics["cvar_95"],
                "worst_daily_return": (
                    float(portfolio_returns.min())
                    if not portfolio_returns.empty
                    else 0.0
                ),
                "best_daily_return": (
                    float(portfolio_returns.max())
                    if not portfolio_returns.empty
                    else 0.0
                ),
            }
        )
    return (
        pd.DataFrame(risk_rows),
        pd.DataFrame(contribution_rows),
        pd.DataFrame(stress_rows),
        pd.DataFrame(tail_rows),
    )


def evaluate_return_series(
    series: pd.Series,
    *,
    risk_free_rate_annual: float = 0.0,
) -> dict[str, object]:
    """Evaluate a daily return series with portfolio risk metrics."""
    clean = pd.Series(series).dropna().astype(float)
    if clean.empty:
        return _empty_metrics()
    if (clean < -1.0 - 1e-12).any():
        raise ValueError("Simple returns below -100% are mathematically invalid.")
    total_return = float((1.0 + clean).prod() - 1.0)
    years = max(len(clean) / TRADING_DAYS_PER_YEAR, 1e-12)
    cagr = float((1.0 + total_return) ** (1.0 / years) - 1.0)
    annual_return = float(clean.mean() * TRADING_DAYS_PER_YEAR)
    volatility = _annualized_volatility(clean)
    daily_hurdle = (1.0 + float(risk_free_rate_annual)) ** (
        1.0 / TRADING_DAYS_PER_YEAR
    ) - 1.0
    excess_daily = clean - daily_hurdle
    annualized_excess_return = float(excess_daily.mean() * TRADING_DAYS_PER_YEAR)
    downside = _downside_volatility(excess_daily)
    max_drawdown = _max_drawdown(clean)
    cvar = _cvar_95(clean)
    return {
        "observations": int(clean.shape[0]),
        "nonzero_observations": int((clean.abs() > 1e-12).sum()),
        "metric_status": (
            "valid" if int((clean.abs() > 1e-12).sum()) > 0 else "zero_return_series"
        ),
        "cagr": cagr,
        "annualized_return": annual_return,
        "annualized_volatility": volatility,
        "sharpe": (annualized_excess_return / volatility if volatility > 0 else 0.0),
        "sortino": (annualized_excess_return / downside if downside > 0 else 0.0),
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
    build_risk_metric_definitions().to_csv(
        path / "global_risk_metric_definitions.csv", index=False
    )
    build_risk_metric_sanity_checks(portfolio_report, tail_risk).to_csv(
        path / "global_risk_metric_sanity_checks.csv", index=False
    )


def build_risk_metric_definitions() -> pd.DataFrame:
    """Return a small data dictionary for generated v2 risk metrics."""
    return pd.DataFrame(
        [
            {
                "metric": "annualized_return",
                "formula": "mean(daily_simple_return) * 252",
                "unit": "decimal annualized arithmetic return",
                "interpretation": "Realized public-data estimate; not a forecast guarantee.",
            },
            {
                "metric": "cagr",
                "formula": "(1 + total_return) ** (252 / observations) - 1",
                "unit": "decimal compound annual growth rate",
                "interpretation": "Compounded realized growth rate over available sample.",
            },
            {
                "metric": "annualized_volatility",
                "formula": "std(daily_simple_return, ddof=1) * sqrt(252)",
                "unit": "decimal annualized volatility",
                "interpretation": "Dispersion estimate from historical daily simple returns.",
            },
            {
                "metric": "sharpe",
                "formula": (
                    "mean(daily_simple_return - daily_compounded_risk_free_hurdle) "
                    "* 252 / annualized_volatility"
                ),
                "unit": "return per unit volatility",
                "interpretation": (
                    "Risk-adjusted return metric. QuantVerse v2 uses a zero "
                    "risk-free assumption unless an explicit risk-free series is "
                    "configured."
                ),
            },
            {
                "metric": "sortino",
                "formula": (
                    "mean(daily_excess_return) * 252 / "
                    "(sqrt(mean(min(daily_excess_return, 0)^2)) * sqrt(252))"
                ),
                "unit": "excess return per unit target semideviation",
                "interpretation": (
                    "Downside deviation is a lower partial second moment over "
                    "all observations, not the standard deviation of only "
                    "negative observations."
                ),
            },
            {
                "metric": "var_95",
                "formula": "5th percentile of daily simple returns",
                "unit": "decimal daily return",
                "interpretation": "Negative values indicate loss threshold.",
            },
            {
                "metric": "cvar_95",
                "formula": "mean of returns less than or equal to VaR_95",
                "unit": "decimal daily return",
                "interpretation": "More negative than VaR when the tail is adverse.",
            },
            {
                "metric": "max_drawdown",
                "formula": "wealth / running_max(wealth) - 1",
                "unit": "decimal drawdown",
                "interpretation": "Non-positive historical peak-to-trough loss.",
            },
        ]
    )


def build_risk_metric_sanity_checks(
    portfolio_report: pd.DataFrame,
    tail_risk: pd.DataFrame,
) -> pd.DataFrame:
    """Build deterministic sanity checks for final risk outputs."""
    checks = []
    if portfolio_report.empty:
        return pd.DataFrame(
            [
                {
                    "check": "portfolio_report_non_empty",
                    "passed": False,
                    "details": "No portfolio risk rows were generated.",
                }
            ]
        )
    numeric = portfolio_report.select_dtypes(include=[np.number])
    checks.append(
        {
            "check": "finite_numeric_metrics",
            "passed": bool(np.isfinite(numeric.to_numpy(dtype=float)).all()),
            "details": "All numeric portfolio risk metrics must be finite.",
        }
    )
    checks.append(
        {
            "check": "cvar_not_greater_than_var",
            "passed": bool(
                (portfolio_report["cvar_95"] <= portfolio_report["var_95"]).all()
            ),
            "details": "Historical CVaR should be at least as adverse as VaR.",
        }
    )
    checks.append(
        {
            "check": "drawdown_non_positive",
            "passed": bool((portfolio_report["max_drawdown"] <= 0.0).all()),
            "details": "Drawdown is expressed as a non-positive loss.",
        }
    )
    checks.append(
        {
            "check": "volatility_non_negative",
            "passed": bool((portfolio_report["annualized_volatility"] >= 0.0).all()),
            "details": "Volatility cannot be negative.",
        }
    )
    metric_columns = [
        "cagr",
        "annualized_return",
        "annualized_volatility",
        "sharpe",
        "max_drawdown",
        "var_95",
        "cvar_95",
    ]
    present = [column for column in metric_columns if column in portfolio_report]
    numeric = portfolio_report[present].apply(pd.to_numeric, errors="coerce")
    checks.append(
        {
            "check": "portfolio_metrics_not_all_zero",
            "passed": bool((numeric.abs().sum(axis=1) > 1e-12).any()),
            "details": "Executable portfolio metrics must not collapse to all zero.",
        }
    )
    if not tail_risk.empty:
        checks.append(
            {
                "check": "tail_report_consistent",
                "passed": bool((tail_risk["cvar_95"] <= tail_risk["var_95"]).all()),
                "details": "Tail-risk report uses the same VaR/CVaR sign convention.",
            }
        )
    return pd.DataFrame(checks)


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
    common = returns.reindex(columns=weights.index).dropna(how="any")
    if common.shape[0] < 2:
        return [
            {
                "model_name": model,
                "ticker": ticker,
                "weight": float(weight),
                "marginal_risk_contribution": np.nan,
                "component_risk_contribution": np.nan,
                "risk_contribution_pct": np.nan,
                "absolute_risk_contribution_pct": np.nan,
                "risk_contribution_note": (
                    "insufficient complete common observations; missing "
                    "covariances were not imputed as zero"
                ),
            }
            for ticker, weight in weights.items()
        ]
    cov = common.cov().reindex(index=weights.index, columns=weights.index)
    if not np.isfinite(cov.to_numpy(dtype=float)).all():
        raise ValueError("Risk-contribution covariance contains non-finite values.")
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
    abs_total = float(np.abs(component).sum())
    contribution_note = (
        "standard positive component risk contribution"
        if total > 0 and np.all(component >= -1e-12)
        else "contains negative covariance hedge effects; absolute contribution also reported"
    )
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
                "absolute_risk_contribution_pct": (
                    float(abs(crc) / abs_total) if abs_total else 0.0
                ),
                "risk_contribution_note": contribution_note,
                "risk_contribution_covariance_estimator": (
                    "sample covariance on complete common daily USD simple returns"
                ),
            }
        )
    return rows


def _stress_tests(
    weights: pd.Series,
    model: str,
    metadata: pd.DataFrame | None,
) -> list[dict[str, object]]:
    exposures, metadata_status = _stress_target_exposures(weights, metadata)
    scenarios = {
        "equity_selloff": (-0.15, "global equity sleeve exposure"),
        "fx_shock": (-0.05, "non-USD currency exposure"),
        "high_volatility_regime": (-0.08, "total invested exposure"),
        "crypto_crash": (-0.25, "crypto sleeve exposure"),
        "turkey_specific_shock": (-0.20, "Turkey equity/country exposure"),
        "rate_shock": (-0.06, "defensive bond and cash proxy exposure"),
    }
    return [
        {
            "model_name": model,
            "scenario": scenario,
            "assumed_shock": shock,
            "shock_scope": scope,
            "target_exposure": exposures.get(scenario, np.nan),
            "portfolio_loss_estimate": (
                float(exposures[scenario] * shock) if scenario in exposures else np.nan
            ),
            "applicability_status": (
                "metadata_missing"
                if scenario not in exposures
                else (
                    "zero_target_exposure"
                    if abs(exposures[scenario]) <= 1e-12
                    else "applied_to_target_exposure"
                )
            ),
            "metadata_status": metadata_status,
            "interpretation": (
                "Stylized sleeve/currency exposure shock; not a forecast or "
                "factor-beta model."
            ),
        }
        for scenario, (shock, scope) in scenarios.items()
    ]


def _stress_target_exposures(
    weights: pd.Series,
    metadata: pd.DataFrame | None,
) -> tuple[dict[str, float], str]:
    total = float(weights.abs().sum())
    base = {"high_volatility_regime": total}
    if metadata is None or metadata.empty or "ticker" not in metadata:
        return base, "metadata_missing_for_targeted_scenarios"
    master = resolve_security_master_rows(metadata).set_index("ticker")
    aligned = master.reindex(weights.index)
    sleeve = aligned.get("sleeve", pd.Series("", index=aligned.index)).astype(str)
    country = aligned.get("country", pd.Series("", index=aligned.index)).astype(str)
    currency = aligned.get("currency", pd.Series("", index=aligned.index)).astype(str)
    absolute_weights = weights.abs()
    equity = sleeve.str.startswith("global_equity", na=False)
    crypto = sleeve.str.contains("crypto", case=False, na=False)
    turkey = country.str.contains("turkey|türkiye", case=False, na=False) | (
        sleeve.str.contains("turkey", case=False, na=False)
    )
    defensive = sleeve.str.contains("defensive|bond|cash", case=False, na=False)
    non_usd = currency.str.upper().ne("USD") & currency.ne("")
    base.update(
        {
            "equity_selloff": float(absolute_weights.loc[equity].sum()),
            "fx_shock": float(absolute_weights.loc[non_usd].sum()),
            "crypto_crash": float(absolute_weights.loc[crypto].sum()),
            "turkey_specific_shock": float(absolute_weights.loc[turkey].sum()),
            "rate_shock": float(absolute_weights.loc[defensive].sum()),
        }
    )
    return base, "security_master_metadata_applied"


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
    clean = series.dropna().astype(float)
    if clean.empty:
        return 0.0
    shortfall = np.minimum(clean.to_numpy(dtype=float), 0.0)
    return float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(TRADING_DAYS_PER_YEAR))


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


def _extreme_metric_warning(metrics: dict[str, object]) -> str:
    """Return operational review flags for unusually scaled point estimates."""
    warnings = []
    observations = int(metrics.get("observations", 0) or 0)
    annualized_return = abs(float(metrics.get("annualized_return", 0.0)))
    cagr = abs(float(metrics.get("cagr", 0.0)))
    sharpe = abs(float(metrics.get("sharpe", 0.0)))
    sortino = abs(float(metrics.get("sortino", 0.0)))
    volatility = abs(float(metrics.get("annualized_volatility", 0.0)))
    if (
        observations < METRIC_REVIEW_THRESHOLDS["short_sample_observations"]
        and annualized_return
        > METRIC_REVIEW_THRESHOLDS["short_sample_annualized_return"]
    ):
        warnings.append("high_annualized_return_short_sample_review_required")
    if (
        observations < METRIC_REVIEW_THRESHOLDS["short_sample_observations"]
        and cagr > METRIC_REVIEW_THRESHOLDS["short_sample_cagr"]
    ):
        warnings.append("high_cagr_short_sample_review_required")
    if annualized_return > METRIC_REVIEW_THRESHOLDS["absolute_annualized_return"]:
        warnings.append("extreme_annualized_return_review_required")
    if cagr > METRIC_REVIEW_THRESHOLDS["absolute_cagr"]:
        warnings.append("extreme_cagr_review_required")
    if sharpe > METRIC_REVIEW_THRESHOLDS["absolute_sharpe"]:
        warnings.append("extreme_sharpe_review_required")
    if sortino > METRIC_REVIEW_THRESHOLDS["absolute_sortino"]:
        warnings.append("extreme_sortino_review_required")
    if volatility > METRIC_REVIEW_THRESHOLDS["annualized_volatility"]:
        warnings.append("extreme_volatility_review_required")
    return "; ".join(warnings) if warnings else "none"


def _empty_metrics() -> dict[str, object]:
    return {
        "observations": 0,
        "nonzero_observations": 0,
        "metric_status": "insufficient_data",
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
