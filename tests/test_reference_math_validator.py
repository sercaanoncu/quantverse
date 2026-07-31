import hashlib
import json

import numpy as np
import pandas as pd

from scripts.qa.verify_quantverse_reference_math import (
    _independent_frame_hash,
    _read_csv,
    verify_reference_math,
)


def test_reference_math_validator_recalculates_and_detects_adversarial_tampering(
    tmp_path,
):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    dates = pd.bdate_range("2024-01-02", periods=260)
    steps = np.arange(len(dates), dtype=float)
    prices = pd.DataFrame(
        {
            "Date": dates,
            "AAA": 100.0 * np.cumprod(1.0 + 0.0005 + 0.002 * np.sin(steps)),
            "BBB": 80.0 * np.cumprod(1.0 + 0.0003 + 0.001 * np.cos(steps)),
        }
    )
    price_indexed = prices.set_index("Date")
    simple = price_indexed.pct_change(fill_method=None).dropna()
    log_returns = np.log(price_indexed / price_indexed.shift(1)).dropna()
    fx_prices = pd.DataFrame(
        {
            "Date": dates,
            "EURUSD=X": 1.08 * np.cumprod(np.full(len(dates), 1.0002)),
        }
    )
    fx_indexed = fx_prices.set_index("Date")
    eur_local = pd.Series(
        0.0004 + 0.0015 * np.sin(steps),
        index=dates,
        name="EUR_ASSET",
    )
    eur_fx_return = fx_indexed["EURUSD=X"].pct_change(fill_method=None)
    eur_usd = ((1.0 + eur_local) * (1.0 + eur_fx_return)) - 1.0
    simple["EUR_ASSET"] = eur_local.reindex(simple.index)
    log_returns["EUR_ASSET"] = np.log1p(simple["EUR_ASSET"])
    simple_usd = simple.copy()
    simple_usd["EUR_ASSET"] = eur_usd.reindex(simple.index)
    _write_matrix(prices, processed / "global_security_prices.csv")
    _write_matrix(
        simple.reset_index(),
        processed / "global_security_simple_returns_local.csv",
    )
    _write_matrix(
        log_returns.reset_index(),
        processed / "global_security_log_returns_local.csv",
    )
    _write_matrix(
        log_returns.reset_index(),
        processed / "global_security_log_returns.csv",
    )
    _write_matrix(
        simple_usd.reset_index(),
        processed / "global_security_simple_returns_usd.csv",
    )
    fx_prices.to_csv(processed / "global_fx_prices.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "EUR_ASSET"],
            "currency": ["USD", "USD", "EUR"],
            "fx_ticker": ["", "", "EURUSD=X"],
            "inversion_required": [False, False, False],
            "max_forward_fill_days": [0, 0, 0],
            "fx_normalization_status": [
                "native_base",
                "native_base",
                "fx_normalized",
            ],
        }
    ).to_csv(processed / "global_fx_normalization_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["AAA", "BBB"],
            "weight": [0.6, 0.4],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)

    portfolio = simple.mul(pd.Series({"AAA": 0.6, "BBB": 0.4}), axis=1).sum(axis=1)
    risk_free_rate = 0.05
    risk = _risk_metrics(portfolio, risk_free_rate=risk_free_rate)
    pd.DataFrame([{"model_name": "Equal Weight", **risk}]).to_csv(
        processed / "global_portfolio_risk_report.csv", index=False
    )
    _risk_contributions(
        simple[["AAA", "BBB"]],
        pd.Series({"AAA": 0.6, "BBB": 0.4}),
    ).to_csv(processed / "global_risk_contribution_report.csv", index=False)
    (processed / "global_final_model_decision.json").write_text(
        json.dumps({"final_selected_model": "Equal Weight"}), encoding="utf-8"
    )
    manifest = {
        "run_id": "unit-run",
        "execution_id": "unit-execution",
        "data_as_of_date": "2024-12-31",
        "generated_at": "2025-01-01T00:00:00+00:00",
        "config_hash": "config-unit",
        "input_fingerprint": "input-unit",
        "universe_snapshot_id": "universe-unit",
        "data_snapshot_id": "data-unit",
    }
    (processed / "quantverse_v2_run_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _write_expanded_reference_artifacts(
        processed,
        simple,
        manifest,
        risk_free_rate,
    )

    checks = verify_reference_math(tmp_path)

    assert checks["passed"].all()
    sharpe_formula = checks.loc[
        checks["check"].eq("final_portfolio_sharpe"),
        "formula_or_method",
    ].iloc[0]
    assert "compounded_daily_risk_free_hurdle" in sharpe_formula

    leakage_path = processed / "global_walk_forward_leakage_audit.csv"
    original_leakage = pd.read_csv(leakage_path)
    additional_check = original_leakage.iloc[[0]].copy()
    additional_check["check"] = "representative_liquidity_uses_no_current_profile_data"
    pd.concat([original_leakage, additional_check], ignore_index=True).to_csv(
        leakage_path,
        index=False,
    )

    additive_leakage_checks = verify_reference_math(tmp_path)

    assert _check_passed(
        additive_leakage_checks,
        "model_selection_evidence_reconciles",
    )
    original_leakage.to_csv(leakage_path, index=False)

    random_weights_path = processed / "global_walk_forward_random_weights.csv"
    original_random_weights = pd.read_csv(random_weights_path)
    tampered_random_weights = original_random_weights.copy()
    tampered_random_weights.loc[0, "target_weight"] += 0.05
    tampered_random_weights.to_csv(random_weights_path, index=False)

    random_weight_tamper_checks = verify_reference_math(tmp_path)

    assert not _check_passed(
        random_weight_tamper_checks,
        "random_benchmark_provenance_reconciles",
    )
    assert not _check_passed(
        random_weight_tamper_checks,
        "random_benchmark_weight_constraints_reconcile",
    )
    assert not _check_passed(
        random_weight_tamper_checks,
        "random_benchmark_net_returns_replay",
    )
    original_random_weights.to_csv(random_weights_path, index=False)

    risk_path = processed / "global_portfolio_risk_report.csv"
    tampered = pd.read_csv(risk_path)
    tampered.loc[0, "cagr"] += 0.10
    tampered.to_csv(risk_path, index=False)

    tampered_checks = verify_reference_math(tmp_path)

    cagr_check = tampered_checks.loc[
        tampered_checks["check"].eq("final_portfolio_cagr")
    ].iloc[0]
    assert not bool(cagr_check["passed"])

    pd.DataFrame([{"model_name": "Equal Weight", **risk}]).to_csv(
        risk_path,
        index=False,
    )
    usd_path = processed / "global_security_simple_returns_usd.csv"
    wrong_fx = pd.read_csv(usd_path)
    wrong_fx["EUR_ASSET"] = (1.0 + simple["EUR_ASSET"].to_numpy()) * (
        1.0 - eur_fx_return.reindex(simple.index).to_numpy()
    ) - 1.0
    wrong_fx.to_csv(usd_path, index=False)

    wrong_direction_checks = verify_reference_math(tmp_path)

    fx_check = wrong_direction_checks.loc[
        wrong_direction_checks["check"].eq("non_native_fx_conversion_replay")
    ].iloc[0]
    assert not bool(fx_check["passed"])

    _write_matrix(simple_usd.reset_index(), usd_path)
    walk_path = processed / "global_walk_forward_returns.csv"
    original_walk = pd.read_csv(walk_path)
    pd.concat([original_walk, original_walk.iloc[[0]]], ignore_index=True).to_csv(
        walk_path,
        index=False,
    )
    overlap_checks = verify_reference_math(tmp_path)
    assert not _check_passed(overlap_checks, "stitched_oos_model_dates_unique")

    original_walk.to_csv(walk_path, index=False)
    random_returns_path = processed / "global_walk_forward_random_returns.csv"
    original_random_returns = pd.read_csv(random_returns_path)
    provenance_path = processed / "global_walk_forward_random_benchmark_provenance.json"
    original_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    removed_date = pd.to_datetime(original_walk.loc[0, "Date"])
    shortened_walk = original_walk.loc[
        pd.to_datetime(original_walk["Date"]).ne(removed_date)
    ]
    shortened_random = original_random_returns.loc[
        pd.to_datetime(original_random_returns["Date"]).ne(removed_date)
    ]
    shortened_walk.to_csv(walk_path, index=False)
    shortened_random.to_csv(random_returns_path, index=False)
    shortened_dates = pd.DatetimeIndex(
        pd.to_datetime(shortened_walk["Date"]).unique()
    ).sort_values()
    shortened_hash = _date_hash(shortened_dates)
    shortened_provenance = {
        **original_provenance,
        "model_oos_dates_hash": shortened_hash,
        "random_oos_dates_hash": shortened_hash,
    }
    provenance_path.write_text(
        json.dumps(shortened_provenance),
        encoding="utf-8",
    )

    shortened_checks = verify_reference_math(tmp_path)

    assert not _check_passed(
        shortened_checks,
        "walk_forward_fold_model_date_sets_complete",
    )
    assert not _check_passed(
        shortened_checks,
        "model_and_random_oos_paths_match_expected_fold_dates",
    )
    original_walk.to_csv(walk_path, index=False)
    original_random_returns.to_csv(random_returns_path, index=False)
    provenance_path.write_text(
        json.dumps(original_provenance),
        encoding="utf-8",
    )

    weights_path = processed / "global_portfolio_league_weights.csv"
    original_weights = pd.read_csv(weights_path)
    impossible_weights = original_weights.copy()
    impossible_weights["weight"] = [0.8, 0.4]
    impossible_weights.to_csv(weights_path, index=False)
    impossible_weight_checks = verify_reference_math(tmp_path)
    assert not _check_passed(impossible_weight_checks, "final_weight_sum")

    original_weights.to_csv(weights_path, index=False)
    wrong_tail = pd.DataFrame([{"model_name": "Equal Weight", **risk}])
    wrong_tail.loc[0, "cvar_95"] = abs(float(wrong_tail.loc[0, "cvar_95"]))
    wrong_tail.to_csv(risk_path, index=False)
    wrong_tail_checks = verify_reference_math(tmp_path)
    assert not _check_passed(wrong_tail_checks, "final_portfolio_cvar_95")

    pd.DataFrame([{"model_name": "Equal Weight", **risk}]).to_csv(
        risk_path,
        index=False,
    )
    zero_filled = simple_usd.reset_index()
    zero_filled.loc[0, "AAA"] = 0.0
    _write_matrix(zero_filled, usd_path)
    zero_fill_checks = verify_reference_math(tmp_path)
    assert not _check_passed(
        zero_fill_checks,
        "native_base_usd_returns_equal_local_returns",
    )

    missing_selected = simple_usd.reset_index()
    missing_selected.loc[0, "AAA"] = np.nan
    _write_matrix(missing_selected, usd_path)
    missing_return_checks = verify_reference_math(tmp_path)
    assert not _check_passed(
        missing_return_checks,
        "final_portfolio_annualized_return",
    )


