"""Global master portfolio research allocator."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize
from sklearn.covariance import LedoitWolf

from project.constants import TRADING_DAYS_PER_YEAR
from project.data_pipeline.market_cap_rank_evidence import (
    EXACT_TOP100_UNSUPPORTED_TEXT,
    black_litterman_priors_available,
    validate_market_cap_rank_evidence,
)
from project.data_pipeline.security_identity import (
    attach_run_metadata,
    resolve_security_master_rows,
)
from project.data_pipeline.security_universe import filter_included_investable_assets
from project.optimization.black_litterman import black_litterman_weights
from project.projection.portfolio_projection import (
    correlation_diagnostics,
    estimator_comparison,
    monte_carlo_projection,
    stress_test_portfolio,
)
from project.research.global_stock_selection import (
    apply_max_weight_cap,
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
    promotion_gate_config: Mapping[str, float | int] | None = None,
    fx_report: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run the first-pass global master portfolio research layer."""
    constraints = _default_constraints(
        min_holdings=min_holdings,
        max_holdings=max_holdings,
        max_weight=max_weight,
        overrides=portfolio_constraints,
    )
    clean = (
        returns.apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna(how="all")
        .dropna(axis=1, how="all")
    )
    metadata = filter_included_investable_assets(resolve_security_master_rows(metadata))
    available = [ticker for ticker in metadata["ticker"].astype(str) if ticker in clean]
    if not available:
        raise ValueError(
            "No eligible investable metadata tickers overlap the returns matrix."
        )
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
    selected_returns = clean[selected].dropna(how="any")
    if len(selected_returns) < 2:
        raise ValueError(
            "At least two common return observations are required; missing returns "
            "are not imputed as zero."
        )
    selected_metadata = (
        metadata.set_index("ticker", drop=False)
        .reindex(selected)
        .reset_index(drop=True)
    )
    _selected_evidence_report, classification, _, bl_prerequisites = (
        validate_market_cap_rank_evidence(selected_metadata)
    )
    clusters = _constraint_clusters(selected_returns, constraints)
    candidates, candidate_failures = _candidate_weights(
        selected_returns, selected_metadata, max_weight
    )
    model_comparison = _compare_models(selected_returns, candidates, candidate_failures)
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
        promotion_gate_config=promotion_gate_config,
    )
    final_constraint = constraint_audit.loc[
        constraint_audit["Model"].eq(final_model)
    ].iloc[0]
    fx_status = _fx_status(selected_metadata, fx_report)
    gate = _apply_non_performance_blocks(
        gate,
        final_constraint,
        fx_status,
        institutional_point_in_time_available=False,
    )
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
            promotion_gate_config=promotion_gate_config,
        )
        final_constraint = constraint_audit.loc[
            constraint_audit["Model"].eq(final_model)
        ].iloc[0]
        gate = _apply_non_performance_blocks(
            gate,
            final_constraint,
            fx_status,
            institutional_point_in_time_available=False,
        )
        gate["Reason"] = _append_reason(
            str(gate["Reason"]),
            "Legacy global master gate fallback remains not promoted; the best "
            "metric candidate failed the promotion gate. This legacy gate does "
            "not override the separate v2 public-data research final model.",
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
        "promotion_universe": _promotion_universe_label(classification),
        "exact_top100_claim_supported": bool(
            not classification.empty
            and classification["classification"]
            .astype(str)
            .eq("exact_market_cap_rank_supported")
            .all()
        ),
        "unsupported_exact_top100_sleeves": (
            classification.loc[
                ~classification["classification"]
                .astype(str)
                .eq("exact_market_cap_rank_supported"),
                "sleeve",
            ]
            .astype(str)
            .tolist()
            if not classification.empty
            else []
        ),
        "exact_top100_required_text": (
            ""
            if classification.empty
            or classification["classification"]
            .astype(str)
            .eq("exact_market_cap_rank_supported")
            .all()
            else EXACT_TOP100_UNSUPPORTED_TEXT
        ),
        "black_litterman_prerequisite_status": (
            "selected_subset_priors_available_diagnostic_only"
            if not bl_prerequisites.empty
            and bl_prerequisites["black_litterman_prior_valid"].astype(bool).all()
            else "blocked_by_data"
        ),
        "constraints_pass": bool(
            constraint_audit.loc[
                constraint_audit["Model"].eq(final_model),
                "All_Constraints_Pass",
            ].iloc[0]
        ),
        "point_in_time_membership_status": "unavailable_current_universe_only",
        "institutional_promotion_eligible": False,
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
        "exact_proxy_classification": classification,
        "black_litterman_prerequisites": bl_prerequisites,
        "decision_summary": decision,
    }


