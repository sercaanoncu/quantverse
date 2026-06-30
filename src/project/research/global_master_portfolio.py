"""Global master portfolio research allocator."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

from project.optimization.black_litterman import black_litterman_weights
from project.projection.portfolio_projection import (
    correlation_diagnostics,
    estimator_comparison,
    monte_carlo_projection,
    stress_test_portfolio,
)
from project.research.global_stock_selection import (
    build_equal_weight_portfolio,
    build_inverse_volatility_portfolio,
    build_min_cvar_portfolio,
    build_shrinkage_max_sharpe_portfolio,
    build_stock_selection_promotion_gate,
    cluster_assets_by_correlation,
    compare_candidate_to_equal_weight_and_random,
    evaluate_portfolio_return_series,
    score_assets_for_selection,
    select_assets_by_cluster,
    simulate_random_portfolios,
)


def run_master_portfolio_research(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    min_holdings: int = 10,
    max_holdings: int = 40,
    max_weight: float = 0.10,
    n_random_portfolios: int = 10000,
    random_state: int = 42,
    portfolio_constraints: dict[str, float | int | bool] | None = None,
    fx_report: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run the first-pass global master portfolio research layer."""
    constraints = _default_constraints(
        min_holdings=min_holdings,
        max_holdings=max_holdings,
        max_weight=max_weight,
        overrides=portfolio_constraints,
    )
    clean = returns.apply(pd.to_numeric, errors="coerce").dropna(how="all").fillna(0.0)
    metadata = metadata.drop_duplicates("ticker").copy()
    available = [ticker for ticker in metadata["ticker"].astype(str) if ticker in clean]
    if not available:
        raise ValueError("No metadata tickers overlap the returns matrix.")
    clean = clean[available]
    initial_selected = select_assets_by_cluster(
        clean,
        min_holdings=min_holdings,
        max_holdings=max_holdings,
        random_state=random_state,
    )
    selected = _select_policy_assets(
        clean,
        metadata,
        initial_selected,
        constraints=constraints,
        random_state=random_state,
    )
    selected_returns = clean[selected]
    selected_metadata = metadata.loc[
        metadata["ticker"].astype(str).isin(selected)
    ].copy()
    clusters = _constraint_clusters(selected_returns, constraints)
    candidates = _candidate_weights(selected_returns, selected_metadata, max_weight)
    model_comparison = _compare_models(selected_returns, candidates)
    constraint_audit = _constraint_audit(
        candidates,
        selected_metadata,
        clusters,
        constraints,
    )
    randoms = simulate_random_portfolios(
        selected_returns,
        n_portfolios=n_random_portfolios,
        max_weight=max_weight,
        random_state=random_state,
    )
    best_row = _best_promotable_candidate(model_comparison)
    best_model = str(best_row["Model"])
    final_model = best_model
    final_weights = candidates.get(best_model, candidates["Equal Weight"])
    comparison, gate = _comparison_and_gate(
        selected_returns,
        final_weights,
        candidates["Equal Weight"],
        randoms,
    )
    final_constraint = constraint_audit.loc[
        constraint_audit["Model"].eq(final_model)
    ].iloc[0]
    fx_status = _fx_status(selected_metadata, fx_report)
    gate = _apply_non_performance_blocks(gate, final_constraint, fx_status)
    if not gate["Promoted"]:
        policy_row = constraint_audit.loc[
            constraint_audit["Model"].eq("Policy Constrained")
        ]
        if not policy_row.empty and bool(policy_row["All_Constraints_Pass"].iloc[0]):
            final_model = "Policy Constrained"
            final_weights = candidates["Policy Constrained"]
        else:
            final_model = "Equal Weight"
            final_weights = candidates["Equal Weight"]
        comparison, gate = _comparison_and_gate(
            selected_returns,
            final_weights,
            candidates["Equal Weight"],
            randoms,
        )
        final_constraint = constraint_audit.loc[
            constraint_audit["Model"].eq(final_model)
        ].iloc[0]
        gate = _apply_non_performance_blocks(gate, final_constraint, fx_status)
        gate["Reason"] = _append_reason(
            str(gate["Reason"]),
            f"Final model set to {final_model}; best metric candidate "
            f"{best_model} was not used because its promotion gate failed.",
        )
    weights_long = _weights_long(candidates)
    risk_report = _risk_report(selected_returns, candidates)
    projection = monte_carlo_projection(
        selected_returns,
        final_weights,
        n_simulations=min(1000, max(100, n_random_portfolios)),
        random_state=random_state,
    )
    stress = stress_test_portfolio(final_weights, selected_metadata)
    diagnostics = correlation_diagnostics(selected_returns)
    final_exposures = _exposure_tables(
        final_model,
        final_weights,
        selected_metadata,
        clusters,
    )
    decision = {
        "selected_holdings": int(len(selected)),
        "final_model": final_model,
        "promotion_decision": gate["Promotion_Decision"],
        "reason": gate["Reason"],
        "selected_assets": selected,
        "fx_normalization_status": fx_status,
        "promotion_universe": "current global proxy research candidate",
        "constraints_pass": bool(
            constraint_audit.loc[
                constraint_audit["Model"].eq(final_model),
                "All_Constraints_Pass",
            ].iloc[0]
        ),
    }
    return {
        "selected_assets": selected_metadata,
        "candidate_weights": weights_long,
        "asset_class_weights": final_exposures["asset_class_weights"],
        "region_weights": final_exposures["region_weights"],
        "cluster_weights": final_exposures["cluster_weights"],
        "model_comparison": model_comparison,
        "equal_weight_comparison": pd.DataFrame([comparison]),
        "random_portfolio_benchmark": randoms,
        "promotion_gate": pd.DataFrame([{**comparison, **gate}]),
        "constraint_audit": constraint_audit,
        "risk_report": risk_report,
        "projection_summary": projection,
        "stress_tests": stress,
        "correlation_matrix": diagnostics["correlation_matrix"],
        "high_correlation_pairs": diagnostics["high_correlation_pairs"],
        "cluster_diagnostics": diagnostics["cluster_diagnostics"],
        "estimator_comparison": estimator_comparison(selected_returns),
        "decision_summary": decision,
    }


