"""Independently verify representative QuantVerse v2 financial calculations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TRADING_DAYS = 252
DEFAULT_ABSOLUTE_TOLERANCE = 1e-9
DEFAULT_RELATIVE_TOLERANCE = 1e-7


def verify_reference_math(
    root: str | Path = ROOT,
    *,
    absolute_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE,
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE,
) -> pd.DataFrame:
    """Recalculate representative outputs without importing production formulas."""
    root_path = Path(root)
    processed = root_path / "data" / "processed"
    prices = _read_matrix(processed / "global_security_prices.csv")
    simple_local = _read_matrix(processed / "global_security_simple_returns_local.csv")
    log_local = _read_matrix(processed / "global_security_log_returns_local.csv")
    simple_usd = _read_matrix(processed / "global_security_simple_returns_usd.csv")
    fx_report = _read_csv(processed / "global_fx_normalization_report.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    risk_report = _read_csv(processed / "global_portfolio_risk_report.csv")
    contributions = _read_csv(processed / "global_risk_contribution_report.csv")
    decision = _read_json(processed / "global_final_model_decision.json")
    manifest = _read_json(processed / "quantverse_v2_run_manifest.json")

    final_model = str(decision.get("final_selected_model", "")).strip()
    checks: list[dict[str, object]] = []
    required_inputs = {
        "prices": prices,
        "simple_local": simple_local,
        "log_local": log_local,
        "simple_usd": simple_usd,
        "fx_report": fx_report,
        "weights": weights,
        "risk_report": risk_report,
        "risk_contributions": contributions,
    }
    missing = [name for name, frame in required_inputs.items() if frame.empty]
    _append_boolean_check(
        checks,
        "required_reference_inputs_present",
        not missing and bool(final_model),
        observed=f"missing={missing}; final_model={final_model or 'missing'}",
        formula="all required artifacts are non-empty and final model is explicit",
        invalidation="Any missing input prevents an independent comparison.",
    )
    if missing or not final_model:
        return _finalize(checks, manifest)

    final_weights = _model_weights(weights, final_model)
    common_tickers = [
        ticker
        for ticker in final_weights.index
        if ticker in prices
        and ticker in simple_local
        and ticker in log_local
        and ticker in simple_usd
    ][:5]
    _append_boolean_check(
        checks,
        "representative_price_return_sample_present",
        bool(common_tickers),
        observed=f"tickers={common_tickers}",
        formula="intersection(final holdings, price and return artifacts)",
        invalidation="No common security can be independently recalculated.",
    )
    if common_tickers:
        expected_simple = prices[common_tickers].pct_change(fill_method=None)
        expected_log = np.log(prices[common_tickers] / prices[common_tickers].shift(1))
        _append_series_comparison(
            checks,
            "simple_returns_from_prices",
            expected_simple,
            simple_local[common_tickers],
            absolute_tolerance,
            relative_tolerance,
            formula="P_t / P_(t-1) - 1",
            invalidation=(
                "Adjusted-price convention, corporate-action handling, dates, or "
                "units differ between price and return artifacts."
            ),
        )
        _append_series_comparison(
            checks,
            "log_returns_from_prices",
            expected_log,
            log_local[common_tickers],
            absolute_tolerance,
            relative_tolerance,
            formula="ln(P_t / P_(t-1))",
            invalidation=(
                "Non-positive prices, date misalignment, or mixed return definitions "
                "invalidate the comparison."
            ),
        )

    native_tickers = _native_base_tickers(fx_report, simple_local, simple_usd)
    _append_series_comparison(
        checks,
        "native_base_usd_returns_equal_local_returns",
        simple_local[native_tickers] if native_tickers else pd.DataFrame(),
        simple_usd[native_tickers] if native_tickers else pd.DataFrame(),
        absolute_tolerance,
        relative_tolerance,
        formula="R_USD = R_local when asset currency equals USD base currency",
        invalidation=(
            "A non-USD security is mislabeled native-base, or local and USD series "
            "come from different dates or price definitions."
        ),
    )

    weight_sum = float(final_weights.sum()) if not final_weights.empty else np.nan
    _append_numeric_check(
        checks,
        "final_weight_sum",
        expected=1.0,
        observed=weight_sum,
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
        formula="sum_i(w_i) = 1",
        invalidation="Incomplete, duplicated, or silently renormalized weights.",
    )
    _append_boolean_check(
        checks,
        "final_weights_long_only",
        bool(not final_weights.empty and (final_weights >= -absolute_tolerance).all()),
        observed=(float(final_weights.min()) if not final_weights.empty else "missing"),
        formula="w_i >= 0 for every holding",
        invalidation="Negative weights violate the declared long-only mandate.",
    )

    portfolio_returns = _independent_portfolio_returns(simple_usd, final_weights)
    _append_boolean_check(
        checks,
        "portfolio_return_series_nonzero",
        bool(
            not portfolio_returns.empty
            and np.isfinite(portfolio_returns.to_numpy(dtype=float)).all()
            and (portfolio_returns.abs() > 1e-12).any()
        ),
        observed=(
            f"observations={len(portfolio_returns)}; "
            f"nonzero={int((portfolio_returns.abs() > 1e-12).sum())}"
        ),
        formula=(
            "sum_i(w_i,t * R_i,t), with dates missing any selected portfolio "
            "weight excluded under the conservative complete-weight policy"
        ),
        invalidation=(
            "Missing-return handling, ticker misalignment, or zero-filled returns "
            "can collapse or bias the portfolio series."
        ),
    )

    reported_risk = _model_row(risk_report, final_model)
    risk_free_rate_annual = _number(reported_risk.get("risk_free_rate_annual"))
    if not np.isfinite(risk_free_rate_annual):
        risk_free_rate_annual = 0.0
    metrics = _independent_metrics(
        portfolio_returns,
        risk_free_rate_annual=risk_free_rate_annual,
    )
    metric_mapping = {
        "cagr": "cagr",
        "annualized_return": "annualized_return",
        "annualized_volatility": "annualized_volatility",
        "sharpe": "sharpe",
        "max_drawdown": "max_drawdown",
        "var_95": "var_95",
        "cvar_95": "cvar_95",
        "total_return": "total_return",
    }
    formulas = {
        "cagr": "(prod(1+r)) ** (252/n) - 1",
        "annualized_return": "mean(r) * 252",
        "annualized_volatility": "sample_std(r) * sqrt(252)",
        "sharpe": (
            "(annualized_return - annual risk-free rate) / " "annualized_volatility"
        ),
        "max_drawdown": "min(wealth / cumulative_max(wealth) - 1)",
        "var_95": "empirical 5th percentile of daily simple returns",
        "cvar_95": "mean(r | r <= empirical VaR_95)",
        "total_return": "prod(1+r) - 1",
    }
    for check_name, column in metric_mapping.items():
        _append_numeric_check(
            checks,
            f"final_portfolio_{check_name}",
            expected=metrics[check_name],
            observed=_number(reported_risk.get(column)),
            absolute_tolerance=absolute_tolerance,
            relative_tolerance=relative_tolerance,
            formula=formulas[check_name],
            invalidation=(
                "Different date coverage, return units, annualization, risk-free "
                "assumption, or tail convention invalidates reconciliation."
            ),
        )

    expected_contributions = _independent_risk_contributions(simple_usd, final_weights)
    reported_contributions = _model_contributions(contributions, final_model)
    _append_risk_contribution_checks(
        checks,
        expected_contributions,
        reported_contributions,
        absolute_tolerance,
        relative_tolerance,
    )
    return _finalize(checks, manifest)


def write_reference_outputs(
    checks: pd.DataFrame,
    root: str | Path = ROOT,
) -> tuple[Path, Path]:
    """Write CSV evidence and a compact JSON summary."""
    root_path = Path(root)
    processed = root_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    csv_path = processed / "quantverse_v2_reference_math_checks.csv"
    json_path = processed / "quantverse_v2_reference_math_summary.json"
    checks.to_csv(csv_path, index=False)
    failed = int((~checks["passed"].astype(bool)).sum()) if not checks.empty else 1
    summary = {
        "status": "passed" if failed == 0 else "failed",
        "check_count": int(len(checks)),
        "failed_check_count": failed,
        "run_id": (
            str(checks["run_id"].iloc[0])
            if not checks.empty and "run_id" in checks
            else "missing"
        ),
        "checks_path": str(csv_path.relative_to(root_path)).replace("\\", "/"),
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return csv_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    checks = verify_reference_math(args.root)
    csv_path, summary_path = write_reference_outputs(checks, args.root)
    failed = int((~checks["passed"].astype(bool)).sum()) if not checks.empty else 1
    print(f"reference_math_status={'passed' if failed == 0 else 'failed'}")
    print(f"reference_math_checks={csv_path}")
    print(f"reference_math_summary={summary_path}")
    return 0 if failed == 0 else 1


def _read_matrix(path: Path) -> pd.DataFrame:
    frame = _read_csv(path)
    if frame.empty:
        return frame
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[frame.index.notna()]
    return frame.apply(pd.to_numeric, errors="coerce").sort_index()


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _model_weights(weights: pd.DataFrame, model: str) -> pd.Series:
    if weights.empty or not {"model_name", "ticker", "weight"}.issubset(weights):
        return pd.Series(dtype=float)
    selected = weights.loc[weights["model_name"].astype(str).eq(model)].copy()
    if selected.empty:
        return pd.Series(dtype=float)
    values = pd.to_numeric(selected["weight"], errors="coerce")
    result = pd.Series(values.to_numpy(), index=selected["ticker"].astype(str))
    return result.groupby(level=0).sum().dropna().astype(float)


def _model_row(frame: pd.DataFrame, model: str) -> dict[str, object]:
    if frame.empty or "model_name" not in frame:
        return {}
    row = frame.loc[frame["model_name"].astype(str).eq(model)]
    return row.iloc[0].to_dict() if not row.empty else {}


def _model_contributions(frame: pd.DataFrame, model: str) -> pd.DataFrame:
    if frame.empty or "model_name" not in frame:
        return pd.DataFrame()
    selected = frame.loc[frame["model_name"].astype(str).eq(model)].copy()
    return selected.set_index("ticker") if "ticker" in selected else pd.DataFrame()


def _native_base_tickers(
    fx_report: pd.DataFrame,
    simple_local: pd.DataFrame,
    simple_usd: pd.DataFrame,
) -> list[str]:
    if fx_report.empty or "ticker" not in fx_report:
        return []
    status = fx_report.get(
        "fx_normalization_status", pd.Series("", index=fx_report.index)
    )
    currency = fx_report.get("currency", pd.Series("", index=fx_report.index))
    mask = status.astype(str).eq("native_base") & currency.astype(str).eq("USD")
    candidates = fx_report.loc[mask, "ticker"].dropna().astype(str).tolist()
    return [
        ticker
        for ticker in candidates
        if ticker in simple_local and ticker in simple_usd
    ][:10]


def _independent_portfolio_returns(
    returns: pd.DataFrame,
    weights: pd.Series,
    *,
    minimum_available_weight: float = 1.00,
) -> pd.Series:
    aligned_weights = weights.reindex(returns.columns).fillna(0.0)
    aligned_weights = aligned_weights.loc[aligned_weights.abs() > 1e-12]
    if aligned_weights.empty:
        return pd.Series(dtype=float)
    aligned_weights = aligned_weights / float(aligned_weights.sum())
    selected = returns.loc[:, aligned_weights.index]
    available = selected.notna()
    available_weight = available.mul(aligned_weights.abs(), axis=1).sum(axis=1)
    weighted_returns = selected.mul(aligned_weights, axis=1).sum(axis=1, skipna=True)
    result = weighted_returns / available_weight.replace(0.0, np.nan)
    result = result.loc[available_weight >= minimum_available_weight - 1e-12]
    return result.replace([np.inf, -np.inf], np.nan).dropna().astype(float)


def _independent_metrics(
    returns: pd.Series,
    *,
    risk_free_rate_annual: float = 0.0,
) -> dict[str, float]:
    clean = returns.dropna().astype(float)
    if clean.empty:
        return {name: np.nan for name in _metric_names()}
    wealth = (1.0 + clean).cumprod()
    total_return = float(wealth.iloc[-1] - 1.0)
    annualized_return = float(clean.mean() * TRADING_DAYS)
    volatility = float(clean.std(ddof=1) * np.sqrt(TRADING_DAYS))
    daily_hurdle = (1.0 + float(risk_free_rate_annual)) ** (1.0 / TRADING_DAYS) - 1.0
    annualized_excess = float((clean - daily_hurdle).mean() * TRADING_DAYS)
    max_drawdown = float((wealth / wealth.cummax() - 1.0).min())
    var_95 = float(clean.quantile(0.05))
    tail = clean.loc[clean <= var_95]
    cvar_95 = float(tail.mean()) if not tail.empty else var_95
    cagr = float((1.0 + total_return) ** (TRADING_DAYS / len(clean)) - 1.0)
    return {
        "cagr": cagr,
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe": (annualized_excess / volatility if volatility > 0 else 0.0),
        "max_drawdown": max_drawdown,
        "var_95": var_95,
        "cvar_95": cvar_95,
        "total_return": total_return,
    }


def _metric_names() -> list[str]:
    return [
        "cagr",
        "annualized_return",
        "annualized_volatility",
        "sharpe",
        "max_drawdown",
        "var_95",
        "cvar_95",
        "total_return",
    ]


def _independent_risk_contributions(
    returns: pd.DataFrame,
    weights: pd.Series,
) -> pd.DataFrame:
    aligned_weights = weights.reindex(returns.columns).dropna()
    aligned_weights = aligned_weights.loc[aligned_weights.abs() > 1e-12]
    if aligned_weights.empty:
        return pd.DataFrame()
    aligned_weights = aligned_weights / float(aligned_weights.sum())
    selected = returns.loc[:, aligned_weights.index].dropna(how="any")
    if selected.shape[0] < 2:
        return pd.DataFrame()
    covariance = selected.cov().to_numpy(dtype=float) * TRADING_DAYS
    vector = aligned_weights.to_numpy(dtype=float)
    variance = float(vector @ covariance @ vector)
    if variance <= 0 or not np.isfinite(variance):
        return pd.DataFrame()
    volatility = float(np.sqrt(variance))
    marginal = covariance @ vector / volatility
    component = vector * marginal
    total = float(component.sum())
    result = pd.DataFrame(
        {
            "marginal_risk_contribution": marginal,
            "component_risk_contribution": component,
            "risk_contribution_pct": component / total,
        },
        index=aligned_weights.index,
    )
    result.index.name = "ticker"
    return result


def _append_risk_contribution_checks(
    checks: list[dict[str, object]],
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> None:
    common = expected.index.intersection(observed.index)
    _append_boolean_check(
        checks,
        "risk_contribution_sample_present",
        bool(len(common)),
        observed=f"common_tickers={len(common)}",
        formula="intersection(independent contribution, reported contribution)",
        invalidation="Ticker or model-name misalignment prevents Euler reconciliation.",
    )
    if not len(common):
        return
    for column in [
        "marginal_risk_contribution",
        "component_risk_contribution",
        "risk_contribution_pct",
    ]:
        _append_series_comparison(
            checks,
            f"final_portfolio_{column}",
            expected.loc[common, [column]],
            observed.loc[common, [column]].apply(pd.to_numeric, errors="coerce"),
            absolute_tolerance,
            relative_tolerance,
            formula=("MRC = Sigma*w/sigma_p; CRC = w*MRC; percentage = CRC/sum(CRC)"),
            invalidation=(
                "Covariance annualization, weight order, or model membership differs."
            ),
        )
    _append_numeric_check(
        checks,
        "final_portfolio_risk_contribution_sum",
        expected=1.0,
        observed=float(
            pd.to_numeric(
                observed.loc[common, "risk_contribution_pct"], errors="coerce"
            ).sum()
        ),
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
        formula="sum_i(component_risk_contribution_i / portfolio_volatility) = 1",
        invalidation="Euler decomposition does not reconcile to total volatility.",
    )


def _append_series_comparison(
    checks: list[dict[str, object]],
    check: str,
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    absolute_tolerance: float,
    relative_tolerance: float,
    *,
    formula: str,
    invalidation: str,
) -> None:
    expected_aligned, observed_aligned = expected.align(observed, join="inner", axis=0)
    expected_aligned, observed_aligned = expected_aligned.align(
        observed_aligned, join="inner", axis=1
    )
    mask = expected_aligned.notna() & observed_aligned.notna()
    count = int(mask.to_numpy().sum())
    if count == 0:
        _append_boolean_check(
            checks,
            check,
            False,
            observed="no overlapping finite observations",
            formula=formula,
            invalidation=invalidation,
        )
        return
    difference = (expected_aligned - observed_aligned).where(mask).abs()
    max_difference = float(difference.max().max())
    scale = float(expected_aligned.where(mask).abs().max().max())
    tolerance = absolute_tolerance + relative_tolerance * scale
    _append_boolean_check(
        checks,
        check,
        bool(np.isfinite(max_difference) and max_difference <= tolerance),
        observed=(
            f"observations={count}; max_abs_difference={max_difference:.12g}; "
            f"tolerance={tolerance:.12g}"
        ),
        formula=formula,
        invalidation=invalidation,
        expected=f"max_abs_difference <= {tolerance:.12g}",
        absolute_difference=max_difference,
        tolerance=tolerance,
    )


def _append_numeric_check(
    checks: list[dict[str, object]],
    check: str,
    *,
    expected: float,
    observed: float,
    absolute_tolerance: float,
    relative_tolerance: float,
    formula: str,
    invalidation: str,
) -> None:
    difference = abs(expected - observed)
    tolerance = absolute_tolerance + relative_tolerance * abs(expected)
    passed = bool(
        np.isfinite(expected) and np.isfinite(observed) and difference <= tolerance
    )
    _append_boolean_check(
        checks,
        check,
        passed,
        observed=observed,
        expected=expected,
        absolute_difference=difference,
        tolerance=tolerance,
        formula=formula,
        invalidation=invalidation,
    )


def _append_boolean_check(
    checks: list[dict[str, object]],
    check: str,
    passed: bool,
    *,
    observed: object,
    formula: str,
    invalidation: str,
    expected: object = True,
    absolute_difference: float | None = None,
    tolerance: float | None = None,
) -> None:
    checks.append(
        {
            "check": check,
            "passed": bool(passed),
            "expected": expected,
            "observed": observed,
            "absolute_difference": absolute_difference,
            "tolerance": tolerance,
            "formula_or_method": formula,
            "source_basis": (
                "Independent pandas/numpy arithmetic; simple/log-return, "
                "compounding, sample-volatility, historical-tail, and Euler "
                "portfolio identities."
            ),
            "why_valid": (
                "The calculation is reconstructed from primitive input artifacts "
                "without importing the production metric or optimizer functions."
            ),
            "invalidation_condition": invalidation,
            "evidence_files": (
                "global_security_prices.csv; global_security_simple_returns_usd.csv; "
                "global_portfolio_league_weights.csv; "
                "global_portfolio_risk_report.csv; "
                "global_risk_contribution_report.csv"
            ),
        }
    )


def _finalize(
    checks: list[dict[str, object]],
    manifest: dict[str, object],
) -> pd.DataFrame:
    frame = pd.DataFrame(checks)
    frame["run_id"] = str(manifest.get("run_id", "missing"))
    frame["validation_status"] = np.where(
        frame["passed"].astype(bool), "passed", "failed"
    )
    return frame


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


if __name__ == "__main__":
    sys.exit(main())