def write_master_portfolio_outputs(
    result: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: str | Path,
) -> None:
    """Write master portfolio outputs to CSV/JSON."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    decision_summary = result.get("decision_summary")
    if not isinstance(decision_summary, dict):
        raise TypeError("decision_summary must be a dictionary.")
    run_metadata = {
        key: value
        for key, value in decision_summary.items()
        if key
        in {
            "run_id",
            "execution_id",
            "data_as_of_date",
            "generated_at",
            "universe_snapshot_id",
            "data_snapshot_id",
            "config_hash",
            "input_fingerprint",
        }
    }
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
        "stress_tests": "global_master_stress_test_results.csv",
        "correlation_matrix": "global_correlation_matrix.csv",
        "high_correlation_pairs": "global_high_correlation_pairs.csv",
        "cluster_diagnostics": "global_cluster_diagnostics.csv",
        "estimator_comparison": "global_estimator_comparison.csv",
        "exact_proxy_classification": "global_master_exact_proxy_classification.csv",
        "black_litterman_prerequisites": "global_master_black_litterman_prerequisites.csv",
    }
    for key, filename in file_map.items():
        value = result[key]
        if isinstance(value, pd.DataFrame):
            bound = attach_run_metadata(value, run_metadata) if run_metadata else value
            bound.to_csv(path / filename, index=key != "correlation_matrix")
    projection_summary = result.get("projection_summary")
    if not isinstance(projection_summary, pd.DataFrame):
        raise TypeError("projection_summary must be a DataFrame.")
    bound_projection = (
        attach_run_metadata(projection_summary, run_metadata)
        if run_metadata
        else projection_summary
    )
    (path / "global_master_monte_carlo_projection.csv").write_text(
        bound_projection.to_csv(index=False),
        encoding="utf-8",
    )
    (path / "global_master_decision_summary.json").write_text(
        json.dumps(decision_summary, indent=2),
        encoding="utf-8",
    )


def _promotion_universe_label(classification: pd.DataFrame) -> str:
    if classification.empty:
        return "current global proxy research candidate"
    if (
        classification["classification"]
        .astype(str)
        .eq("exact_market_cap_rank_supported")
        .all()
    ):
        return "exact market-cap-ranked current universe"
    return "current global proxy research candidate"


def _candidate_weights(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    max_weight: float,
) -> tuple[dict[str, pd.Series], dict[str, tuple[str, str]]]:
    candidates: dict[str, pd.Series] = {}
    failures: dict[str, tuple[str, str]] = {}

    def add_candidate(name: str, builder, failure_status: str) -> None:
        try:
            built = builder()
            candidates[name] = _checked_candidate_weights(
                built,
                returns.columns,
                max_weight=max_weight,
            )
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
            failures[name] = (failure_status, str(exc))

    add_candidate(
        "Equal Weight",
        lambda: build_equal_weight_portfolio(returns, returns.columns),
        "construction_failed",
    )
    add_candidate(
        "Inverse Volatility",
        lambda: build_inverse_volatility_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "construction_failed",
    )
    add_candidate(
        "Min Variance",
        lambda: _min_variance_weights(returns, max_weight=max_weight),
        "optimizer_failed",
    )
    add_candidate(
        "Max Sharpe",
        lambda: build_shrinkage_max_sharpe_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "optimizer_failed",
    )
    add_candidate(
        "Min CVaR",
        lambda: build_min_cvar_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "optimizer_failed",
    )
    add_candidate(
        "Cluster Balanced",
        lambda: _cluster_balanced_weights(returns, max_weight=max_weight),
        "construction_failed",
    )
    add_candidate(
        "Policy Constrained",
        lambda: _policy_constrained_weights(
            returns,
            metadata,
            max_weight=max_weight,
        ),
        "infeasible_constraints",
    )
    caps = (
        pd.to_numeric(metadata.set_index("ticker")["market_cap_usd"], errors="coerce")
        if "market_cap_usd" in metadata
        else pd.Series(dtype=float)
    )
    caps = caps.reindex(returns.columns)
    if (
        caps.notna().all()
        and (caps > 0).all()
        and black_litterman_priors_available(
            metadata,
            returns.columns,
        )
    ):
        add_candidate(
            "Black-Litterman",
            lambda: black_litterman_weights(
                _ledoit_wolf_covariance(returns),
                caps,
                max_weight=max_weight,
            ),
            "optimizer_failed",
        )
    else:
        failures["Black-Litterman"] = (
            "blocked_missing_market_cap_priors",
            "Valid market-cap priors are not available for every selected asset.",
        )
    if "Equal Weight" not in candidates:
        raise ValueError("Equal Weight benchmark construction failed.")
    return candidates, failures


def _compare_models(
    returns: pd.DataFrame,
    candidates: dict[str, pd.Series],
    failures: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    rows = []
    for name, weights in candidates.items():
        metrics = evaluate_portfolio_return_series(returns @ weights)
        status = "computed_diagnostic_only" if name == "Black-Litterman" else "computed"
        notes = (
            "Prior-only Black-Litterman diagnostic on the selected current subset; "
            "not promotion-eligible evidence."
            if name == "Black-Litterman"
            else ""
        )
        rows.append({"Model": name, "Status": status, "Notes": notes, **metrics})
    rows.extend(
        _uncomputed_model_row(name, status, reason)
        for name, (status, reason) in failures.items()
    )
    for name in [
        "HRP",
        "Risk Parity",
        "Forecast-enhanced Max Sharpe",
        "Forecast-enhanced Min CVaR",
    ]:
        rows.append({"Model": name, "Status": "not_available_in_this_run"})
    return pd.DataFrame(rows)


def _uncomputed_model_row(name: str, status: str, reason: str) -> dict[str, object]:
    return {
        "Model": name,
        "Status": status,
        "Notes": reason,
        "CAGR": np.nan,
        "Annual_Return": np.nan,
        "Volatility": np.nan,
        "Sharpe": np.nan,
        "Sortino": np.nan,
        "Max_Drawdown": np.nan,
        "CVaR_95": np.nan,
        "Total_Return": np.nan,
    }


def _checked_candidate_weights(
    weights: pd.Series,
    assets: Iterable[str],
    *,
    max_weight: float,
) -> pd.Series:
    expected = [str(asset) for asset in assets]
    candidate = pd.Series(weights, dtype=float)
    if candidate.index.duplicated().any():
        raise ValueError("Candidate weights contain duplicate assets.")
    candidate = candidate.reindex(expected)
    if candidate.isna().any() or not np.isfinite(candidate.to_numpy()).all():
        raise ValueError("Candidate weights contain missing or non-finite values.")
    if (candidate < -1e-10).any():
        raise ValueError("Candidate weights violate the long-only constraint.")
    total = float(candidate.sum())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Candidate weights sum to {total:.12f}, not 1.")
    candidate = candidate / total
    if float(candidate.max()) > float(max_weight) + 1e-8:
        raise ValueError("Candidate weights violate the maximum-weight constraint.")
    candidate.name = "Weight"
    return candidate


def _comparison_and_gate(
    returns: pd.DataFrame,
    candidate_weights: pd.Series,
    equal_weight_weights: pd.Series,
    randoms: pd.DataFrame,
    *,
    promotion_gate_config: Mapping[str, float | int] | None = None,
) -> tuple[dict[str, float | bool], dict[str, object]]:
    config = dict(promotion_gate_config or {})
    turnover = _finite_gate_value(
        config.get("estimated_initial_turnover", 1.0),
        name="estimated_initial_turnover",
        minimum=0.0,
    )
    transaction_cost_bps = _finite_gate_value(
        config.get("transaction_cost_bps", 10.0),
        name="transaction_cost_bps",
        minimum=0.0,
    )
    random_percentile_threshold = _finite_gate_value(
        config.get("random_percentile_threshold", 0.90),
        name="random_percentile_threshold",
        minimum=0.0,
        maximum=1.0,
    )
    volatility_relative_limit = _finite_gate_value(
        config.get("volatility_relative_limit", 1.25),
        name="volatility_relative_limit",
        minimum=0.0,
        minimum_inclusive=False,
    )
    max_drawdown_penalty = _finite_gate_value(
        config.get("max_drawdown_penalty", 0.05),
        name="max_drawdown_penalty",
        minimum=0.0,
    )
    cvar_penalty = _finite_gate_value(
        config.get("cvar_penalty", 0.05),
        name="cvar_penalty",
        minimum=0.0,
    )
    max_turnover = _finite_gate_value(
        config.get("max_turnover", 1.0),
        name="max_turnover",
        minimum=0.0,
    )
    max_transaction_cost_drag = _finite_gate_value(
        config.get("max_transaction_cost_drag", 0.0025),
        name="max_transaction_cost_drag",
        minimum=0.0,
    )
    candidate_returns = returns @ candidate_weights
    ew_returns = returns @ equal_weight_weights
    comparison = compare_candidate_to_equal_weight_and_random(
        evaluate_portfolio_return_series(candidate_returns),
        evaluate_portfolio_return_series(ew_returns),
        randoms,
    )
    comparison.update(
        {
            "Turnover": turnover,
            "Transaction_Cost_Bps": transaction_cost_bps,
            "Transaction_Cost_Drag": turnover * transaction_cost_bps / 10000.0,
        }
    )
    return comparison, build_stock_selection_promotion_gate(
        comparison,
        random_percentile_threshold=random_percentile_threshold,
        volatility_relative_limit=volatility_relative_limit,
        max_drawdown_penalty=max_drawdown_penalty,
        cvar_penalty=cvar_penalty,
        max_turnover=max_turnover,
        max_transaction_cost_drag=max_transaction_cost_drag,
    )


def _finite_gate_value(
    value: object,
    *,
    name: str,
    minimum: float,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite numeric value.") from exc
    minimum_ok = number >= minimum if minimum_inclusive else number > minimum
    maximum_ok = maximum is None or number <= maximum
    if not np.isfinite(number) or not minimum_ok or not maximum_ok:
        interval = (
            f"{minimum} <= {name} <= {maximum}"
            if maximum is not None and minimum_inclusive
            else (
                f"{minimum} < {name}"
                if maximum is None and not minimum_inclusive
                else f"{name} >= {minimum}"
            )
        )
        raise ValueError(f"{name} violates its configured domain ({interval}).")
    return number


def _apply_non_performance_blocks(
    gate: dict[str, object],
    constraint_row: pd.Series,
    fx_status: str,
    *,
    institutional_point_in_time_available: bool,
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
    if not institutional_point_in_time_available:
        blocked["Promoted"] = False
        blocked["Promotion_Decision"] = "not promoted"
        blocked["Reason"] = _append_reason(
            str(blocked["Reason"]),
            "Point-in-time historical universe membership and delisting evidence "
            "are unavailable; a current-universe diagnostic cannot promote an "
            "institutional global master portfolio.",
        )
    blocked["Institutional_Point_In_Time_Available"] = bool(
        institutional_point_in_time_available
    )
    blocked["Institutional_Promotion_Eligible"] = bool(
        blocked.get("Promoted", False) and institutional_point_in_time_available
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
    cov = _ledoit_wolf_covariance(returns).to_numpy(dtype=float)
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
        raise ValueError("Min Variance optimization failed: " + str(result.message))
    weights = pd.Series(result.x, index=assets, name="Weight")
    return weights / weights.sum()


def _ledoit_wolf_covariance(returns: pd.DataFrame) -> pd.DataFrame:
    complete = returns.apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if complete.shape[0] < 2:
        raise ValueError(
            "At least two complete common observations are required for "
            "Ledoit-Wolf covariance estimation."
        )
    covariance = (
        LedoitWolf().fit(complete.to_numpy(dtype=float)).covariance_
        * TRADING_DAYS_PER_YEAR
    )
    covariance = 0.5 * (covariance + covariance.T)
    if not np.isfinite(covariance).all():
        raise ValueError("Ledoit-Wolf covariance contains non-finite values.")
    if float(np.linalg.eigvalsh(covariance).min()) < -1e-10:
        raise ValueError("Ledoit-Wolf covariance is not positive semi-definite.")
    return pd.DataFrame(covariance, index=complete.columns, columns=complete.columns)


def _cluster_balanced_weights(returns: pd.DataFrame, max_weight: float) -> pd.Series:
    clusters = cluster_assets_by_correlation(returns)
    weights = pd.Series(0.0, index=returns.columns, dtype=float)
    for _, tickers in clusters.groupby(clusters).groups.items():
        cluster_weight = 1.0 / clusters.nunique()
        per_asset = cluster_weight / len(tickers)
        weights.loc[list(tickers)] = per_asset
    weights = apply_max_weight_cap(weights, max_weight)
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
        raise ValueError(
            "Policy-constrained optimization is infeasible: " + str(result.message)
        )
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
