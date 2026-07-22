"""Independently verify representative QuantVerse v2 financial calculations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)

TRADING_DAYS = 252
DEFAULT_ABSOLUTE_TOLERANCE = 1e-9
DEFAULT_RELATIVE_TOLERANCE = 1e-7
RUN_IDENTITY_FIELDS = (
    "run_id",
    "execution_id",
    "data_as_of_date",
    "generated_at",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
)


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
    diagnostic_log_returns = _read_matrix(processed / "global_security_log_returns.csv")
    simple_usd = _read_matrix(processed / "global_security_simple_returns_usd.csv")
    fx_report = _read_csv(processed / "global_fx_normalization_report.csv")
    fx_prices = _read_matrix(processed / "global_fx_prices.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    risk_report = _read_csv(processed / "global_portfolio_risk_report.csv")
    contributions = _read_csv(processed / "global_risk_contribution_report.csv")
    walk_returns = _read_csv(processed / "global_walk_forward_returns.csv")
    walk_weights = _read_csv(processed / "global_walk_forward_weights.csv")
    walk_turnover = _read_csv(processed / "global_walk_forward_turnover.csv")
    walk_validation = _read_csv(processed / "global_walk_forward_validation.csv")
    walk_windows = _read_csv(processed / "global_walk_forward_window_summary.csv")
    leakage_audit = _read_csv(processed / "global_walk_forward_leakage_audit.csv")
    random_returns = _read_csv(processed / "global_walk_forward_random_returns.csv")
    random_weights = _read_csv(processed / "global_walk_forward_random_weights.csv")
    random_distribution = _read_csv(
        processed / "global_walk_forward_random_distribution.csv"
    )
    random_provenance = _read_json(
        processed / "global_walk_forward_random_benchmark_provenance.json"
    )
    uncertainty = _read_csv(processed / "global_walk_forward_uncertainty.csv")
    covariance_comparison = _read_csv(
        processed / "global_covariance_estimator_comparison.csv"
    )
    league = _read_csv(processed / "global_portfolio_league.csv")
    selection = _read_csv(processed / "global_model_selection_report.csv")
    random_percentiles = _read_csv(
        processed / "global_random_portfolio_percentile_report.csv"
    )
    robustness = _read_json(processed / "global_parameter_sensitivity_summary.json")
    decision = _read_json(processed / "global_final_model_decision.json")
    manifest = _read_json(processed / "quantverse_v2_run_manifest.json")

    final_model = str(decision.get("final_selected_model", "")).strip()
    checks: list[dict[str, object]] = []
    required_inputs = {
        "prices": prices,
        "simple_local": simple_local,
        "log_local": log_local,
        "diagnostic_log_returns": diagnostic_log_returns,
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
    _append_fx_conversion_checks(
        checks,
        simple_local,
        simple_usd,
        fx_prices,
        fx_report,
        absolute_tolerance,
        relative_tolerance,
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
        "sortino": "sortino",
        "max_drawdown": "max_drawdown",
        "var_95": "var_95",
        "cvar_95": "cvar_95",
        "calmar": "calmar",
        "total_return": "total_return",
    }
    formulas = {
        "cagr": "(prod(1+r)) ** (252/n) - 1",
        "annualized_return": "mean(r) * 252",
        "annualized_volatility": "sample_std(r) * sqrt(252)",
        "sharpe": (
            "mean(daily_simple_return - compounded_daily_risk_free_hurdle) "
            "* 252 / annualized_volatility"
        ),
        "sortino": (
            "mean(daily_excess_return) * 252 / "
            "(sqrt(mean(min(daily_excess_return, 0)^2)) * sqrt(252))"
        ),
        "max_drawdown": (
            "min(wealth / max(1, cumulative_max(wealth)) - 1); "
            "initial capital baseline = 1"
        ),
        "var_95": "empirical 5th percentile of daily simple returns",
        "cvar_95": "mean(r | r <= empirical VaR_95)",
        "calmar": "CAGR / abs(max_drawdown)",
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
    _append_walk_forward_reference_checks(
        checks,
        simple_usd,
        walk_returns,
        walk_weights,
        walk_turnover,
        walk_validation,
        absolute_tolerance,
        relative_tolerance,
    )
    _append_random_benchmark_reference_checks(
        checks,
        walk_returns,
        random_returns,
        random_weights,
        random_distribution,
        random_provenance,
        manifest,
        simple_usd,
        walk_windows,
        absolute_tolerance,
        relative_tolerance,
    )
    _append_bootstrap_input_checks(checks, walk_returns, uncertainty)
    _append_covariance_checks(
        checks,
        diagnostic_log_returns,
        covariance_comparison,
        absolute_tolerance,
        relative_tolerance,
    )
    _append_optimizer_constraint_checks(checks, weights, league)
    _append_model_selection_reconciliation_checks(
        checks,
        selection,
        random_percentiles,
        random_provenance,
        robustness,
        leakage_audit,
        manifest,
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
        **{
            field: (
                str(checks[field].iloc[0])
                if not checks.empty and field in checks
                else "missing"
            )
            for field in RUN_IDENTITY_FIELDS
        },
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
    root_path = Path(args.root).resolve()
    processed = root_path / "data" / "processed"
    register_artifacts(
        processed,
        [csv_path, summary_path],
        read_run_manifest(processed),
        root=root_path,
    )
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
    # Provenance hashes must recover the exact floats emitted by DataFrame.to_csv.
    return (
        pd.read_csv(path, float_precision="round_trip")
        if path.exists()
        else pd.DataFrame()
    )


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


def _append_fx_conversion_checks(
    checks: list[dict[str, object]],
    simple_local: pd.DataFrame,
    simple_usd: pd.DataFrame,
    fx_prices: pd.DataFrame,
    fx_report: pd.DataFrame,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> None:
    required = {
        "ticker",
        "fx_ticker",
        "inversion_required",
        "fx_normalization_status",
    }
    if fx_report.empty or not required.issubset(fx_report):
        _append_boolean_check(
            checks,
            "non_native_fx_conversion_replay",
            False,
            observed="FX normalization report is missing required provenance columns.",
            formula="R_base = (1 + R_local) * (1 + R_FX_to_base) - 1",
            invalidation="FX direction and compounding cannot be independently replayed.",
        )
        return
    normalized = fx_report.loc[
        fx_report["fx_normalization_status"].astype(str).eq("fx_normalized")
    ].copy()
    if normalized.empty:
        _append_boolean_check(
            checks,
            "non_native_fx_conversion_replay",
            True,
            observed="not_applicable_no_fx_normalized_assets",
            formula="R_base = (1 + R_local) * (1 + R_FX_to_base) - 1",
            invalidation=(
                "This pass is scope-limited to a native-base universe; it does not "
                "claim empirical non-native FX coverage."
            ),
        )
        return
    expected: dict[str, pd.Series] = {}
    observed: dict[str, pd.Series] = {}
    missing: list[str] = []
    for _, row in normalized.head(5).iterrows():
        ticker = str(row["ticker"])
        fx_ticker = str(row["fx_ticker"])
        if (
            ticker not in simple_local
            or ticker not in simple_usd
            or fx_ticker not in fx_prices
        ):
            missing.append(f"{ticker}:{fx_ticker}")
            continue
        prices = pd.to_numeric(fx_prices[fx_ticker], errors="coerce").sort_index()
        if _truthy(row["inversion_required"]):
            prices = 1.0 / prices.where(prices > 0)
        limit = int(_number(row.get("max_forward_fill_days", 0)))
        aligned = prices.reindex(pd.DatetimeIndex(simple_local.index))
        if limit > 0:
            aligned = aligned.ffill(limit=limit)
        fx_return = aligned.pct_change(fill_method=None)
        local = pd.to_numeric(simple_local[ticker], errors="coerce")
        expected[ticker] = ((1.0 + local) * (1.0 + fx_return)) - 1.0
        observed[ticker] = pd.to_numeric(simple_usd[ticker], errors="coerce")
    if missing or not expected:
        _append_boolean_check(
            checks,
            "non_native_fx_conversion_replay",
            False,
            observed=f"missing_raw_fx_evidence={missing}",
            formula="R_base = (1 + R_local) * (1 + R_FX_to_base) - 1",
            invalidation=(
                "A normalized non-base return without raw FX prices cannot prove "
                "quote direction or compounding."
            ),
        )
        return
    _append_series_comparison(
        checks,
        "non_native_fx_conversion_replay",
        pd.DataFrame(expected),
        pd.DataFrame(observed),
        absolute_tolerance,
        relative_tolerance,
        formula=(
            "invert quote when declared, R_FX = FX_t/FX_(t-1)-1, "
            "R_base = (1 + R_local)*(1 + R_FX)-1"
        ),
        invalidation=(
            "Wrong quote direction, inversion, calendar fill, date alignment or "
            "return compounding invalidates base-currency portfolio evidence."
        ),
    )


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


def _independent_drifted_weights(
    weights: pd.Series,
    asset_returns: pd.DataFrame,
) -> pd.Series:
    """Recompute terminal buy-and-hold weights without production helpers."""
    current = pd.Series(weights, dtype=float)
    current = current.loc[current.abs() > 1e-12]
    if current.empty:
        raise ValueError("empty portfolio")
    missing = [
        ticker for ticker in current.index if ticker not in asset_returns.columns
    ]
    if missing:
        raise ValueError("selected ticker missing from returns")
    selected = asset_returns.reindex(columns=current.index).apply(
        pd.to_numeric,
        errors="coerce",
    )
    values = selected.to_numpy(dtype=float)
    if selected.empty or not np.isfinite(values).all() or bool((values < -1.0).any()):
        raise ValueError("invalid selected return path")
    terminal = current * (1.0 + selected).prod(axis=0)
    total = float(terminal.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("invalid terminal portfolio value")
    result = terminal / total
    if not np.isfinite(result.to_numpy(dtype=float)).all():
        raise ValueError("invalid terminal weights")
    return result.astype(float)


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
    excess = clean - daily_hurdle
    annualized_excess = float(excess.mean() * TRADING_DAYS)
    downside = float(
        np.sqrt(np.mean(np.minimum(excess.to_numpy(dtype=float), 0.0) ** 2))
        * np.sqrt(TRADING_DAYS)
    )
    running_peak = wealth.cummax().clip(lower=1.0)
    max_drawdown = float((wealth / running_peak - 1.0).min())
    var_95 = float(clean.quantile(0.05))
    tail = clean.loc[clean <= var_95]
    cvar_95 = float(tail.mean()) if not tail.empty else var_95
    cagr = float((1.0 + total_return) ** (TRADING_DAYS / len(clean)) - 1.0)
    return {
        "cagr": cagr,
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe": (annualized_excess / volatility if volatility > 0 else 0.0),
        "sortino": (annualized_excess / downside if downside > 0 else 0.0),
        "max_drawdown": max_drawdown,
        "var_95": var_95,
        "cvar_95": cvar_95,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0 else 0.0,
        "total_return": total_return,
    }


def _metric_names() -> list[str]:
    return [
        "cagr",
        "annualized_return",
        "annualized_volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "var_95",
        "cvar_95",
        "calmar",
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


def _append_walk_forward_reference_checks(
    checks: list[dict[str, object]],
    returns: pd.DataFrame,
    walk_returns: pd.DataFrame,
    walk_weights: pd.DataFrame,
    walk_turnover: pd.DataFrame,
    walk_validation: pd.DataFrame,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> None:
    required = {
        "walk_returns": (
            walk_returns,
            {"Date", "fold", "model_name", "return"},
        ),
        "walk_weights": (
            walk_weights,
            {"fold", "model_name", "ticker", "weight"},
        ),
        "walk_turnover": (
            walk_turnover,
            {
                "fold",
                "model_name",
                "turnover",
                "transaction_cost_bps",
                "transaction_cost_decimal",
            },
        ),
        "walk_validation": (
            walk_validation,
            {
                "fold",
                "model_name",
                "test_start",
                "test_end",
                "test_observations",
            },
        ),
    }
    missing = [
        name
        for name, (frame, columns) in required.items()
        if frame.empty or not columns.issubset(frame.columns)
    ]
    _append_boolean_check(
        checks,
        "walk_forward_reference_inputs_present",
        not missing,
        observed=f"missing={missing}",
        formula="required raw OOS returns, weights, turnover and fold windows exist",
        invalidation="Missing raw walk-forward evidence prevents independent replay.",
    )
    if missing:
        return

    actual = walk_returns.copy()
    actual["Date"] = pd.to_datetime(actual["Date"], errors="coerce")
    actual["return"] = pd.to_numeric(actual["return"], errors="coerce")
    actual["fold"] = pd.to_numeric(actual["fold"], errors="coerce")
    actual["model_name"] = actual["model_name"].astype(str).str.strip()
    duplicate_count = int(actual.duplicated(["model_name", "Date"], keep=False).sum())
    _append_boolean_check(
        checks,
        "stitched_oos_model_dates_unique",
        duplicate_count == 0,
        observed=f"duplicate_model_dates={duplicate_count}",
        formula="one net OOS return per model and date",
        invalidation="Overlapping test windows double-count path-dependent evidence.",
    )
    expected_dates_by_fold, schedule_issues = _expected_oos_dates_by_fold(
        returns.index,
        walk_validation,
    )
    completeness_issues = list(schedule_issues)
    validation_groups = set(
        walk_validation[["fold", "model_name"]]
        .assign(
            fold=lambda frame: pd.to_numeric(frame["fold"], errors="coerce"),
            model_name=lambda frame: frame["model_name"].astype(str).str.strip(),
        )
        .itertuples(index=False, name=None)
    )
    actual_groups = set(
        actual[["fold", "model_name"]].itertuples(index=False, name=None)
    )
    if validation_groups != actual_groups:
        completeness_issues.append(
            "fold/model group mismatch between validation and OOS returns"
        )
    for fold, model in validation_groups:
        if not np.isfinite(_number(fold)):
            completeness_issues.append(f"invalid fold for model={model}")
            continue
        fold_key = int(fold)
        expected_dates = expected_dates_by_fold.get(fold_key)
        group = actual.loc[
            actual["fold"].eq(fold) & actual["model_name"].eq(str(model))
        ]
        observed_dates = pd.DatetimeIndex(group["Date"]).unique().sort_values()
        finite = bool(
            group["Date"].notna().all()
            and np.isfinite(group["return"].to_numpy(dtype=float)).all()
        )
        if (
            expected_dates is None
            or not finite
            or not observed_dates.equals(expected_dates)
        ):
            completeness_issues.append(
                f"incomplete fold={fold_key}, model={model}, "
                f"observed={len(observed_dates)}, "
                f"expected={len(expected_dates) if expected_dates is not None else 0}"
            )
    _append_boolean_check(
        checks,
        "walk_forward_fold_model_date_sets_complete",
        not completeness_issues,
        observed=f"issues={completeness_issues}",
        formula=(
            "for every validation fold/model: finite OOS dates equal the complete "
            "underlying return-index slice from test_start through test_end and "
            "count equals test_observations"
        ),
        invalidation=(
            "Omitting even one OOS date can bias CAGR, Sharpe, drawdown and tail risk."
        ),
    )

    previous: dict[str, pd.Series] = {}
    expected_return_frames: list[pd.DataFrame] = []
    turnover_differences: list[float] = []
    cost_differences: list[float] = []
    for (fold, model), group in walk_weights.groupby(
        ["fold", "model_name"],
        sort=True,
    ):
        weights = (
            group.assign(weight=pd.to_numeric(group["weight"], errors="coerce"))
            .dropna(subset=["weight"])
            .groupby(group["ticker"].astype(str))["weight"]
            .sum()
        )
        if weights.empty:
            continue
        prior = previous.get(str(model), pd.Series(dtype=float))
        union = weights.index.union(prior.index)
        expected_turnover = float(
            (
                weights.reindex(union, fill_value=0.0)
                - prior.reindex(union, fill_value=0.0)
            )
            .abs()
            .sum()
        )
        turnover_row = walk_turnover.loc[
            walk_turnover["fold"].eq(fold)
            & walk_turnover["model_name"].astype(str).eq(str(model))
        ]
        if turnover_row.empty:
            turnover_differences.append(float("inf"))
            cost_differences.append(float("inf"))
            continue
        reported_turnover = _number(turnover_row.iloc[0]["turnover"])
        bps = _number(turnover_row.iloc[0]["transaction_cost_bps"])
        reported_cost = _number(turnover_row.iloc[0]["transaction_cost_decimal"])
        expected_cost = expected_turnover * bps / 10000.0
        turnover_differences.append(abs(expected_turnover - reported_turnover))
        cost_differences.append(abs(expected_cost - reported_cost))

        actual_group = actual.loc[
            actual["fold"].eq(fold) & actual["model_name"].astype(str).eq(str(model))
        ].sort_values("Date")
        expected_dates = expected_dates_by_fold.get(int(fold))
        if (
            actual_group.empty
            or expected_dates is None
            or len(actual_group) != len(expected_dates)
            or actual_group["Date"].duplicated().any()
            or not np.isfinite(actual_group["return"].to_numpy(dtype=float)).all()
            or not pd.DatetimeIndex(actual_group["Date"])
            .unique()
            .sort_values()
            .equals(expected_dates)
        ):
            turnover_differences.append(float("inf"))
            cost_differences.append(float("inf"))
            continue
        selected_returns = returns.reindex(
            expected_dates,
            columns=weights.index,
        )
        gross = _independent_portfolio_returns(selected_returns, weights)
        expected = gross.reindex(expected_dates)
        if not expected.empty:
            expected.iloc[0] = expected.iloc[0] - expected_cost
        expected_return_frames.append(
            pd.DataFrame(
                {
                    "Date": actual_group["Date"].to_numpy(),
                    "model_name": str(model),
                    "fold": fold,
                    "expected": expected.to_numpy(dtype=float),
                    "observed": actual_group["return"].to_numpy(dtype=float),
                }
            )
        )
        try:
            previous[str(model)] = _independent_drifted_weights(
                weights,
                selected_returns,
            )
        except ValueError:
            turnover_differences.append(float("inf"))
            cost_differences.append(float("inf"))

    turnover_max = max(turnover_differences, default=float("inf"))
    cost_max = max(cost_differences, default=float("inf"))
    tolerance = absolute_tolerance + relative_tolerance
    _append_boolean_check(
        checks,
        "walk_forward_turnover_reconciles",
        bool(turnover_differences and turnover_max <= tolerance),
        observed=f"max_abs_difference={turnover_max}",
        formula=(
            "turnover_t = sum_i(abs(target_weight_i,t - drifted_pre_trade_weight_i,t)) "
            "including exits"
        ),
        invalidation=(
            "A missing return drift, exit, first allocation, or rebalance leg changes costs."
        ),
    )
    _append_boolean_check(
        checks,
        "walk_forward_transaction_costs_reconcile",
        bool(cost_differences and cost_max <= tolerance),
        observed=f"max_abs_difference={cost_max}",
        formula="cost_t = gross_L1_turnover_t * bps / 10000",
        invalidation="Mismatched bps or turnover convention invalidates net returns.",
    )
    if expected_return_frames:
        replay = pd.concat(expected_return_frames, ignore_index=True)
        return_difference = float((replay["expected"] - replay["observed"]).abs().max())
    else:
        return_difference = float("inf")
    _append_boolean_check(
        checks,
        "walk_forward_net_returns_replay",
        bool(np.isfinite(return_difference) and return_difference <= tolerance),
        observed=f"max_abs_difference={return_difference}",
        formula=(
            "net OOS return = sum_i(w_i * asset_simple_return_i); first fold day "
            "minus turnover * bps / 10000"
        ),
        invalidation="Weight, date, missing-return, or cost alignment differs.",
    )


def _expected_oos_dates_by_fold(
    asset_return_index: pd.Index,
    schedule: pd.DataFrame,
) -> tuple[dict[int, pd.DatetimeIndex], list[str]]:
    required = {"fold", "test_start", "test_end", "test_observations"}
    if schedule.empty or not required.issubset(schedule.columns):
        return {}, ["fold schedule is missing required date/count fields"]
    frame = schedule[list(required)].copy()
    frame["fold"] = pd.to_numeric(frame["fold"], errors="coerce")
    frame["test_start"] = pd.to_datetime(frame["test_start"], errors="coerce")
    frame["test_end"] = pd.to_datetime(frame["test_end"], errors="coerce")
    frame["test_observations"] = pd.to_numeric(
        frame["test_observations"],
        errors="coerce",
    )
    source_dates = pd.DatetimeIndex(pd.to_datetime(asset_return_index, errors="coerce"))
    source_dates = source_dates[source_dates.notna()].unique().sort_values()
    expected: dict[int, pd.DatetimeIndex] = {}
    issues: list[str] = []
    for fold, group in frame.groupby("fold", sort=True, dropna=False):
        if not np.isfinite(_number(fold)):
            issues.append("non-finite fold identifier")
            continue
        fold_key = int(fold)
        starts = pd.DatetimeIndex(group["test_start"]).unique()
        ends = pd.DatetimeIndex(group["test_end"]).unique()
        counts = pd.to_numeric(
            group["test_observations"],
            errors="coerce",
        ).unique()
        if (
            len(starts) != 1
            or len(ends) != 1
            or len(counts) != 1
            or pd.isna(starts[0])
            or pd.isna(ends[0])
            or not np.isfinite(_number(counts[0]))
            or int(counts[0]) <= 0
        ):
            issues.append(f"inconsistent schedule for fold={fold_key}")
            continue
        fold_dates = source_dates[
            (source_dates >= starts[0]) & (source_dates <= ends[0])
        ]
        if len(fold_dates) != int(counts[0]):
            issues.append(
                f"underlying date count mismatch for fold={fold_key}: "
                f"observed={len(fold_dates)}, declared={int(counts[0])}"
            )
            continue
        expected[fold_key] = fold_dates
    return expected, issues


def _append_random_benchmark_reference_checks(
    checks: list[dict[str, object]],
    model_returns: pd.DataFrame,
    random_returns: pd.DataFrame,
    random_weights: pd.DataFrame,
    random_distribution: pd.DataFrame,
    provenance: dict[str, object],
    manifest: dict[str, object],
    asset_returns: pd.DataFrame,
    window_summary: pd.DataFrame,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> None:
    required_random = {"Date", "fold", "portfolio_id", "return"}
    required_weights = {
        "fold",
        "portfolio_id",
        "ticker",
        "target_weight",
        "pre_trade_weight",
        "post_test_weight",
    }
    present = bool(
        not model_returns.empty
        and not random_returns.empty
        and not random_weights.empty
        and not random_distribution.empty
        and required_random.issubset(random_returns.columns)
        and required_weights.issubset(random_weights.columns)
        and provenance
    )
    _append_boolean_check(
        checks,
        "random_benchmark_reference_inputs_present",
        present,
        observed=(
            f"model_rows={len(model_returns)}; random_rows={len(random_returns)}; "
            f"weight_rows={len(random_weights)}; "
            f"distribution_rows={len(random_distribution)}"
        ),
        formula=(
            "raw model OOS rows + random OOS rows + random target/pre-trade/"
            "post-test weights + provenance + summary"
        ),
        invalidation="A scope label without raw comparable evidence is insufficient.",
    )
    if not present:
        return
    model_hashes = _independent_date_hashes(model_returns, "model_name")
    random_hashes = _independent_date_hashes(random_returns, "portfolio_id")
    equal_weight_hash = model_hashes.get("Equal Weight", "missing")
    dates_match = bool(
        equal_weight_hash != "missing"
        and all(value == equal_weight_hash for value in model_hashes.values())
        and all(value == equal_weight_hash for value in random_hashes.values())
    )
    provenance_match = bool(
        provenance.get("benchmark_scope") == "walk_forward_oos_net"
        and provenance.get("provenance_status") == "verified_same_protocol"
        and provenance.get("oos_dates_match") is True
        and provenance.get("model_oos_dates_hash") == equal_weight_hash
        and provenance.get("random_oos_dates_hash") == equal_weight_hash
        and all(
            str(provenance.get(field)) == str(manifest.get(field))
            for field in [
                "run_id",
                "execution_id",
                "data_as_of_date",
                "generated_at",
                "config_hash",
                "input_fingerprint",
                "universe_snapshot_id",
                "data_snapshot_id",
            ]
        )
        and provenance.get("random_weights_hash")
        == _independent_frame_hash(
            random_weights,
            [
                "fold",
                "portfolio_id",
                "ticker",
                "target_weight",
                "pre_trade_weight",
                "post_test_weight",
            ],
        )
    )
    _append_boolean_check(
        checks,
        "random_benchmark_provenance_reconciles",
        bool(dates_match and provenance_match),
        observed=(
            f"dates_match={dates_match}; status={provenance.get('provenance_status')}; "
            f"protocol_hash={provenance.get('protocol_hash')}; "
            f"random_weights_hash={provenance.get('random_weights_hash')}"
        ),
        formula=(
            "identical unique OOS dates plus matching full run identity and "
            "content-hashed random weight paths"
        ),
        invalidation="Static, stale, differently dated, or differently configured evidence.",
    )

    weights = random_weights.copy()
    for column in ["fold", "portfolio_id"]:
        weights[column] = pd.to_numeric(weights[column], errors="coerce")
    for column in ["target_weight", "pre_trade_weight", "post_test_weight"]:
        weights[column] = pd.to_numeric(weights[column], errors="coerce")
    raw_returns = random_returns.copy()
    raw_returns["Date"] = pd.to_datetime(raw_returns["Date"], errors="coerce")
    raw_returns["return"] = pd.to_numeric(raw_returns["return"], errors="coerce")
    raw_returns["fold"] = pd.to_numeric(raw_returns["fold"], errors="coerce")
    raw_returns["portfolio_id"] = pd.to_numeric(
        raw_returns["portfolio_id"],
        errors="coerce",
    )
    expected_dates_by_fold, schedule_issues = _expected_oos_dates_by_fold(
        asset_returns.index,
        window_summary,
    )
    completeness_issues = list(schedule_issues)
    model_path = model_returns.copy()
    model_path["Date"] = pd.to_datetime(model_path["Date"], errors="coerce")
    model_path["fold"] = pd.to_numeric(model_path["fold"], errors="coerce")
    model_path["return"] = pd.to_numeric(model_path["return"], errors="coerce")
    for (fold, model), group in model_path.groupby(
        ["fold", "model_name"],
        sort=True,
        dropna=False,
    ):
        if not np.isfinite(_number(fold)):
            completeness_issues.append(f"invalid model fold for model={model}")
            continue
        expected_dates = expected_dates_by_fold.get(int(fold))
        observed_dates = pd.DatetimeIndex(group["Date"]).unique().sort_values()
        finite = bool(
            group["Date"].notna().all()
            and np.isfinite(group["return"].to_numpy(dtype=float)).all()
        )
        if (
            expected_dates is None
            or not finite
            or not observed_dates.equals(expected_dates)
        ):
            completeness_issues.append(
                f"incomplete model path fold={int(fold)}, model={model}"
            )
    expected_random_groups = set(
        weights[["fold", "portfolio_id"]].itertuples(index=False, name=None)
    )
    observed_random_groups = set(
        raw_returns[["fold", "portfolio_id"]].itertuples(index=False, name=None)
    )
    if expected_random_groups != observed_random_groups:
        completeness_issues.append(
            "random fold/portfolio groups do not match the weight evidence"
        )
    for fold, portfolio_id in expected_random_groups:
        if not np.isfinite(_number(fold)) or not np.isfinite(_number(portfolio_id)):
            completeness_issues.append("invalid random fold or portfolio identifier")
            continue
        expected_dates = expected_dates_by_fold.get(int(fold))
        group = raw_returns.loc[
            raw_returns["fold"].eq(fold) & raw_returns["portfolio_id"].eq(portfolio_id)
        ]
        observed_dates = pd.DatetimeIndex(group["Date"]).unique().sort_values()
        finite = bool(
            group["Date"].notna().all()
            and np.isfinite(group["return"].to_numpy(dtype=float)).all()
        )
        if (
            expected_dates is None
            or not finite
            or not observed_dates.equals(expected_dates)
        ):
            completeness_issues.append(
                f"incomplete random path fold={int(fold)}, "
                f"portfolio={int(portfolio_id)}"
            )
    _append_boolean_check(
        checks,
        "model_and_random_oos_paths_match_expected_fold_dates",
        not completeness_issues,
        observed=f"issues={completeness_issues}",
        formula=(
            "every model and random fold path uses the exact finite underlying "
            "test-window date set declared by test_observations"
        ),
        invalidation=(
            "A synchronized date omission can preserve cross-path hashes while "
            "biasing every performance and risk statistic."
        ),
    )
    duplicate_weight_rows = int(
        weights.duplicated(["fold", "portfolio_id", "ticker"], keep=False).sum()
    )
    duplicate_return_rows = int(
        raw_returns.duplicated(["portfolio_id", "Date"], keep=False).sum()
    )
    tolerance = absolute_tolerance + relative_tolerance
    max_weight = _number(provenance.get("max_weight"))
    bps = _number(provenance.get("transaction_cost_bps"))
    expected_selected_by_fold: dict[int, set[str]] = {}
    if not window_summary.empty and {"fold", "selected_tickers"}.issubset(
        window_summary.columns
    ):
        for row in window_summary[["fold", "selected_tickers"]].itertuples(index=False):
            expected_selected_by_fold[int(row.fold)] = {
                ticker
                for ticker in str(row.selected_tickers).split(";")
                if ticker.strip()
            }

    previous_by_portfolio: dict[int, pd.Series] = {}
    replay_differences: list[float] = []
    pre_trade_differences: list[float] = []
    post_test_differences: list[float] = []
    constraint_results: list[bool] = []
    universe_results: list[bool] = []
    for (portfolio_id, fold), group in weights.groupby(
        ["portfolio_id", "fold"],
        sort=True,
    ):
        portfolio_key = int(portfolio_id)
        fold_key = int(fold)
        target = group.set_index(group["ticker"].astype(str))["target_weight"]
        stored_pre = group.set_index(group["ticker"].astype(str))["pre_trade_weight"]
        stored_post = group.set_index(group["ticker"].astype(str))["post_test_weight"]
        prior = previous_by_portfolio.get(portfolio_key, pd.Series(dtype=float))
        union = target.index.union(prior.index).union(stored_pre.index)
        expected_pre = prior.reindex(union, fill_value=0.0)
        observed_pre = stored_pre.reindex(union, fill_value=0.0)
        pre_trade_differences.append(float((expected_pre - observed_pre).abs().max()))
        nonzero_target = target.loc[target.abs() > 1e-12]
        constraint_results.append(
            bool(
                np.isfinite(target.to_numpy(dtype=float)).all()
                and abs(float(target.sum()) - 1.0) <= tolerance
                and float(target.min()) >= -tolerance
                and np.isfinite(max_weight)
                and float(target.max()) <= max_weight + tolerance
            )
        )
        expected_selected = expected_selected_by_fold.get(fold_key)
        universe_results.append(
            bool(
                expected_selected
                and set(nonzero_target.index.astype(str)) == expected_selected
            )
        )
        observed_group = raw_returns.loc[
            raw_returns["fold"].eq(fold) & raw_returns["portfolio_id"].eq(portfolio_id)
        ].sort_values("Date")
        if observed_group.empty:
            replay_differences.append(float("inf"))
            post_test_differences.append(float("inf"))
            continue
        selected_returns = asset_returns.reindex(
            pd.DatetimeIndex(observed_group["Date"]),
            columns=nonzero_target.index,
        )
        gross = _independent_portfolio_returns(selected_returns, nonzero_target)
        turnover = float(
            (
                target.reindex(union, fill_value=0.0)
                - prior.reindex(union, fill_value=0.0)
            )
            .abs()
            .sum()
        )
        expected_cost = turnover * bps / 10000.0
        expected_net = gross.reindex(pd.DatetimeIndex(observed_group["Date"]))
        if len(expected_net) != len(observed_group) or expected_net.isna().any():
            replay_differences.append(float("inf"))
            post_test_differences.append(float("inf"))
            continue
        expected_net.iloc[0] = expected_net.iloc[0] - expected_cost
        replay_differences.append(
            float(
                np.max(
                    np.abs(
                        expected_net.to_numpy(dtype=float)
                        - observed_group["return"].to_numpy(dtype=float)
                    )
                )
            )
        )
        try:
            expected_post = _independent_drifted_weights(
                nonzero_target,
                selected_returns,
            )
        except ValueError:
            post_test_differences.append(float("inf"))
            continue
        post_union = expected_post.index.union(stored_post.index)
        post_test_differences.append(
            float(
                (
                    expected_post.reindex(post_union, fill_value=0.0)
                    - stored_post.reindex(post_union, fill_value=0.0)
                )
                .abs()
                .max()
            )
        )
        previous_by_portfolio[portfolio_key] = expected_post

    max_pre_trade_difference = max(pre_trade_differences, default=float("inf"))
    max_post_test_difference = max(post_test_differences, default=float("inf"))
    max_replay_difference = max(replay_differences, default=float("inf"))
    _append_boolean_check(
        checks,
        "random_benchmark_weight_paths_reconcile",
        bool(
            duplicate_weight_rows == 0
            and max_pre_trade_difference <= tolerance
            and max_post_test_difference <= tolerance
        ),
        observed=(
            f"duplicate_weight_rows={duplicate_weight_rows}; "
            f"max_pre_trade_difference={max_pre_trade_difference}; "
            f"max_post_test_difference={max_post_test_difference}"
        ),
        formula=(
            "pre_trade_t = normalized(target_(t-1) * product(1 + asset_returns)); "
            "post_test_t applies the same buy-and-hold drift"
        ),
        invalidation="Target, pre-trade, or post-test random weights are missing or stale.",
    )
    _append_boolean_check(
        checks,
        "random_benchmark_weight_constraints_reconcile",
        bool(
            constraint_results
            and all(constraint_results)
            and universe_results
            and all(universe_results)
        ),
        observed=(
            f"fold_portfolios={len(constraint_results)}; max_weight={max_weight}; "
            f"constraint_failures={constraint_results.count(False)}; "
            f"universe_failures={universe_results.count(False)}"
        ),
        formula=(
            "target weights are finite, long-only, sum to one, respect configured "
            "max weight, and equal each fold's training-selected universe"
        ),
        invalidation="A random portfolio uses a different universe or constraint set.",
    )
    _append_boolean_check(
        checks,
        "random_benchmark_net_returns_replay",
        bool(
            duplicate_return_rows == 0
            and np.isfinite(max_replay_difference)
            and max_replay_difference <= tolerance
        ),
        observed=(
            f"duplicate_return_rows={duplicate_return_rows}; "
            f"max_abs_difference={max_replay_difference}"
        ),
        formula=(
            "net random OOS return = target-weight asset return; first fold day "
            "minus drift-aware gross L1 turnover * bps / 10000"
        ),
        invalidation="Random returns are static, gross, cost-misaligned, or unreplayable.",
    )

    risk_free = _number(provenance.get("risk_free_rate_annual"))
    metric_comparisons: list[bool] = []
    metric_rows = 0
    for portfolio_id, sample in raw_returns.groupby("portfolio_id", sort=True):
        series = (
            sample.dropna(subset=["Date", "return"])
            .sort_values("Date")
            .set_index("Date")["return"]
        )
        metrics = _independent_metrics(series, risk_free_rate_annual=risk_free)
        reported = random_distribution.loc[
            pd.to_numeric(
                random_distribution["portfolio_id"],
                errors="coerce",
            ).eq(portfolio_id)
        ]
        if reported.empty:
            metric_comparisons.append(False)
            continue
        row = reported.iloc[0]
        metric_rows += 1
        for metric in [
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
        ]:
            expected_key = "annualized_volatility" if metric == "volatility" else metric
            expected = metrics[expected_key]
            observed = _number(row.get(metric))
            metric_tolerance = absolute_tolerance + relative_tolerance * abs(expected)
            metric_comparisons.append(abs(expected - observed) <= metric_tolerance)
    _append_boolean_check(
        checks,
        "random_benchmark_metric_replay",
        bool(metric_comparisons and all(metric_comparisons)),
        observed=(
            f"portfolios_compared={metric_rows}; "
            f"metrics_compared={len(metric_comparisons)}"
        ),
        formula="independent metrics from raw stitched random OOS net return path",
        invalidation="Distribution metrics are in-sample, gross, stale, or differently dated.",
    )


def _append_bootstrap_input_checks(
    checks: list[dict[str, object]],
    walk_returns: pd.DataFrame,
    uncertainty: pd.DataFrame,
) -> None:
    required = {
        "Date",
        "model_name",
        "return",
    }
    present = bool(
        not walk_returns.empty
        and required.issubset(walk_returns.columns)
        and not uncertainty.empty
        and {
            "model_name",
            "paired_observations",
            "bootstrap_samples",
            "block_length",
            "confidence_level",
            "random_state",
        }.issubset(uncertainty.columns)
    )
    _append_boolean_check(
        checks,
        "paired_bootstrap_inputs_present",
        present,
        observed=f"return_rows={len(walk_returns)}; uncertainty_rows={len(uncertainty)}",
        formula="paired model and Equal Weight OOS rows on common dates",
        invalidation="Unpaired dates or undocumented bootstrap settings invalidate CIs.",
    )
    if not present:
        return
    frame = walk_returns[["Date", "model_name", "return"]].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["return"] = pd.to_numeric(frame["return"], errors="coerce")
    clean = frame.dropna()
    duplicate_pairs = int(clean.duplicated(["Date", "model_name"], keep=False).sum())
    if duplicate_pairs:
        _append_boolean_check(
            checks,
            "paired_bootstrap_observation_counts_reconcile",
            False,
            observed=f"duplicate_model_date_rows={duplicate_pairs}",
            formula="n_paired = count(one model return per OOS date)",
            invalidation=(
                "Overlapping or duplicated model-date rows double-count the "
                "bootstrap sample."
            ),
        )
        return
    pivot = clean.pivot(index="Date", columns="model_name", values="return")
    if "Equal Weight" not in pivot:
        paired_ok = False
    else:
        paired_ok = True
        for _, row in uncertainty.iterrows():
            model = str(row["model_name"])
            if model == "Equal Weight" or model not in pivot:
                continue
            expected = int(pivot[[model, "Equal Weight"]].dropna().shape[0])
            paired_ok = paired_ok and expected == int(row["paired_observations"])
            paired_ok = paired_ok and int(row["bootstrap_samples"]) > 0
            paired_ok = paired_ok and int(row["block_length"]) > 0
            paired_ok = paired_ok and 0.0 < float(row["confidence_level"]) < 1.0
    _append_boolean_check(
        checks,
        "paired_bootstrap_observation_counts_reconcile",
        paired_ok,
        observed=f"models={len(uncertainty)}",
        formula="n_paired = count(nonmissing(model_t, EqualWeight_t))",
        invalidation="Unpaired samples or invalid block settings invalidate uncertainty.",
    )


def _append_covariance_checks(
    checks: list[dict[str, object]],
    returns: pd.DataFrame,
    comparison: pd.DataFrame,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> None:
    clean = returns.dropna(how="any")
    row = (
        comparison.loc[comparison["estimator"].eq("sample_covariance")]
        if not comparison.empty and "estimator" in comparison
        else pd.DataFrame()
    )
    present = bool(clean.shape[0] >= 2 and not row.empty)
    _append_boolean_check(
        checks,
        "sample_covariance_reference_inputs_present",
        present,
        observed=f"complete_rows={len(clean)}; reported_rows={len(row)}",
        formula="sample covariance on common complete-case daily return matrix",
        invalidation="Different missing-data samples invalidate matrix comparison.",
    )
    if not present:
        return
    covariance = clean.cov().to_numpy(dtype=float) * TRADING_DAYS
    symmetric = 0.5 * (covariance + covariance.T)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    expected = {
        "average_variance": float(np.diag(covariance).mean()),
        "condition_number": float(np.linalg.cond(covariance)),
        "min_eigenvalue": float(eigenvalues.min()),
    }
    reported = row.iloc[0]
    reconciled = []
    for field, value in expected.items():
        observed = _number(reported.get(field))
        tolerance = absolute_tolerance + relative_tolerance * abs(value)
        reconciled.append(
            np.isfinite(observed)
            and (
                abs(value - observed) <= tolerance
                or (field == "condition_number" and value > 1e12 and observed > 1e12)
            )
        )
    psd = bool(eigenvalues.min() >= -1e-10)
    _append_boolean_check(
        checks,
        "sample_covariance_properties_reconcile",
        bool(all(reconciled) and bool(reported.get("psd_check")) == psd),
        observed=(
            f"min_eigenvalue={eigenvalues.min()}; "
            f"condition_number={expected['condition_number']}"
        ),
        formula="Sigma = sample_cov(complete cases) * 252; eigvalsh(Sigma)",
        invalidation="Frequency, missing-data policy, or estimator identity differs.",
    )


def _append_optimizer_constraint_checks(
    checks: list[dict[str, object]],
    weights: pd.DataFrame,
    league: pd.DataFrame,
) -> None:
    present = bool(
        not weights.empty
        and {"model_name", "ticker", "weight"}.issubset(weights.columns)
        and not league.empty
        and {
            "model_name",
            "actual_status",
            "weight_sum",
            "max_weight",
            "configured_max_weight",
        }.issubset(league.columns)
    )
    _append_boolean_check(
        checks,
        "optimizer_constraint_inputs_present",
        present,
        observed=f"weight_rows={len(weights)}; league_rows={len(league)}",
        formula="reported executable model weights and status rows",
        invalidation="Missing weights can hide optimizer fallback or infeasibility.",
    )
    if not present:
        return
    executable = league.loc[
        league["actual_status"].astype(str).isin(["actually_run", "benchmark_only"])
        & ~league["model_name"].astype(str).eq("Random Portfolios")
    ]
    valid = True
    for _, row in executable.iterrows():
        model = str(row["model_name"])
        model_weights = pd.to_numeric(
            weights.loc[weights["model_name"].astype(str).eq(model), "weight"],
            errors="coerce",
        ).dropna()
        valid = valid and not model_weights.empty
        if model_weights.empty:
            continue
        valid = valid and abs(float(model_weights.sum()) - 1.0) <= 1e-9
        valid = valid and bool((model_weights >= -1e-12).all())
        valid = (
            valid
            and abs(float(model_weights.max()) - _number(row["max_weight"])) <= 1e-9
        )
        valid = valid and bool(
            float(model_weights.max()) <= _number(row["configured_max_weight"]) + 1e-9
        )
        valid = (
            valid
            and abs(float(model_weights.sum()) - _number(row["weight_sum"])) <= 1e-9
        )
    _append_boolean_check(
        checks,
        "all_executable_optimizer_constraints_reconcile",
        bool(valid and not executable.empty),
        observed=f"executable_models={len(executable)}",
        formula=(
            "sum(w)=1; min(w)>=0; observed max and sum match model league; "
            "observed max <= configured max-weight cap"
        ),
        invalidation="A mislabeled fallback, negative weight, cap breach, or missing model.",
    )


def _append_model_selection_reconciliation_checks(
    checks: list[dict[str, object]],
    selection: pd.DataFrame,
    random_percentiles: pd.DataFrame,
    random_provenance: dict[str, object],
    robustness: dict[str, object],
    leakage_audit: pd.DataFrame,
    manifest: dict[str, object],
    absolute_tolerance: float,
    relative_tolerance: float,
) -> None:
    present = bool(
        not selection.empty
        and "model_name" in selection
        and not random_percentiles.empty
        and "model_name" in random_percentiles
    )
    _append_boolean_check(
        checks,
        "model_selection_reference_inputs_present",
        present,
        observed=(
            f"selection_rows={len(selection)}; percentile_rows={len(random_percentiles)}"
        ),
        formula="selection rows reconcile to benchmark and evidence artifacts",
        invalidation="Missing component evidence makes a final gate unverifiable.",
    )
    if not present:
        return
    merged = selection.merge(
        random_percentiles[["model_name", "sharpe_percentile"]],
        on="model_name",
        suffixes=("_selection", "_benchmark"),
        how="left",
    )
    differences = (
        pd.to_numeric(merged["random_sharpe_percentile"], errors="coerce")
        - pd.to_numeric(merged["sharpe_percentile"], errors="coerce")
    ).abs()
    finite = differences.dropna()
    tolerance = absolute_tolerance + relative_tolerance
    percentile_ok = bool(not finite.empty and float(finite.max()) <= tolerance)
    identity_ok = all(
        str(random_provenance.get(field)) == str(manifest.get(field))
        for field in [
            "run_id",
            "execution_id",
            "data_as_of_date",
            "generated_at",
            "config_hash",
            "input_fingerprint",
            "universe_snapshot_id",
            "data_snapshot_id",
        ]
    )
    random_gate_expected = bool(
        random_provenance.get("provenance_status") == "verified_same_protocol"
        and identity_ok
    )
    reported_random_gate = selection["random_sharpe_gate_pass"].map(_truthy)
    no_false_random_gate = bool(random_gate_expected or not reported_random_gate.any())
    robustness_is_promotion_grade = bool(
        robustness.get("robustness_status") == "promotion_grade_nested_walk_forward_oos"
        and robustness.get("robustness_method")
        == "nested_chronological_walk_forward_oos"
        and _truthy(robustness.get("promotion_eligible"))
        and all(
            str(robustness.get(field)) == str(manifest.get(field))
            for field in [
                "run_id",
                "config_hash",
                "input_fingerprint",
                "universe_snapshot_id",
                "data_snapshot_id",
            ]
        )
    )
    reported_robust_gate = selection["robustness_gate_pass"].map(_truthy)
    no_false_robust_gate = bool(
        robustness_is_promotion_grade or not reported_robust_gate.any()
    )
    identity_fields = [
        "run_id",
        "execution_id",
        "data_as_of_date",
        "generated_at",
        "config_hash",
        "input_fingerprint",
        "universe_snapshot_id",
        "data_snapshot_id",
    ]
    required_leakage_checks = {
        "train_end_before_test_start",
        "scores_as_of_not_after_train_end",
        "selected_tickers_available_in_train",
        "scores_recomputed_inside_fold",
    }
    leakage_valid = bool(
        not leakage_audit.empty
        and {
            "fold",
            "check",
            "passed",
            "audit_status",
            "evidence_scope",
            *identity_fields,
        }.issubset(leakage_audit.columns)
        and not leakage_audit.duplicated(["fold", "check"]).any()
        and all(
            set(group["check"].astype(str)) == required_leakage_checks
            for _, group in leakage_audit.groupby("fold", sort=False)
        )
        and leakage_audit["passed"].map(_truthy).all()
        and leakage_audit["audit_status"]
        .astype(str)
        .eq("passed_with_current_universe_survivorship_limitation")
        .all()
        and leakage_audit["evidence_scope"]
        .astype(str)
        .eq("current_universe_not_point_in_time")
        .all()
        and all(
            set(leakage_audit[field].dropna().astype(str)) == {str(manifest.get(field))}
            for field in identity_fields
        )
    )
    reported_leakage_gate = (
        selection["leakage_gate_pass"].map(_truthy)
        if "leakage_gate_pass" in selection
        else pd.Series([True])
    )
    leakage_gate_consistent = bool(
        (leakage_valid and reported_leakage_gate.all())
        or (not leakage_valid and not reported_leakage_gate.any())
    )
    _append_boolean_check(
        checks,
        "model_selection_evidence_reconciles",
        bool(
            percentile_ok
            and no_false_random_gate
            and no_false_robust_gate
            and leakage_gate_consistent
        ),
        observed=(
            f"percentile_max_diff={finite.max() if not finite.empty else 'missing'}; "
            f"random_provenance_valid={random_gate_expected}; "
            f"robustness_promotion_grade={robustness_is_promotion_grade}; "
            f"leakage_valid={leakage_valid}; "
            f"reported_leakage_passes={int(reported_leakage_gate.sum())}"
        ),
        formula=(
            "selection percentiles equal benchmark artifact; random and robustness "
            "gates fail closed unless same-run promotion evidence is proven; "
            "leakage checks are complete, current-run and pass fail-closed"
        ),
        invalidation="Stale, diagnostic, missing, or relabeled evidence reaches selection.",
    )


def _independent_date_hashes(
    frame: pd.DataFrame,
    group_column: str,
) -> dict[object, str]:
    if frame.empty or not {group_column, "Date"}.issubset(frame.columns):
        return {}
    hashes: dict[object, str] = {}
    for key, group in frame.groupby(group_column, sort=True):
        dates = (
            pd.to_datetime(group["Date"], errors="coerce")
            .dropna()
            .drop_duplicates()
            .sort_values()
        )
        payload = "\n".join(dates.dt.strftime("%Y-%m-%d")).encode("utf-8")
        hashes[key] = f"dates-{hashlib.sha256(payload).hexdigest()[:24]}"
    return hashes


def _independent_frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    """Hash a stable evidence projection without production hash helpers."""
    if frame.empty or not set(columns).issubset(frame.columns):
        return "missing"
    normalized = frame[columns].copy()
    for column in columns:
        if "date" in column or column.endswith(("_start", "_end")):
            normalized[column] = pd.to_datetime(
                normalized[column],
                errors="coerce",
            ).dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_numeric_dtype(normalized[column]):
            numeric = pd.to_numeric(normalized[column], errors="coerce")
            normalized[column] = numeric.map(
                lambda value: (
                    f"{float(value):.12g}" if np.isfinite(value) else "missing"
                )
            )
        else:
            normalized[column] = normalized[column].fillna("").astype(str)
    normalized = normalized.sort_values(columns, kind="stable")
    payload = normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return f"frame-{hashlib.sha256(payload).hexdigest()[:24]}"


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


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
    for field in RUN_IDENTITY_FIELDS:
        frame[field] = str(manifest.get(field, "missing"))
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