def _write_matrix(frame: pd.DataFrame, path) -> None:
    output = frame.copy()
    output.columns = ["Date", *output.columns[1:]]
    output.to_csv(path, index=False)


def _check_passed(checks: pd.DataFrame, name: str) -> bool:
    row = checks.loc[checks["check"].eq(name)]
    assert len(row) == 1
    return bool(row.iloc[0]["passed"])


def _risk_metrics(
    returns: pd.Series,
    *,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    wealth = (1.0 + returns).cumprod()
    total_return = float(wealth.iloc[-1] - 1.0)
    annualized_return = float(returns.mean() * 252)
    volatility = float(returns.std(ddof=1) * np.sqrt(252))
    daily_hurdle = (1.0 + risk_free_rate) ** (1.0 / 252) - 1.0
    excess = returns - daily_hurdle
    annualized_excess = float(excess.mean() * 252)
    downside = float(
        np.sqrt(np.mean(np.minimum(excess.to_numpy(dtype=float), 0.0) ** 2))
        * np.sqrt(252)
    )
    var_95 = float(returns.quantile(0.05))
    max_drawdown = float((wealth / wealth.cummax().clip(lower=1.0) - 1.0).min())
    cagr = float((1.0 + total_return) ** (252 / len(returns)) - 1.0)
    return {
        "cagr": cagr,
        "annualized_return": annualized_return,
        "annualized_volatility": volatility,
        "sharpe": annualized_excess / volatility,
        "sortino": annualized_excess / downside,
        "max_drawdown": max_drawdown,
        "var_95": var_95,
        "cvar_95": float(returns.loc[returns <= var_95].mean()),
        "calmar": cagr / abs(max_drawdown),
        "total_return": total_return,
        "risk_free_rate_annual": risk_free_rate,
    }


def _risk_contributions(returns: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    covariance = returns.cov().to_numpy(dtype=float) * 252
    vector = weights.to_numpy(dtype=float)
    volatility = float(np.sqrt(vector @ covariance @ vector))
    marginal = covariance @ vector / volatility
    component = vector * marginal
    return pd.DataFrame(
        {
            "model_name": "Equal Weight",
            "ticker": weights.index,
            "marginal_risk_contribution": marginal,
            "component_risk_contribution": component,
            "risk_contribution_pct": component / component.sum(),
        }
    )


def _write_expanded_reference_artifacts(
    processed,
    simple: pd.DataFrame,
    manifest: dict[str, str],
    risk_free_rate: float,
) -> None:
    fold_dates = [simple.index[:10], simple.index[10:20]]
    weight_map = {
        ("Equal Weight", 0): pd.Series({"AAA": 0.6, "BBB": 0.4}),
        ("Equal Weight", 1): pd.Series({"AAA": 0.6, "BBB": 0.4}),
        ("Active", 0): pd.Series({"AAA": 0.5, "BBB": 0.5}),
        ("Active", 1): pd.Series({"AAA": 0.4, "BBB": 0.6}),
    }
    return_rows = []
    weight_rows = []
    turnover_rows = []
    validation_rows = []
    previous: dict[str, pd.Series] = {}
    for (model, fold), weights in weight_map.items():
        dates = fold_dates[fold]
        gross = simple.loc[dates, weights.index].mul(weights, axis=1).sum(axis=1)
        prior = previous.get(model, pd.Series(dtype=float))
        union = weights.index.union(prior.index)
        turnover = float(
            (
                weights.reindex(union, fill_value=0.0)
                - prior.reindex(union, fill_value=0.0)
            )
            .abs()
            .sum()
        )
        cost = turnover * 10.0 / 10000.0
        net = gross.copy()
        net.iloc[0] -= cost
        return_rows.extend(
            {
                "Date": date,
                "fold": fold,
                "model_name": model,
                "return": value,
            }
            for date, value in net.items()
        )
        weight_rows.extend(
            {
                "fold": fold,
                "model_name": model,
                "ticker": ticker,
                "weight": weight,
            }
            for ticker, weight in weights.items()
        )
        turnover_rows.append(
            {
                "fold": fold,
                "model_name": model,
                "turnover": turnover,
                "transaction_cost_bps": 10.0,
                "transaction_cost_decimal": cost,
            }
        )
        validation_rows.append(
            {
                "fold": fold,
                "model_name": model,
                "test_start": dates.min(),
                "test_end": dates.max(),
                "test_observations": len(dates),
            }
        )
        previous[model] = _drifted_weights(weights, simple.loc[dates, weights.index])
    pd.DataFrame(return_rows).to_csv(
        processed / "global_walk_forward_returns.csv",
        index=False,
    )
    pd.DataFrame(weight_rows).to_csv(
        processed / "global_walk_forward_weights.csv",
        index=False,
    )
    pd.DataFrame(turnover_rows).to_csv(
        processed / "global_walk_forward_turnover.csv",
        index=False,
    )
    pd.DataFrame(validation_rows).to_csv(
        processed / "global_walk_forward_validation.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "fold": fold,
                "selected_count": 2,
                "selected_tickers": "AAA;BBB",
                "test_start": fold_dates[fold].min(),
                "test_end": fold_dates[fold].max(),
                "test_observations": len(fold_dates[fold]),
            }
            for fold in range(2)
        ]
    ).to_csv(
        processed / "global_walk_forward_window_summary.csv",
        index=False,
    )

    model_dates = pd.DatetimeIndex(
        pd.concat([pd.Series(dates) for dates in fold_dates], ignore_index=True)
    )
    date_hash = _date_hash(model_dates)
    random_rows = []
    random_weight_rows = []
    random_distribution = []
    for portfolio_id, weights in enumerate(
        [
            pd.Series({"AAA": 0.7, "BBB": 0.3}),
            pd.Series({"AAA": 0.3, "BBB": 0.7}),
        ]
    ):
        series_parts = []
        previous_weights = pd.Series(dtype=float)
        turnovers = []
        for fold, dates in enumerate(fold_dates):
            gross = simple.loc[dates, weights.index].mul(weights, axis=1).sum(axis=1)
            union = weights.index.union(previous_weights.index)
            turnover = float(
                (
                    weights.reindex(union, fill_value=0.0)
                    - previous_weights.reindex(union, fill_value=0.0)
                )
                .abs()
                .sum()
            )
            post_test_weights = _drifted_weights(
                weights,
                simple.loc[dates, weights.index],
            )
            net = gross.copy()
            net.iloc[0] -= turnover * 10.0 / 10000.0
            turnovers.append(turnover)
            series_parts.append(net)
            random_rows.extend(
                {
                    "Date": date,
                    "fold": fold,
                    "portfolio_id": portfolio_id,
                    "return": value,
                }
                for date, value in net.items()
            )
            weight_union = weights.index.union(previous_weights.index).union(
                post_test_weights.index
            )
            random_weight_rows.extend(
                {
                    "fold": fold,
                    "portfolio_id": portfolio_id,
                    "ticker": ticker,
                    "target_weight": float(weights.get(ticker, 0.0)),
                    "pre_trade_weight": float(previous_weights.get(ticker, 0.0)),
                    "post_test_weight": float(post_test_weights.get(ticker, 0.0)),
                }
                for ticker in weight_union
            )
            previous_weights = post_test_weights
        stitched = pd.concat(series_parts)
        metrics = _risk_metrics(stitched, risk_free_rate=risk_free_rate)
        random_distribution.append(
            {
                "portfolio_id": portfolio_id,
                "benchmark_scope": "walk_forward_oos_net",
                "benchmark_provenance_status": "verified_same_protocol",
                "protocol_hash": "wf-random-unit",
                "folds": 2,
                "avg_turnover": float(np.mean(turnovers)),
                "volatility": metrics.pop("annualized_volatility"),
                **metrics,
                **manifest,
            }
        )
    random_returns = pd.DataFrame(random_rows)
    random_weights = pd.DataFrame(random_weight_rows)
    random_returns.to_csv(
        processed / "global_walk_forward_random_returns.csv",
        index=False,
    )
    pd.DataFrame(random_distribution).to_csv(
        processed / "global_walk_forward_random_distribution.csv",
        index=False,
    )
    random_weights.to_csv(
        processed / "global_walk_forward_random_weights.csv",
        index=False,
    )
    provenance = {
        **manifest,
        "benchmark_scope": "walk_forward_oos_net",
        "provenance_status": "verified_same_protocol",
        "protocol_hash": "wf-random-unit",
        "fold_schedule_hash": "frame-unit",
        "selected_universe_by_fold_hash": "universe-fold-unit",
        "model_oos_dates_hash": date_hash,
        "random_oos_dates_hash": date_hash,
        "oos_dates_match": True,
        "constraint_policy": "long_only_capped_simplex",
        "train_window_days": 252,
        "test_window_days": 10,
        "step_days": 10,
        "max_weight": 0.7,
        "transaction_cost_bps": 10.0,
        "random_portfolio_count": 2,
        "risk_free_rate_annual": risk_free_rate,
        "random_weights_hash": _frame_hash(
            random_weights,
            [
                "fold",
                "portfolio_id",
                "ticker",
                "target_weight",
                "pre_trade_weight",
                "post_test_weight",
            ],
        ),
    }
    (processed / "global_walk_forward_random_benchmark_provenance.json").write_text(
        json.dumps(provenance),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "paired_observations": 20,
                "bootstrap_samples": 100,
                "block_length": 5,
                "confidence_level": 0.95,
                "random_state": 42,
            },
            {
                "model_name": "Active",
                "paired_observations": 20,
                "bootstrap_samples": 100,
                "block_length": 5,
                "confidence_level": 0.95,
                "random_state": 200_051,
            },
        ]
    ).to_csv(processed / "global_walk_forward_uncertainty.csv", index=False)

    complete = np.log1p(simple).dropna(how="any")
    covariance = complete.cov().to_numpy(dtype=float) * 252
    eigenvalues = np.linalg.eigvalsh(0.5 * (covariance + covariance.T))
    pd.DataFrame(
        [
            {
                "estimator": "sample_covariance",
                "average_variance": float(np.diag(covariance).mean()),
                "condition_number": float(np.linalg.cond(covariance)),
                "min_eigenvalue": float(eigenvalues.min()),
                "psd_check": bool(eigenvalues.min() >= -1e-10),
            }
        ]
    ).to_csv(
        processed / "global_covariance_estimator_comparison.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "actual_status": "benchmark_only",
                "weight_sum": 1.0,
                "max_weight": 0.6,
                "configured_max_weight": 0.7,
            }
        ]
    ).to_csv(processed / "global_portfolio_league.csv", index=False)
    pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "random_sharpe_percentile": 0.75,
                "random_sharpe_gate_pass": True,
                "robustness_gate_pass": False,
                "leakage_gate_pass": True,
            }
        ]
    ).to_csv(processed / "global_model_selection_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "fold": 1,
                "check": check,
                "passed": True,
                "audit_status": (
                    "passed_with_current_universe_survivorship_limitation"
                ),
                "evidence_scope": "current_universe_not_point_in_time",
                **manifest,
            }
            for check in [
                "train_end_before_test_start",
                "scores_as_of_not_after_train_end",
                "selected_tickers_available_in_train",
                "scores_recomputed_inside_fold",
            ]
        ]
    ).to_csv(processed / "global_walk_forward_leakage_audit.csv", index=False)
    pd.DataFrame([{"model_name": "Equal Weight", "sharpe_percentile": 0.75}]).to_csv(
        processed / "global_random_portfolio_percentile_report.csv",
        index=False,
    )
    (processed / "global_parameter_sensitivity_summary.json").write_text(
        json.dumps(
            {
                **manifest,
                "robustness_status": "diagnostic_configuration_stability_only",
                "robustness_method": "current_sample_parameter_sensitivity",
                "promotion_eligible": False,
            }
        ),
        encoding="utf-8",
    )