def write_master_portfolio_outputs(
    result: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: str | Path,
) -> None:
    """Write master portfolio outputs to CSV/JSON."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    file_map = {
        "selected_assets": "global_master_selected_assets.csv",
        "candidate_weights": "global_master_candidate_weights.csv",
        "model_comparison": "global_master_model_comparison.csv",
        "equal_weight_comparison": "global_master_equal_weight_comparison.csv",
        "random_portfolio_benchmark": "global_master_random_portfolio_benchmark.csv",
        "promotion_gate": "global_master_promotion_gate.csv",
        "constraint_audit": "global_master_constraint_audit.csv",
        "asset_class_weights": "global_master_asset_class_weights.csv",
        "region_weights": "global_master_region_weights.csv",
        "cluster_weights": "global_master_cluster_weights.csv",
        "risk_report": "global_master_risk_report.csv",
        "projection_summary": "global_master_projection_summary.csv",
        "stress_tests": "global_stress_test_results.csv",
        "correlation_matrix": "global_correlation_matrix.csv",
        "high_correlation_pairs": "global_high_correlation_pairs.csv",
        "cluster_diagnostics": "global_cluster_diagnostics.csv",
        "estimator_comparison": "global_estimator_comparison.csv",
    }
    for key, filename in file_map.items():
        value = result[key]
        if isinstance(value, pd.DataFrame):
            value.to_csv(path / filename, index=key != "correlation_matrix")
    (path / "global_monte_carlo_projection.csv").write_text(
        result["projection_summary"].to_csv(index=False),
        encoding="utf-8",
    )
    (path / "global_master_decision_summary.json").write_text(
        json.dumps(result["decision_summary"], indent=2),
        encoding="utf-8",
    )


def _candidate_weights(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    max_weight: float,
) -> dict[str, pd.Series]:
    candidates = {
        "Equal Weight": build_equal_weight_portfolio(returns, returns.columns),
        "Inverse Volatility": build_inverse_volatility_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "Min Variance": _min_variance_weights(returns, max_weight=max_weight),
        "Max Sharpe": build_shrinkage_max_sharpe_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "Min CVaR": build_min_cvar_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "Cluster Balanced": _cluster_balanced_weights(returns, max_weight=max_weight),
    }
    candidates["Policy Constrained"] = _policy_constrained_weights(
        returns,
        metadata,
        max_weight=max_weight,
    )
    caps = (
        pd.to_numeric(metadata.set_index("ticker")["market_cap_usd"], errors="coerce")
        if "market_cap_usd" in metadata
        else pd.Series(dtype=float)
    )
    caps = caps.reindex(returns.columns)
    if caps.notna().all() and (caps > 0).all():
        candidates["Black-Litterman"] = black_litterman_weights(
            returns.cov() * 252,
            caps,
            max_weight=max_weight,
        )
    return candidates


def _compare_models(
    returns: pd.DataFrame,
    candidates: dict[str, pd.Series],
) -> pd.DataFrame:
    rows = []
    for name, weights in candidates.items():
        metrics = evaluate_portfolio_return_series(returns @ weights)
        rows.append({"Model": name, "Status": "computed", **metrics})
    if "Black-Litterman" not in candidates:
        rows.append(
            {
                "Model": "Black-Litterman",
                "Status": "missing_market_caps",
                "CAGR": np.nan,
                "Annual_Return": np.nan,
                "Volatility": np.nan,
                "Sharpe": np.nan,
                "Sortino": np.nan,
                "Max_Drawdown": np.nan,
                "CVaR_95": np.nan,
                "Total_Return": np.nan,
            }
        )
    for name in [
        "HRP",
        "Risk Parity",
        "Forecast-enhanced Max Sharpe",
        "Forecast-enhanced Min CVaR",
    ]:
        rows.append({"Model": name, "Status": "not_available_in_this_run"})
    return pd.DataFrame(rows)


def _comparison_and_gate(
    returns: pd.DataFrame,
    candidate_weights: pd.Series,
    equal_weight_weights: pd.Series,
    randoms: pd.DataFrame,
) -> tuple[dict[str, float | bool], dict[str, object]]:
    candidate_returns = returns @ candidate_weights
    ew_returns = returns @ equal_weight_weights
    comparison = compare_candidate_to_equal_weight_and_random(
        evaluate_portfolio_return_series(candidate_returns),
        evaluate_portfolio_return_series(ew_returns),
        randoms,
    )
    comparison.update(
        {
            "Turnover": 1.0,
            "Transaction_Cost_Bps": 10.0,
            "Transaction_Cost_Drag": 0.001,
        }
    )
    return comparison, build_stock_selection_promotion_gate(comparison)


def _apply_non_performance_blocks(
    gate: dict[str, object],
    constraint_row: pd.Series,
    fx_status: str,
) -> dict[str, object]:
    blocked = dict(gate)
    failed_constraints = str(constraint_row.get("Failed_Constraints", "None"))
    if not bool(constraint_row["All_Constraints_Pass"]):
        blocked["Promoted"] = False
        blocked["Promotion_Decision"] = "not promoted"
        blocked["Reason"] = _append_reason(
            str(blocked["Reason"]),
            "Constraint audit failed: " + failed_constraints + ".",
        )
    if fx_status not in {"usd_native", "fx_normalized"}:
        blocked["Promoted"] = False
        blocked["Promotion_Decision"] = "not promoted"
        blocked["Reason"] = _append_reason(
            str(blocked["Reason"]),
            "FX normalization is insufficient for a promoted global USD portfolio.",
        )
    return blocked


def _append_reason(reason: str, addition: str) -> str:
    normalized = reason.strip()
    if normalized and normalized[-1] not in ".;:":
        normalized += "."
    return (normalized + " " + addition).strip()


def _best_promotable_candidate(model_comparison: pd.DataFrame) -> pd.Series:
    computed = model_comparison.loc[model_comparison["Status"].eq("computed")].copy()
    computed = computed.sort_values(["Sharpe", "CAGR"], ascending=False)
    return computed.iloc[0]


def _weights_long(candidates: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for model, weights in candidates.items():
        rows.extend(
            {"Model": model, "Ticker": ticker, "Weight": float(weight)}
            for ticker, weight in weights.items()
        )
    return pd.DataFrame(rows)


def _risk_report(
    returns: pd.DataFrame,
    candidates: dict[str, pd.Series],
) -> pd.DataFrame:
    rows = []
    for model, weights in candidates.items():
        portfolio_returns = returns @ weights
        metrics = evaluate_portfolio_return_series(portfolio_returns)
        rows.append(
            {
                "Model": model,
                "Volatility": metrics["Volatility"],
                "Max_Drawdown": metrics["Max_Drawdown"],
                "CVaR_95": metrics["CVaR_95"],
                "Weight_Concentration_HHI": float((weights**2).sum()),
            }
        )
    return pd.DataFrame(rows)


def _min_variance_weights(returns: pd.DataFrame, max_weight: float) -> pd.Series:
    assets = list(returns.columns)
    cov = returns.cov().to_numpy(dtype=float)
    x0 = np.repeat(1.0 / len(assets), len(assets))

    def objective(weights: np.ndarray) -> float:
        return float(weights @ cov @ weights)

    result = minimize(
        objective,
        x0=x0,
        bounds=[(0.0, float(max_weight)) for _ in assets],
        constraints={"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
        method="SLSQP",
    )
    if not result.success:
        return build_inverse_volatility_portfolio(returns, assets, max_weight)
    weights = pd.Series(result.x, index=assets, name="Weight")
    return weights / weights.sum()


def _cluster_balanced_weights(returns: pd.DataFrame, max_weight: float) -> pd.Series:
    clusters = cluster_assets_by_correlation(returns)
    weights = pd.Series(0.0, index=returns.columns, dtype=float)
    for _, tickers in clusters.groupby(clusters).groups.items():
        cluster_weight = 1.0 / clusters.nunique()
        per_asset = cluster_weight / len(tickers)
        weights.loc[list(tickers)] = min(per_asset, max_weight)
    weights = weights / weights.sum()
    weights.name = "Weight"
    return weights


def _policy_constrained_weights(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    max_weight: float,
) -> pd.Series:
    assets = list(returns.columns)
    clusters = _constraint_clusters(
        returns,
        _default_constraints(
            min_holdings=len(returns.columns),
            max_holdings=len(returns.columns),
            max_weight=max_weight,
            overrides=None,
        ),
    )
    meta = metadata.set_index("ticker").reindex(assets)
    constraints = _default_constraints(
        min_holdings=len(assets),
        max_holdings=len(assets),
        max_weight=max_weight,
        overrides=None,
    )
    c = np.zeros(len(assets))
    a_ub = []
    b_ub = []
    equity_mask = meta["sleeve"].astype(str).str.startswith("global_equity")
    a_ub.append(-equity_mask.reindex(assets).fillna(False).to_numpy(dtype=float))
    b_ub.append(-float(constraints["min_global_equity_weight"]))
    for mask, limit in [
        (
            meta["sleeve"].astype(str).eq("defensive_bonds_cash"),
            constraints["max_defensive_weight"],
        ),
        (
            meta["sleeve"].astype(str).isin(["crypto", "crypto_top100"]),
            constraints["max_crypto_weight"],
        ),
        (
            meta["sleeve"].astype(str).eq("commodity_real_assets"),
            constraints["max_commodity_weight"],
        ),
    ]:
        a_ub.append(mask.reindex(assets).fillna(False).to_numpy(dtype=float))
        b_ub.append(float(limit))
    for region in sorted(set(meta["region"].fillna("unknown").astype(str))):
        mask = meta["region"].fillna("unknown").astype(str).eq(region)
        a_ub.append(mask.reindex(assets).fillna(False).to_numpy(dtype=float))
        b_ub.append(float(constraints["max_region_weight"]))
    for cluster in sorted(set(clusters.astype(int))):
        mask = clusters.reindex(assets).astype(int).eq(cluster)
        a_ub.append(mask.reindex(assets).fillna(False).to_numpy(dtype=float))
        b_ub.append(float(constraints["max_cluster_weight"]))
    result = linprog(
        c=c,
        A_ub=np.vstack(a_ub),
        b_ub=np.array(b_ub, dtype=float),
        A_eq=np.ones((1, len(assets))),
        b_eq=np.array([1.0]),
        bounds=[(min(1e-4, 0.5 / len(assets)), float(max_weight)) for _ in assets],
        method="highs",
    )
    if not result.success:
        return pd.Series(1.0 / len(assets), index=assets, name="Weight")
    weights = pd.Series(result.x, index=assets, name="Weight")
    return weights / weights.sum()


def _default_constraints(
    min_holdings: int,
    max_holdings: int,
    max_weight: float,
    overrides: dict[str, float | int | bool] | None,
) -> dict[str, float | int | bool]:
    constraints: dict[str, float | int | bool] = {
        "long_only": True,
        "weight_sum": 1.0,
        "max_single_asset_weight": float(max_weight),
        "min_holdings": int(min_holdings),
        "max_holdings": int(max_holdings),
        "min_global_equity_weight": 0.50,
        "max_defensive_weight": 0.35,
        "max_crypto_weight": 0.10,
        "max_commodity_weight": 0.20,
        "max_region_weight": 0.35,
        "max_cluster_weight": 0.25,
    }
    if overrides:
        constraints.update(overrides)
    return constraints


def _select_policy_assets(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    initial_selected: list[str],
    constraints: dict[str, float | int | bool],
    random_state: int,
) -> list[str]:
    del random_state
    max_holdings = min(int(constraints["max_holdings"]), returns.shape[1])
    min_holdings = min(int(constraints["min_holdings"]), max_holdings)
    target = max(min_holdings, min(max_holdings, len(initial_selected) or max_holdings))
    meta = metadata.set_index("ticker").reindex(returns.columns)
    scores = score_assets_for_selection(returns).set_index("Ticker")
    ranked = scores.index.tolist()
    selected: list[str] = []
    clusters = cluster_assets_by_correlation(returns)

    def add_from(candidates: list[str], target_count: int) -> None:
        for ticker in candidates:
            if len(selected) >= target or len(selected) >= target_count:
                break
            if ticker in selected:
                continue
            if _can_add_with_count_caps(
                ticker, selected, meta, clusters, constraints, target
            ):
                selected.append(ticker)

    equity = [
        ticker
        for ticker in ranked
        if str(meta.loc[ticker, "sleeve"]).startswith("global_equity")
    ]
    min_equity = int(np.ceil(float(constraints["min_global_equity_weight"]) * target))
    add_from(equity, min_equity)
    add_from(initial_selected + ranked, target)
    if len(selected) < min_holdings:
        for ticker in ranked:
            if ticker not in selected:
                selected.append(ticker)
            if len(selected) >= min_holdings:
                break
    return selected[:target]


def _can_add_with_count_caps(
    ticker: str,
    selected: list[str],
    meta: pd.DataFrame,
    clusters: pd.Series,
    constraints: dict[str, float | int | bool],
    target: int,
) -> bool:
    proposed = selected + [ticker]
    sleeve = str(meta.loc[ticker, "sleeve"])
    region = str(meta.loc[ticker, "region"])
    cluster = int(clusters.loc[ticker])
    max_defensive = int(np.floor(float(constraints["max_defensive_weight"]) * target))
    max_crypto = int(np.floor(float(constraints["max_crypto_weight"]) * target))
    max_commodity = int(np.floor(float(constraints["max_commodity_weight"]) * target))
    max_region = max(1, int(np.floor(float(constraints["max_region_weight"]) * target)))
    max_cluster = max(
        1, int(np.floor(float(constraints["max_cluster_weight"]) * target))
    )
    if (
        sleeve == "defensive_bonds_cash"
        and _count_sleeve(proposed, meta, sleeve) > max_defensive
    ):
        return False
    if (
        sleeve in {"crypto", "crypto_top100"}
        and _count_sleeve(proposed, meta, sleeve) > max_crypto
    ):
        return False
    if (
        sleeve == "commodity_real_assets"
        and _count_sleeve(proposed, meta, sleeve) > max_commodity
    ):
        return False
    if sum(str(meta.loc[item, "region"]) == region for item in proposed) > max_region:
        return False
    if sum(int(clusters.loc[item]) == cluster for item in proposed) > max_cluster:
        return False
    return True


def _count_sleeve(tickers: list[str], meta: pd.DataFrame, sleeve: str) -> int:
    return sum(str(meta.loc[ticker, "sleeve"]) == sleeve for ticker in tickers)


def _constraint_audit(
    candidates: dict[str, pd.Series],
    metadata: pd.DataFrame,
    clusters: pd.Series,
    constraints: dict[str, float | int | bool],
) -> pd.DataFrame:
    meta = metadata.set_index("ticker")
    rows = []
    for model, weights in candidates.items():
        weights = weights.astype(float)
        asset_class = _group_weights(weights, meta, "sleeve")
        region = _group_weights(weights, meta, "region")
        cluster_weights = weights.groupby(clusters.reindex(weights.index)).sum()
        checks = {
            "weight_sum_ok": abs(
                float(weights.sum()) - float(constraints["weight_sum"])
            )
            <= 1e-6,
            "long_only_ok": bool((weights >= -1e-12).all()),
            "max_weight_ok": bool(
                weights.max() <= float(constraints["max_single_asset_weight"]) + 1e-8
            ),
            "holdings_count_ok": int(constraints["min_holdings"])
            <= int((weights > 1e-10).sum())
            <= int(constraints["max_holdings"]),
            "min_global_equity_ok": float(
                asset_class[
                    asset_class.index.astype(str).str.startswith("global_equity")
                ].sum()
            )
            >= float(constraints["min_global_equity_weight"]) - 1e-8,
            "max_defensive_ok": float(asset_class.get("defensive_bonds_cash", 0.0))
            <= float(constraints["max_defensive_weight"]) + 1e-8,
            "max_crypto_ok": float(
                asset_class.reindex(["crypto", "crypto_top100"]).fillna(0.0).sum()
            )
            <= float(constraints["max_crypto_weight"]) + 1e-8,
            "max_commodity_ok": float(asset_class.get("commodity_real_assets", 0.0))
            <= float(constraints["max_commodity_weight"]) + 1e-8,
            "max_region_ok": bool(
                region.max() <= float(constraints["max_region_weight"]) + 1e-8
            ),
            "max_cluster_ok": bool(
                cluster_weights.max() <= float(constraints["max_cluster_weight"]) + 1e-8
            ),
        }
        failed = [name for name, ok in checks.items() if not ok]
        rows.append(
            {
                "Model": model,
                "Weight_Sum": float(weights.sum()),
                "Holdings_Count": int((weights > 1e-10).sum()),
                "Max_Weight": float(weights.max()),
                "Global_Equity_Weight": float(
                    asset_class[
                        asset_class.index.astype(str).str.startswith("global_equity")
                    ].sum()
                ),
                "Defensive_Weight": float(asset_class.get("defensive_bonds_cash", 0.0)),
                "Crypto_Weight": float(
                    asset_class.reindex(["crypto", "crypto_top100"]).fillna(0.0).sum()
                ),
                "Commodity_Weight": float(
                    asset_class.get("commodity_real_assets", 0.0)
                ),
                "Max_Region_Weight": float(region.max()),
                "Max_Cluster_Weight": float(cluster_weights.max()),
                "All_Constraints_Pass": not failed,
                "Failed_Constraints": "; ".join(failed) if failed else "None",
                **checks,
            }
        )
    return pd.DataFrame(rows)


def _group_weights(weights: pd.Series, meta: pd.DataFrame, column: str) -> pd.Series:
    labels = meta.reindex(weights.index)[column].fillna("unknown").astype(str)
    return weights.groupby(labels).sum()


def _exposure_tables(
    model: str,
    weights: pd.Series,
    metadata: pd.DataFrame,
    clusters: pd.Series,
) -> dict[str, pd.DataFrame]:
    meta = metadata.set_index("ticker")
    asset_class = _group_weights(weights, meta, "sleeve")
    region = _group_weights(weights, meta, "region")
    cluster = weights.groupby(clusters.reindex(weights.index)).sum()
    return {
        "asset_class_weights": _exposure_frame(asset_class, "Asset_Class", model),
        "region_weights": _exposure_frame(region, "Region", model),
        "cluster_weights": _exposure_frame(cluster, "Cluster", model),
    }


def _exposure_frame(series: pd.Series, label: str, model: str) -> pd.DataFrame:
    frame = series.rename("Weight").reset_index()
    frame = frame.rename(columns={frame.columns[0]: label})
    frame.insert(0, "Model", model)
    return frame


def _fx_status(metadata: pd.DataFrame, fx_report: pd.DataFrame | None = None) -> str:
    currencies = set(metadata["currency"].fillna("").astype(str).str.upper())
    non_usd = {currency for currency in currencies if currency and currency != "USD"}
    if not non_usd:
        return "usd_native"
    if fx_report is None or fx_report.empty:
        return "local_currency_mixed_not_promotable"
    required = {"ticker", "fx_normalization_status"}
    if not required.issubset(fx_report.columns):
        return "local_currency_mixed_not_promotable"
    status = (
        fx_report.drop_duplicates("ticker", keep="last")
        .set_index("ticker")["fx_normalization_status"]
        .astype(str)
    )
    selected_non_usd = metadata.loc[
        metadata["currency"].fillna("").astype(str).str.upper().ne("USD"),
        "ticker",
    ].astype(str)
    if selected_non_usd.empty:
        return "usd_native"
    selected_status = status.reindex(selected_non_usd)
    return (
        "fx_normalized"
        if selected_status.eq("fx_normalized").all()
        else "local_currency_mixed_not_promotable"
    )


def _constraint_clusters(
    returns: pd.DataFrame,
    constraints: dict[str, float | int | bool],
) -> pd.Series:
    min_clusters = int(np.ceil(1.0 / float(constraints["max_cluster_weight"])))
    max_clusters = min(len(returns.columns), max(min_clusters * 4, min_clusters, 25))
    return cluster_assets_by_correlation(returns, max_clusters=max_clusters)