def _date_hash(dates: pd.DatetimeIndex) -> str:
    normalized = pd.Series(pd.to_datetime(dates)).drop_duplicates().sort_values()
    payload = "\n".join(normalized.dt.strftime("%Y-%m-%d")).encode("utf-8")
    return f"dates-{hashlib.sha256(payload).hexdigest()[:24]}"


def _drifted_weights(weights: pd.Series, returns: pd.DataFrame) -> pd.Series:
    terminal = weights * (1.0 + returns).prod(axis=0)
    return terminal / float(terminal.sum())


def _frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    normalized = frame[columns].copy()
    for column in columns:
        if pd.api.types.is_numeric_dtype(normalized[column]):
            normalized[column] = pd.to_numeric(
                normalized[column],
                errors="coerce",
            ).map(
                lambda value: (
                    f"{float(value):.12g}" if np.isfinite(value) else "missing"
                )
            )
        else:
            normalized[column] = normalized[column].fillna("").astype(str)
    normalized = normalized.sort_values(columns, kind="stable")
    payload = normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return f"frame-{hashlib.sha256(payload).hexdigest()[:24]}"


def test_reference_hash_preserves_csv_float_round_trip(tmp_path):
    columns = [
        "fold",
        "portfolio_id",
        "ticker",
        "target_weight",
        "pre_trade_weight",
        "post_test_weight",
    ]
    weights = pd.DataFrame(
        [
            {
                "fold": 0,
                "portfolio_id": 0,
                "ticker": "AAA",
                "target_weight": 0.0022572766357450576,
                "pre_trade_weight": 0.0005180252718075835,
                "post_test_weight": 0.002120485286404839,
            }
        ]
    )
    path = tmp_path / "random_weights.csv"
    weights.to_csv(path, index=False)

    expected = _frame_hash(weights, columns)
    observed = _independent_frame_hash(_read_csv(path), columns)

    assert observed == expected
