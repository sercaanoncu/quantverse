"""Return-seeking champion-challenger research layer.

The functions in this module intentionally use only information available up to
each rebalance date. Equal Weight stays in the result set as the benchmark.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from project.backtest.metrics import PerformanceMetrics
from project.backtest.rebalancing import TransactionCosts
from project.constants import DEFAULT_RISK_FREE_RATE, TRADING_DAYS_PER_YEAR

ALLOWED_EVIDENCE_CLASSES = {
    "Strong challenger",
    "Moderate challenger",
    "Weak challenger",
    "Diagnostic only",
    "Failed / not robust",
}

ALLOWED_RESEARCH_EVIDENCE_CLASSES = {
    "Strong evidence",
    "Moderate evidence",
    "Weak evidence",
    "Diagnostic only",
    "Rejected: leakage",
    "Rejected: unstable",
    "Rejected: cost-sensitive",
    "Rejected: overfit risk",
}

ALLOWED_FINAL_LABELS = {
    "Broad Default Champion",
    "Annual Return Challenger Winner",
    "Risk-Adjusted Champion",
    "Defensive / Risk-Reduction Candidate",
    "Research Candidate",
    "Diagnostic Only",
    "Rejected",
}

ALLOWED_PROMOTION_DECISIONS = {
    "Promote to Broad Default Champion",
    "Promote to Annual Return Challenger",
    "Promote to Risk-Adjusted Champion",
    "Keep as Research Candidate",
    "Keep as Diagnostic Only",
    "Reject",
}


@dataclass(frozen=True)
class ChallengerConfig:
    """Configuration for the local champion-challenger research layer."""

    train_window: int = 504
    rebal_frequency: int = 63
    max_weight: float = 0.25
    transaction_cost_proportional: float = 0.001
    transaction_cost_spread: float = 0.0005
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE
    bootstrap_samples: int = 300
    bootstrap_block_size: int = 21
    random_seed: int = 42


StrategyFn = Callable[[pd.DataFrame], pd.Series]


def run_champion_challenger_research(
    output_dir: Path,
    returns: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> Dict[str, object]:
    """Run challenger research and write all requested artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_returns = returns.dropna().sort_index()
    costs = TransactionCosts(
        proportional=config.transaction_cost_proportional,
        spread=config.transaction_cost_spread,
    )

    strategies = _strategy_registry(clean_returns, class_map, config)
    base_results = _run_strategy_set(clean_returns, strategies, config, costs)
    equal_weight = base_results["Equal Weight"]["returns"]

    robustness = _bootstrap_vs_equal_weight(
        base_results,
        equal_weight,
        config,
    )
    summary = _summarize_results(base_results, equal_weight, robustness, config)
    returns_frame = pd.DataFrame(
        {name: result["returns"] for name, result in base_results.items()}
    )
    weights_frame = _weights_panel_to_frame(base_results)
    turnover = _turnover_frame(base_results)
    vs_equal = _vs_equal_weight_frame(base_results, equal_weight, config)
    subperiod = _subperiod_analysis(base_results, equal_weight, config)
    rolling = _rolling_relative_performance(base_results, equal_weight)
    cost_robustness = _cost_robustness(
        clean_returns,
        class_map,
        config,
        cost_bps_values=[0, 5, 10, 25, 50],
    )
    diagnostic = _equal_weight_diagnostic(
        returns=clean_returns,
        class_map=class_map,
        summary=summary,
        vs_equal=vs_equal,
        subperiod=subperiod,
        config=config,
    )
    metric_recompute = _asset_class_momentum_metric_recompute_check(
        summary=summary,
        returns_frame=returns_frame,
        config=config,
    )
    weight_audit = _asset_class_momentum_weight_audit(
        weights_frame=weights_frame,
        turnover=turnover,
        class_map=class_map,
        config=config,
    )
    champion = _champion_summary(
        summary=summary,
        robustness=robustness,
        cost_robustness=cost_robustness,
        subperiod=subperiod,
        rolling=rolling,
        config=config,
    )
    research_alpha = _research_alpha_leaderboard(
        summary=summary,
        robustness=robustness,
        cost_robustness=cost_robustness,
        subperiod=subperiod,
        champion=champion,
    )
    model_league = _model_league_summary(research_alpha, summary, champion)
    promotion_gate = _model_promotion_gate(research_alpha, summary)
    overfit_diagnostics = _model_overfit_diagnostics(research_alpha)

    summary.to_csv(output_dir / "challenger_backtest_summary.csv", index=False)
    returns_frame.to_csv(output_dir / "challenger_returns.csv", index_label="Date")
    weights_frame.to_csv(output_dir / "challenger_weights.csv", index=False)
    turnover.to_csv(output_dir / "challenger_turnover.csv", index=False)
    vs_equal.to_csv(output_dir / "challenger_vs_equal_weight.csv", index=False)
    subperiod.to_csv(output_dir / "challenger_subperiod_analysis.csv", index=False)
    rolling.to_csv(
        output_dir / "challenger_rolling_relative_performance.csv", index=False
    )
    cost_robustness.to_csv(output_dir / "challenger_cost_robustness.csv", index=False)
    robustness.to_csv(
        output_dir / "challenger_bootstrap_vs_equal_weight.csv", index=False
    )
    diagnostic.to_csv(output_dir / "equal_weight_diagnostic.csv", index=False)
    metric_recompute.to_csv(
        output_dir / "asset_class_momentum_metric_recompute_check.csv",
        index=False,
    )
    weight_audit.to_csv(
        output_dir / "asset_class_momentum_weight_audit.csv",
        index=False,
    )
    research_alpha.to_csv(output_dir / "research_alpha_leaderboard.csv", index=False)
    returns_frame.to_csv(output_dir / "research_alpha_returns.csv", index_label="Date")
    weights_frame.to_csv(output_dir / "research_alpha_weights.csv", index=False)
    turnover.to_csv(output_dir / "research_alpha_turnover.csv", index=False)
    vs_equal.to_csv(output_dir / "research_alpha_vs_equal_weight.csv", index=False)
    model_league.to_csv(output_dir / "model_league_summary.csv", index=False)
    (output_dir / "model_league_summary.json").write_text(
        json.dumps(model_league.to_dict(orient="records"), indent=2),
        encoding="utf-8",
    )
    promotion_gate.to_csv(output_dir / "model_promotion_gate.csv", index=False)
    overfit_diagnostics.to_csv(
        output_dir / "model_overfit_diagnostics.csv", index=False
    )
    (output_dir / "champion_selection_summary.json").write_text(
        json.dumps(champion, indent=2),
        encoding="utf-8",
    )

    return {
        "summary": summary,
        "returns": returns_frame,
        "weights": weights_frame,
        "turnover": turnover,
        "vs_equal_weight": vs_equal,
        "subperiod": subperiod,
        "rolling": rolling,
        "cost_robustness": cost_robustness,
        "bootstrap": robustness,
        "diagnostic": diagnostic,
        "asset_class_momentum_metric_recompute": metric_recompute,
        "asset_class_momentum_weight_audit": weight_audit,
        "research_alpha": research_alpha,
        "model_league": model_league,
        "promotion_gate": promotion_gate,
        "overfit_diagnostics": overfit_diagnostics,
        "champion": champion,
    }


def _strategy_registry(
    returns: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> Dict[str, StrategyFn]:
    return {
        "Equal Weight": lambda train: _equal_weight(train, config.max_weight),
        "Momentum Tilt 6M/12M": lambda train: _momentum_tilt(train, config),
        "Time-Series Momentum": lambda train: _time_series_momentum(train, config),
        "Cross-Asset Relative Momentum": lambda train: _cross_asset_momentum(
            train, config
        ),
        "Dual Momentum Absolute": lambda train: _dual_momentum(train, config),
        "Trend-Following MA": lambda train: _trend_following_ma(train, config),
        "Volatility-Scaled Momentum": lambda train: _vol_scaled_momentum(train, config),
        "Risk-Managed Equal Weight": lambda train: _risk_managed_equal_weight(
            train, class_map, config
        ),
        "Regime-Aware Allocation": lambda train: _regime_aware_allocation(
            train, class_map, config
        ),
        "Asset-Class Momentum Rotation": lambda train: _asset_class_rotation(
            train, class_map, config
        ),
        "Signal-Aware HRP Lite": lambda train: _signal_aware_hrp_lite(
            train, class_map, config
        ),
        "Shrunk Max Sharpe Nested": lambda train: _nested_shrunk_max_sharpe(
            train, config
        ),
    }


def _run_strategy_set(
    returns: pd.DataFrame,
    strategies: Dict[str, StrategyFn],
    config: ChallengerConfig,
    costs: TransactionCosts,
) -> Dict[str, Dict[str, object]]:
    return {
        name: _walk_forward_strategy(returns, optimizer, config, costs, name)
        for name, optimizer in strategies.items()
    }


def _walk_forward_strategy(
    returns: pd.DataFrame,
    optimizer: StrategyFn,
    config: ChallengerConfig,
    costs: TransactionCosts,
    label: str,
) -> Dict[str, object]:
    tickers = list(returns.columns)
    n_assets = len(tickers)
    if config.train_window >= len(returns):
        raise ValueError("train_window must be shorter than return history")

    current = np.ones(n_assets) / n_assets
    returns_out: list[float] = []
    weights_rows: list[Dict[str, object]] = []
    turnover_rows: list[Dict[str, object]] = []
    total_turnover = 0.0
    total_cost = 0.0
    days_since_rebalance = config.rebal_frequency

    for i in range(config.train_window, len(returns)):
        date = returns.index[i]
        daily = returns.iloc[i].to_numpy(dtype=float)
        cost_today = 0.0

        if days_since_rebalance >= config.rebal_frequency:
            train = returns.iloc[max(0, i - config.train_window) : i]
            proposed = optimizer(train)
            proposed = proposed.reindex(tickers).fillna(0.0).to_numpy(dtype=float)
            proposed = _sanitize_weights(proposed, config.max_weight)
            turnover = float(np.abs(proposed - current).sum())
            cost_today = float(costs.cost(turnover))
            current = proposed
            total_turnover += turnover
            total_cost += cost_today
            turnover_rows.append(
                {
                    "Date": date.date().isoformat(),
                    "Strategy": label,
                    "Turnover": turnover,
                    "Transaction_Cost": cost_today,
                }
            )
            days_since_rebalance = 0

        weights_rows.extend(
            {
                "Date": date.date().isoformat(),
                "Strategy": label,
                "Ticker": ticker,
                "Weight": float(weight),
            }
            for ticker, weight in zip(tickers, current)
        )

        returns_out.append(float(current @ daily - cost_today))
        drifted = current * (1.0 + daily)
        total_value = float(drifted.sum())
        if total_value > 0:
            current = drifted / total_value
        days_since_rebalance += 1

    series = pd.Series(
        returns_out, index=returns.index[config.train_window :], name=label
    )
    metrics = PerformanceMetrics(
        series, risk_free_rate=config.risk_free_rate
    ).full_report()
    years = max(len(series) / TRADING_DAYS_PER_YEAR, 1.0)
    n_rebalances = max(len(turnover_rows), 1)
    return {
        "returns": series,
        "metrics": metrics,
        "weights": pd.DataFrame(weights_rows),
        "turnover": pd.DataFrame(turnover_rows),
        "total_turnover": total_turnover,
        "average_turnover": total_turnover / n_rebalances,
        "total_cost": total_cost,
        "annualized_cost_drag": total_cost / years,
        "n_rebalances": len(turnover_rows),
    }


def _equal_weight(train: pd.DataFrame, max_weight: float) -> pd.Series:
    raw = np.ones(train.shape[1]) / train.shape[1]
    return pd.Series(_project_to_capped_simplex(raw, max_weight), index=train.columns)


def _momentum_tilt(train: pd.DataFrame, config: ChallengerConfig) -> pd.Series:
    score = 0.5 * _lookback_return(train, 126) + 0.5 * _lookback_return(train, 252)
    vol = train.tail(126).std().replace(0, np.nan) * np.sqrt(TRADING_DAYS_PER_YEAR)
    raw = score.clip(lower=0.0) / vol
    if raw.replace([np.inf, -np.inf], np.nan).dropna().sum() <= 0:
        raw = pd.Series(1.0, index=train.columns)
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    momentum = _project_to_capped_simplex(raw.to_numpy(), config.max_weight)
    blended = 0.40 * np.ones(train.shape[1]) / train.shape[1] + 0.60 * momentum
    return pd.Series(
        _project_to_capped_simplex(blended, config.max_weight), index=train.columns
    )


def _time_series_momentum(train: pd.DataFrame, config: ChallengerConfig) -> pd.Series:
    lookback = min(252, len(train))
    trailing = _lookback_return(train, lookback)
    hurdle = (1.0 + config.risk_free_rate) ** (lookback / TRADING_DAYS_PER_YEAR) - 1.0
    eligible = trailing > hurdle
    if not eligible.any():
        return _equal_weight(train, config.max_weight)

    vol = train.tail(min(126, len(train))).std().replace(0, np.nan)
    score = (trailing.where(eligible, 0.0).clip(lower=0.0) / vol).replace(
        [np.inf, -np.inf], np.nan
    )
    score = score.fillna(0.0)
    if score.sum() <= 0:
        score = eligible.astype(float)
    weights = _project_to_capped_simplex(score.to_numpy(), config.max_weight)
    return pd.Series(weights, index=train.columns)


def _cross_asset_momentum(train: pd.DataFrame, config: ChallengerConfig) -> pd.Series:
    score = 0.5 * _lookback_return(train, 126) + 0.5 * _lookback_return(train, 252)
    ranks = score.rank(method="first", ascending=False)
    top_count = max(1, int(np.ceil(len(score) / 3)))
    selected = ranks <= top_count
    raw = score.where(selected, 0.0).clip(lower=0.0)
    if raw.sum() <= 0:
        raw = selected.astype(float)
    concentrated = _project_to_capped_simplex(raw.to_numpy(), config.max_weight)
    diversified_floor = np.ones(train.shape[1]) / train.shape[1]
    blended = 0.25 * diversified_floor + 0.75 * concentrated
    return pd.Series(
        _project_to_capped_simplex(blended, config.max_weight),
        index=train.columns,
    )


def _dual_momentum(train: pd.DataFrame, config: ChallengerConfig) -> pd.Series:
    lookback = min(252, len(train))
    trailing = _lookback_return(train, lookback)
    hurdle = (1.0 + config.risk_free_rate) ** (lookback / TRADING_DAYS_PER_YEAR) - 1.0
    eligible = trailing > hurdle
    if eligible.any():
        score = trailing.where(eligible, 0.0).clip(lower=0.0)
    else:
        score = 1.0 / (train.tail(126).std().replace(0, np.nan))
    score = score.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return pd.Series(
        _project_to_capped_simplex(score.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _trend_following_ma(train: pd.DataFrame, config: ChallengerConfig) -> pd.Series:
    window = min(200, max(20, len(train) // 2))
    price_proxy = (1.0 + train).cumprod()
    ma = price_proxy.rolling(window).mean()
    trend_positive = price_proxy.iloc[-1] > ma.iloc[-1]
    if trend_positive.isna().all() or not bool(trend_positive.fillna(False).any()):
        return _equal_weight(train, config.max_weight)

    vol = train.tail(min(126, len(train))).std().replace(0, np.nan)
    score = (trend_positive.astype(float) / vol).replace([np.inf, -np.inf], np.nan)
    score = score.fillna(0.0)
    return pd.Series(
        _project_to_capped_simplex(score.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _vol_scaled_momentum(train: pd.DataFrame, config: ChallengerConfig) -> pd.Series:
    momentum = _lookback_return(train, 252).clip(lower=0.0)
    vol = train.tail(126).std().replace(0, np.nan)
    score = (momentum / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if score.sum() <= 0:
        score = pd.Series(1.0, index=train.columns)
    return pd.Series(
        _project_to_capped_simplex(score.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _risk_managed_equal_weight(
    train: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> pd.Series:
    weights = pd.Series(1.0 / train.shape[1], index=train.columns)
    recent = train.tail(126)
    vol = recent.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    drawdown = _lookback_drawdown(recent)
    risky_classes = {"us_equity_sectors", "international_equity", "crypto", "reits"}
    penalized = [
        ticker
        for ticker in train.columns
        if (
            vol.get(ticker, 0.0) > vol.median() * 1.25
            or drawdown.get(ticker, 0.0) < -0.20
            or class_map.get(ticker) == "crypto"
        )
        and class_map.get(ticker) in risky_classes
    ]
    if penalized:
        weights.loc[penalized] *= 0.55
        receivers = [
            ticker
            for ticker in train.columns
            if class_map.get(ticker) in {"fixed_income", "commodities"}
        ]
        if not receivers:
            receivers = (
                vol.sort_values().head(max(1, len(train.columns) // 4)).index.tolist()
            )
        freed = 1.0 - weights.sum()
        weights.loc[receivers] += freed / len(receivers)
    return pd.Series(
        _project_to_capped_simplex(weights.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _regime_aware_allocation(
    train: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> pd.Series:
    base = pd.Series(1.0 / train.shape[1], index=train.columns)
    ew = train.mean(axis=1)
    current_vol = float(ew.tail(63).std() * np.sqrt(TRADING_DAYS_PER_YEAR))
    rolling_vol = ew.rolling(63).std().dropna() * np.sqrt(TRADING_DAYS_PER_YEAR)
    vol_threshold = (
        float(rolling_vol.quantile(0.75)) if len(rolling_vol) else current_vol
    )
    current_dd = float(
        ((1 + ew.tail(126)).cumprod() / (1 + ew.tail(126)).cumprod().cummax() - 1).min()
    )

    growth = [
        ticker
        for ticker in train.columns
        if class_map.get(ticker)
        in {"us_equity_sectors", "international_equity", "crypto", "reits"}
    ]
    defensive = [
        ticker
        for ticker in train.columns
        if class_map.get(ticker) in {"fixed_income", "commodities"}
    ]
    if current_vol > vol_threshold or current_dd < -0.12:
        base.loc[growth] *= 0.65
        if defensive:
            base.loc[defensive] += (1.0 - base.sum()) / len(defensive)
    elif current_vol < rolling_vol.quantile(0.35) if len(rolling_vol) else False:
        momentum = _lookback_return(train, 126)
        top_growth = [
            ticker
            for ticker in momentum.sort_values(ascending=False).index
            if ticker in growth
        ][: max(1, len(growth) // 3)]
        base.loc[top_growth] *= 1.35
    return pd.Series(
        _project_to_capped_simplex(base.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _asset_class_rotation(
    train: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> pd.Series:
    class_returns: Dict[str, pd.Series] = {}
    for asset_class in sorted(set(class_map.values())):
        members = [
            ticker for ticker in train.columns if class_map.get(ticker) == asset_class
        ]
        if members:
            class_returns[asset_class] = train[members].mean(axis=1)
    if not class_returns:
        return _equal_weight(train, config.max_weight)

    scores = {
        asset_class: float((1.0 + series.tail(126)).prod() - 1.0)
        for asset_class, series in class_returns.items()
    }
    ranked = sorted(scores, key=scores.get, reverse=True)
    class_budget = {asset_class: 0.05 for asset_class in ranked}
    if ranked:
        class_budget[ranked[0]] = 0.45
    if len(ranked) > 1:
        class_budget[ranked[1]] = 0.25
    leftover = 1.0 - sum(class_budget.values())
    if leftover > 0 and ranked:
        for asset_class in ranked:
            class_budget[asset_class] += leftover / len(ranked)

    weights = pd.Series(0.0, index=train.columns)
    for asset_class, budget in class_budget.items():
        members = [
            ticker for ticker in train.columns if class_map.get(ticker) == asset_class
        ]
        if not members:
            continue
        vol = train[members].tail(126).std().replace(0, np.nan)
        inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        if inv.sum() <= 0:
            inv = pd.Series(1.0, index=members)
        weights.loc[members] = budget * inv / inv.sum()
    return pd.Series(
        _project_to_capped_simplex(weights.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _signal_aware_hrp_lite(
    train: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> pd.Series:
    vol = train.tail(min(126, len(train))).std().replace(0, np.nan)
    inv_vol = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if inv_vol.sum() <= 0:
        inv_vol = pd.Series(1.0, index=train.columns)

    momentum = _lookback_return(train, min(126, len(train)))
    score = inv_vol * (1.0 + momentum.clip(lower=-0.50))
    broad_return = train.mean(axis=1)
    recent_curve = (1.0 + broad_return.tail(min(126, len(broad_return)))).cumprod()
    broad_drawdown = float((recent_curve / recent_curve.cummax() - 1.0).min())
    risky_classes = {"us_equity_sectors", "international_equity", "crypto", "reits"}
    if broad_drawdown < -0.12:
        risky = [
            ticker for ticker in train.columns if class_map.get(ticker) in risky_classes
        ]
        defensive = [
            ticker
            for ticker in train.columns
            if class_map.get(ticker) in {"fixed_income", "commodities"}
        ]
        score.loc[risky] *= 0.70
        if defensive:
            score.loc[defensive] *= 1.20

    return pd.Series(
        _project_to_capped_simplex(score.to_numpy(), config.max_weight),
        index=train.columns,
    )


def _nested_shrunk_max_sharpe(
    train: pd.DataFrame, config: ChallengerConfig
) -> pd.Series:
    validation_window = min(126, max(21, len(train) // 4))
    if len(train) <= validation_window + 63:
        return _max_sharpe_weights(train, config, shrinkage=0.75)

    sub_train = train.iloc[:-validation_window]
    validation = train.iloc[-validation_window:]
    strengths = [0.25, 0.50, 0.75, 0.90]
    scores = []
    for shrinkage in strengths:
        weights = _max_sharpe_weights(sub_train, config, shrinkage=shrinkage)
        validation_returns = validation @ weights.reindex(validation.columns).fillna(
            0.0
        )
        metrics = PerformanceMetrics(
            validation_returns,
            risk_free_rate=config.risk_free_rate,
        ).full_report()
        scores.append((metrics["Sharpe Ratio"], shrinkage))
    selected = max(scores, key=lambda item: item[0])[1]
    return _max_sharpe_weights(train, config, shrinkage=selected)


def _max_sharpe_weights(
    train: pd.DataFrame,
    config: ChallengerConfig,
    shrinkage: float,
) -> pd.Series:
    raw_mu = train.mean() * TRADING_DAYS_PER_YEAR
    target = float(raw_mu.median())
    mu = ((1.0 - shrinkage) * raw_mu + shrinkage * target).to_numpy(dtype=float)
    cov = (
        LedoitWolf().fit(train.to_numpy(dtype=float)).covariance_
        * TRADING_DAYS_PER_YEAR
    )
    n_assets = train.shape[1]
    cap = config.max_weight
    start = _project_to_capped_simplex(np.ones(n_assets), cap)

    def objective(weights: np.ndarray) -> float:
        vol = float(np.sqrt(np.maximum(weights @ cov @ weights, 1e-12)))
        return -((float(weights @ mu) - config.risk_free_rate) / vol)

    result = minimize(
        objective,
        start,
        method="SLSQP",
        bounds=[(0.0, cap)] * n_assets,
        constraints=[{"type": "eq", "fun": lambda weights: weights.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-9},
    )
    if not result.success:
        raise RuntimeError(
            "Shrunk Max Sharpe optimization failed: " + str(result.message)
        )
    weights = result.x
    return pd.Series(_sanitize_weights(weights, cap), index=train.columns)


def _lookback_return(train: pd.DataFrame, lookback: int) -> pd.Series:
    window = train.tail(min(lookback, len(train)))
    return (1.0 + window).prod() - 1.0


def _lookback_drawdown(train: pd.DataFrame) -> pd.Series:
    curves = (1.0 + train).cumprod()
    return (curves / curves.cummax() - 1.0).min()


def _sanitize_weights(weights: Iterable[float], cap: float) -> np.ndarray:
    values = np.asarray(list(weights), dtype=float)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    values = np.maximum(values, 0.0)
    return _project_to_capped_simplex(values, cap)


def _project_to_capped_simplex(raw_weights: Iterable[float], cap: float) -> np.ndarray:
    weights = np.asarray(list(raw_weights), dtype=float)
    n_assets = len(weights)
    if cap * n_assets < 1.0:
        raise ValueError("max weight cap is infeasible for the asset count")
    weights = np.maximum(np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0), 0.0)
    if weights.sum() <= 1e-12:
        weights = np.ones(n_assets) / n_assets
    else:
        weights = weights / weights.sum()

    for _ in range(n_assets + 2):
        over = weights > cap
        if not over.any():
            break
        excess = float((weights[over] - cap).sum())
        weights[over] = cap
        free = ~over
        if not free.any():
            break
        free_sum = float(weights[free].sum())
        if free_sum <= 1e-12:
            weights[free] += excess / free.sum()
        else:
            weights[free] += excess * weights[free] / free_sum
    weights = np.minimum(weights, cap)
    if abs(weights.sum() - 1.0) > 1e-10:
        free = weights < cap - 1e-12
        if free.any() and weights[free].sum() > 0:
            weights[free] += (1.0 - weights.sum()) * weights[free] / weights[free].sum()
        else:
            weights = np.ones(n_assets) / n_assets
    return weights / weights.sum()


def _weights_panel_to_frame(results: Dict[str, Dict[str, object]]) -> pd.DataFrame:
    frames = [
        result["weights"]
        for result in results.values()
        if isinstance(result.get("weights"), pd.DataFrame)
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _turnover_frame(results: Dict[str, Dict[str, object]]) -> pd.DataFrame:
    frames = [
        result["turnover"]
        for result in results.values()
        if isinstance(result.get("turnover"), pd.DataFrame)
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _summarize_results(
    results: Dict[str, Dict[str, object]],
    equal_weight: pd.Series,
    bootstrap: pd.DataFrame,
    config: ChallengerConfig,
) -> pd.DataFrame:
    ew_metrics = PerformanceMetrics(
        equal_weight,
        risk_free_rate=config.risk_free_rate,
    ).full_report()
    rows = []
    boot = bootstrap.set_index("Strategy") if not bootstrap.empty else pd.DataFrame()
    for name, result in results.items():
        metrics = result["metrics"]
        beats_cagr = bool(metrics["CAGR"] > ew_metrics["CAGR"] + 1e-12)
        beats_sharpe = bool(
            metrics["Sharpe Ratio"] > ew_metrics["Sharpe Ratio"] + 1e-12
        )
        evidence = _evidence_class(name, beats_cagr, beats_sharpe, boot)
        rows.append(
            {
                "Strategy": name,
                "CAGR": metrics["CAGR"],
                "Annual_Return": metrics["CAGR"],
                "Volatility": metrics["Annualized Volatility"],
                "Sharpe": metrics["Sharpe Ratio"],
                "Sortino": metrics["Sortino Ratio"],
                "Calmar": metrics["Calmar Ratio"],
                "Max_Drawdown": metrics["Max Drawdown"],
                "Turnover": result["total_turnover"],
                "Average_Turnover_Per_Rebalance": result["average_turnover"],
                "Transaction_Cost_Drag": result["annualized_cost_drag"],
                "Hit_Rate_By_Rebalance": _rebalance_hit_rate(
                    result["returns"],
                    equal_weight,
                    config.rebal_frequency,
                ),
                "Beats_Equal_Weight_CAGR": beats_cagr,
                "Beats_Equal_Weight_Sharpe": beats_sharpe,
                "Evidence_Class": evidence,
                "Notes": _strategy_note(name, evidence),
            }
        )
    return pd.DataFrame(rows).sort_values("CAGR", ascending=False)


def _evidence_class(
    strategy: str,
    beats_cagr: bool,
    beats_sharpe: bool,
    bootstrap: pd.DataFrame,
) -> str:
    if strategy == "Equal Weight":
        return "Diagnostic only"
    ci_low = (
        float(bootstrap.loc[strategy, "CAGR_Diff_CI_5"])
        if strategy in bootstrap.index
        else np.nan
    )
    sharpe_ci_low = (
        float(bootstrap.loc[strategy, "Sharpe_Diff_CI_5"])
        if strategy in bootstrap.index
        else np.nan
    )
    if (
        beats_cagr
        and beats_sharpe
        and pd.notna(ci_low)
        and ci_low > 0
        and pd.notna(sharpe_ci_low)
        and sharpe_ci_low > 0
    ):
        return "Strong challenger"
    if beats_cagr and (beats_sharpe or (pd.notna(ci_low) and ci_low > 0)):
        return "Moderate challenger"
    if beats_cagr:
        return "Weak challenger"
    if strategy == "Shrunk Max Sharpe Nested":
        return "Failed / not robust"
    return "Diagnostic only"


def _strategy_note(strategy: str, evidence_class: str) -> str:
    notes = {
        "Equal Weight": "Benchmark; retained as the reference champion unless a challenger wins out-of-sample.",
        "Shrunk Max Sharpe Nested": "Nested shrinkage selection uses only train/validation data inside each rebalance window.",
        "Momentum Tilt 6M/12M": "Trailing 6M/12M return tilt with volatility scaling and max-weight cap.",
        "Dual Momentum Absolute": "Positive absolute momentum rule versus a risk-free hurdle; no cash sleeve is assumed.",
        "Regime-Aware Allocation": "Rules use trailing volatility and drawdown only; no full-sample regime labels are used.",
    }
    return f"{notes.get(strategy, 'Long-only capped walk-forward challenger.')} Evidence class: {evidence_class}."


def _rebalance_hit_rate(
    strategy_returns: pd.Series,
    equal_weight: pd.Series,
    rebal_frequency: int,
) -> float:
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "equal": equal_weight}
    ).dropna()
    if aligned.empty:
        return float("nan")
    groups = np.arange(len(aligned)) // rebal_frequency
    strategy_period = (
        aligned["strategy"].groupby(groups).apply(lambda x: (1.0 + x).prod() - 1.0)
    )
    equal_period = (
        aligned["equal"].groupby(groups).apply(lambda x: (1.0 + x).prod() - 1.0)
    )
    return float((strategy_period > equal_period).mean())


def _vs_equal_weight_frame(
    results: Dict[str, Dict[str, object]],
    equal_weight: pd.Series,
    config: ChallengerConfig,
) -> pd.DataFrame:
    ew_metrics = PerformanceMetrics(
        equal_weight,
        risk_free_rate=config.risk_free_rate,
    ).full_report()
    rows = []
    for name, result in results.items():
        metrics = result["metrics"]
        rows.append(
            {
                "Strategy": name,
                "CAGR_Diff": metrics["CAGR"] - ew_metrics["CAGR"],
                "Sharpe_Diff": metrics["Sharpe Ratio"] - ew_metrics["Sharpe Ratio"],
                "Volatility_Diff": metrics["Annualized Volatility"]
                - ew_metrics["Annualized Volatility"],
                "Max_Drawdown_Diff": metrics["Max Drawdown"]
                - ew_metrics["Max Drawdown"],
                "Hit_Rate_By_Rebalance": _rebalance_hit_rate(
                    result["returns"],
                    equal_weight,
                    config.rebal_frequency,
                ),
            }
        )
    return pd.DataFrame(rows)


def _subperiod_analysis(
    results: Dict[str, Dict[str, object]],
    equal_weight: pd.Series,
    config: ChallengerConfig,
) -> pd.DataFrame:
    columns = [
        "Subperiod",
        "Strategy",
        "Start",
        "End",
        "CAGR",
        "Sharpe",
        "Max_Drawdown",
        "CAGR_Diff_vs_Equal_Weight",
        "Sharpe_Diff_vs_Equal_Weight",
    ]
    periods = {
        "pre-COVID": (None, "2020-02-19"),
        "COVID crash": ("2020-02-20", "2020-04-30"),
        "2022 inflation/rate shock": ("2022-01-01", "2022-12-31"),
        "recent period": ("2024-01-01", None),
    }
    rows = []
    for strategy, result in results.items():
        series = result["returns"]
        for label, (start, end) in periods.items():
            window = series.copy()
            if start is not None:
                window = window.loc[window.index >= pd.Timestamp(start)]
            if end is not None:
                window = window.loc[window.index <= pd.Timestamp(end)]
            ew = equal_weight.reindex(window.index).dropna()
            window = window.reindex(ew.index).dropna()
            if len(window) < 10:
                continue
            metrics = PerformanceMetrics(
                window,
                risk_free_rate=config.risk_free_rate,
            ).full_report()
            ew_metrics = PerformanceMetrics(
                ew,
                risk_free_rate=config.risk_free_rate,
            ).full_report()
            rows.append(
                {
                    "Subperiod": label,
                    "Strategy": strategy,
                    "Start": str(window.index[0].date()),
                    "End": str(window.index[-1].date()),
                    "CAGR": metrics["CAGR"],
                    "Sharpe": metrics["Sharpe Ratio"],
                    "Max_Drawdown": metrics["Max Drawdown"],
                    "CAGR_Diff_vs_Equal_Weight": metrics["CAGR"] - ew_metrics["CAGR"],
                    "Sharpe_Diff_vs_Equal_Weight": metrics["Sharpe Ratio"]
                    - ew_metrics["Sharpe Ratio"],
                }
            )
    return pd.DataFrame(rows, columns=columns)


def _rolling_relative_performance(
    results: Dict[str, Dict[str, object]],
    equal_weight: pd.Series,
) -> pd.DataFrame:
    columns = [
        "Date",
        "Strategy",
        "Window",
        "Rolling_CAGR_Diff_vs_Equal_Weight",
    ]
    rows = []
    for strategy, result in results.items():
        if strategy == "Equal Weight":
            continue
        aligned = pd.DataFrame(
            {"strategy": result["returns"], "equal": equal_weight}
        ).dropna()
        for window, label in [(252, "1Y"), (756, "3Y")]:
            if len(aligned) < window:
                continue
            strategy_cagr = aligned["strategy"].rolling(window).apply(_window_cagr)
            equal_cagr = aligned["equal"].rolling(window).apply(_window_cagr)
            diff = (strategy_cagr - equal_cagr).dropna()
            for date, value in diff.items():
                rows.append(
                    {
                        "Date": date.date().isoformat(),
                        "Strategy": strategy,
                        "Window": label,
                        "Rolling_CAGR_Diff_vs_Equal_Weight": float(value),
                    }
                )
    return pd.DataFrame(rows, columns=columns)


def _window_cagr(values: np.ndarray) -> float:
    total = float(np.prod(1.0 + values) - 1.0)
    years = len(values) / TRADING_DAYS_PER_YEAR
    return (1.0 + total) ** (1.0 / years) - 1.0 if years > 0 else np.nan


def _cost_robustness(
    returns: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
    cost_bps_values: Iterable[int],
) -> pd.DataFrame:
    rows = []
    strategies = _strategy_registry(returns, class_map, config)
    for bps in cost_bps_values:
        run_config = ChallengerConfig(
            train_window=config.train_window,
            rebal_frequency=config.rebal_frequency,
            max_weight=config.max_weight,
            transaction_cost_proportional=bps / 10000,
            transaction_cost_spread=0.0,
            risk_free_rate=config.risk_free_rate,
            bootstrap_samples=config.bootstrap_samples,
            bootstrap_block_size=config.bootstrap_block_size,
            random_seed=config.random_seed,
        )
        results = _run_strategy_set(
            returns,
            strategies,
            run_config,
            TransactionCosts(proportional=bps / 10000, spread=0.0),
        )
        equal = results["Equal Weight"]["returns"]
        ew_metrics = results["Equal Weight"]["metrics"]
        for strategy, result in results.items():
            metrics = result["metrics"]
            rows.append(
                {
                    "Cost_Bps": bps,
                    "Strategy": strategy,
                    "CAGR": metrics["CAGR"],
                    "Sharpe": metrics["Sharpe Ratio"],
                    "Max_Drawdown": metrics["Max Drawdown"],
                    "CAGR_Diff_vs_Equal_Weight": metrics["CAGR"] - ew_metrics["CAGR"],
                    "Sharpe_Diff_vs_Equal_Weight": metrics["Sharpe Ratio"]
                    - ew_metrics["Sharpe Ratio"],
                    "Beats_Equal_Weight_CAGR": bool(
                        metrics["CAGR"] > ew_metrics["CAGR"] + 1e-12
                    ),
                    "Hit_Rate_By_Rebalance": _rebalance_hit_rate(
                        result["returns"],
                        equal,
                        config.rebal_frequency,
                    ),
                }
            )
    return pd.DataFrame(rows)


def _asset_class_momentum_metric_recompute_check(
    summary: pd.DataFrame,
    returns_frame: pd.DataFrame,
    config: ChallengerConfig,
) -> pd.DataFrame:
    strategy = "Asset-Class Momentum Rotation"
    columns = [
        "Strategy",
        "Metric",
        "Summary_Value",
        "Recomputed_Value",
        "Absolute_Diff",
        "Matches",
        "Tolerance",
        "Source",
        "Conclusion",
    ]
    if strategy not in returns_frame.columns:
        return pd.DataFrame(columns=columns)

    series = returns_frame[strategy].dropna()
    metrics = PerformanceMetrics(
        series,
        risk_free_rate=config.risk_free_rate,
    ).full_report()
    summary_rows = summary[summary["Strategy"].eq(strategy)]
    if summary_rows.empty:
        return pd.DataFrame(columns=columns)

    row = summary_rows.iloc[0]
    mapping = {
        "CAGR": "CAGR",
        "Annual_Return": "CAGR",
        "Volatility": "Annualized Volatility",
        "Sharpe": "Sharpe Ratio",
        "Sortino": "Sortino Ratio",
        "Calmar": "Calmar Ratio",
        "Max_Drawdown": "Max Drawdown",
    }
    tolerance = 1e-10
    rows = []
    for summary_metric, recomputed_metric in mapping.items():
        summary_value = float(row[summary_metric])
        recomputed_value = float(metrics[recomputed_metric])
        diff = abs(summary_value - recomputed_value)
        rows.append(
            {
                "Strategy": strategy,
                "Metric": summary_metric,
                "Summary_Value": summary_value,
                "Recomputed_Value": recomputed_value,
                "Absolute_Diff": diff,
                "Matches": bool(diff <= tolerance),
                "Tolerance": tolerance,
                "Source": "challenger_returns.csv recomputed with PerformanceMetrics",
                "Conclusion": (
                    "Matches saved summary."
                    if diff <= tolerance
                    else "Mismatch; investigate before promotion."
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _asset_class_momentum_weight_audit(
    weights_frame: pd.DataFrame,
    turnover: pd.DataFrame,
    class_map: Dict[str, str],
    config: ChallengerConfig,
) -> pd.DataFrame:
    strategy = "Asset-Class Momentum Rotation"
    columns = [
        "Date",
        "Strategy",
        "Is_Rebalance_Date",
        "Asset_Count",
        "Nonzero_Weight_Count",
        "Weight_Sum",
        "Min_Weight",
        "Max_Weight",
        "Long_Only",
        "Sum_To_One",
        "Cap_Check_Applies",
        "Max_Weight_Cap",
        "Cap_Respected_On_Rebalance",
        "Top_Ticker",
        "Top_Asset_Class",
        "Top_Weight",
    ]
    if weights_frame.empty:
        return pd.DataFrame(columns=columns)

    rows_for_strategy = weights_frame[weights_frame["Strategy"].eq(strategy)].copy()
    if rows_for_strategy.empty:
        return pd.DataFrame(columns=columns)

    rebalance_dates = set()
    if not turnover.empty:
        rebalance_dates = set(
            turnover[turnover["Strategy"].eq(strategy)]["Date"].astype(str)
        )

    rows = []
    for date, date_rows in rows_for_strategy.groupby("Date", sort=True):
        weights = date_rows.set_index("Ticker")["Weight"].astype(float)
        top_ticker = str(weights.idxmax())
        is_rebalance = str(date) in rebalance_dates
        cap_respected = (
            bool(weights.max() <= config.max_weight + 1e-10) if is_rebalance else True
        )
        rows.append(
            {
                "Date": str(date),
                "Strategy": strategy,
                "Is_Rebalance_Date": bool(is_rebalance),
                "Asset_Count": int(len(weights)),
                "Nonzero_Weight_Count": int((weights > 1e-12).sum()),
                "Weight_Sum": float(weights.sum()),
                "Min_Weight": float(weights.min()),
                "Max_Weight": float(weights.max()),
                "Long_Only": bool((weights >= -1e-12).all()),
                "Sum_To_One": bool(abs(weights.sum() - 1.0) <= 1e-8),
                "Cap_Check_Applies": bool(is_rebalance),
                "Max_Weight_Cap": config.max_weight,
                "Cap_Respected_On_Rebalance": cap_respected,
                "Top_Ticker": top_ticker,
                "Top_Asset_Class": class_map.get(top_ticker, "unknown"),
                "Top_Weight": float(weights.loc[top_ticker]),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _bootstrap_vs_equal_weight(
    results: Dict[str, Dict[str, object]],
    equal_weight: pd.Series,
    config: ChallengerConfig,
) -> pd.DataFrame:
    rng = np.random.default_rng(config.random_seed)
    rows = []
    for strategy, result in results.items():
        if strategy == "Equal Weight":
            rows.append(
                {
                    "Strategy": strategy,
                    "Samples": config.bootstrap_samples,
                    "CAGR_Diff": 0.0,
                    "CAGR_Diff_CI_5": 0.0,
                    "CAGR_Diff_CI_95": 0.0,
                    "Sharpe_Diff": 0.0,
                    "Sharpe_Diff_CI_5": 0.0,
                    "Sharpe_Diff_CI_95": 0.0,
                    "Conclusion": "Benchmark comparator.",
                }
            )
            continue
        aligned = pd.DataFrame(
            {"strategy": result["returns"], "equal": equal_weight}
        ).dropna()
        diffs = _paired_bootstrap_diffs(aligned, config, rng)
        observed = _metric_diffs(aligned, config.risk_free_rate)
        rows.append(
            {
                "Strategy": strategy,
                "Samples": config.bootstrap_samples,
                "CAGR_Diff": observed["CAGR"],
                "CAGR_Diff_CI_5": np.nanpercentile(diffs["CAGR"], 5),
                "CAGR_Diff_CI_95": np.nanpercentile(diffs["CAGR"], 95),
                "Sharpe_Diff": observed["Sharpe"],
                "Sharpe_Diff_CI_5": np.nanpercentile(diffs["Sharpe"], 5),
                "Sharpe_Diff_CI_95": np.nanpercentile(diffs["Sharpe"], 95),
                "Conclusion": _bootstrap_conclusion(
                    np.nanpercentile(diffs["CAGR"], 5),
                    np.nanpercentile(diffs["CAGR"], 95),
                ),
            }
        )
    return pd.DataFrame(rows)


def _paired_bootstrap_diffs(
    aligned: pd.DataFrame,
    config: ChallengerConfig,
    rng: np.random.Generator,
) -> Dict[str, np.ndarray]:
    values = aligned[["strategy", "equal"]].to_numpy(dtype=float)
    n_obs = len(values)
    block = min(max(1, config.bootstrap_block_size), n_obs)
    n_blocks = int(np.ceil(n_obs / block))
    cagr = np.full(config.bootstrap_samples, np.nan)
    sharpe = np.full(config.bootstrap_samples, np.nan)
    for sample in range(config.bootstrap_samples):
        chunks = []
        for _ in range(n_blocks):
            start = int(rng.integers(0, max(1, n_obs - block + 1)))
            chunks.append(values[start : start + block])
        sampled = np.vstack(chunks)[:n_obs]
        frame = pd.DataFrame(sampled, columns=["strategy", "equal"])
        diffs = _metric_diffs(frame, config.risk_free_rate)
        cagr[sample] = diffs["CAGR"]
        sharpe[sample] = diffs["Sharpe"]
    return {"CAGR": cagr, "Sharpe": sharpe}


def _metric_diffs(frame: pd.DataFrame, risk_free_rate: float) -> Dict[str, float]:
    strategy_metrics = PerformanceMetrics(
        frame["strategy"],
        risk_free_rate=risk_free_rate,
    )
    equal_metrics = PerformanceMetrics(
        frame["equal"],
        risk_free_rate=risk_free_rate,
    )
    return {
        "CAGR": strategy_metrics.cagr() - equal_metrics.cagr(),
        "Sharpe": strategy_metrics.sharpe_ratio() - equal_metrics.sharpe_ratio(),
    }


def _bootstrap_conclusion(ci_low: float, ci_high: float) -> str:
    if pd.isna(ci_low) or pd.isna(ci_high):
        return "Inconclusive bootstrap interval."
    if ci_low > 0:
        return "Positive CAGR difference survives this bootstrap check."
    if ci_high < 0:
        return "Negative CAGR difference in this bootstrap check."
    return (
        "Interval crosses zero; do not treat the difference as statistically settled."
    )


def _equal_weight_diagnostic(
    returns: pd.DataFrame,
    class_map: Dict[str, str],
    summary: pd.DataFrame,
    vs_equal: pd.DataFrame,
    subperiod: pd.DataFrame,
    config: ChallengerConfig,
) -> pd.DataFrame:
    ew = summary[summary["Strategy"].eq("Equal Weight")].iloc[0]
    best_cagr = summary.iloc[0]
    best_sharpe = summary.sort_values("Sharpe", ascending=False).iloc[0]
    class_contrib = _equal_weight_class_contribution(returns, class_map)
    risky_contrib = class_contrib[
        class_contrib["Asset_Class"].isin(
            ["us_equity_sectors", "international_equity", "crypto", "commodities"]
        )
    ]["Approx_Annual_Return_Contribution"].sum()
    ew_sub = (
        subperiod[subperiod["Strategy"].eq("Equal Weight")]
        if "Strategy" in subperiod
        else pd.DataFrame()
    )
    challengers = vs_equal[~vs_equal["Strategy"].eq("Equal Weight")]
    rows = [
        _diagnostic_row(
            "broad_diversification",
            "Effective asset breadth",
            returns.shape[1],
            "Equal Weight holds every surviving investable asset, limiting estimator error and single-model dependence.",
            "Use as the benchmark because no estimated return vector is required.",
        ),
        _diagnostic_row(
            "noisy_expected_returns",
            "Optimizers beating EW on CAGR",
            int(challengers["CAGR_Diff"].gt(0).sum()),
            "Few or no return-estimation models beat the naive benchmark when tested out-of-sample.",
            "Expected return estimates are noisy; simple diversification can dominate fragile optimization.",
        ),
        _diagnostic_row(
            "optimized_defensive_concentration",
            "Best Sharpe model",
            str(best_sharpe["Strategy"]),
            "Risk-focused models may improve Sharpe or drawdown while giving up CAGR.",
            "A risk interview should separate return target from risk-adjusted utility.",
        ),
        _diagnostic_row(
            "transaction_cost_drag",
            "EW cost drag",
            float(ew["Transaction_Cost_Drag"]),
            "Active challengers require turnover; cost drag is measured net of transaction costs.",
            "A strategy must beat EW after costs, not before costs.",
        ),
        _diagnostic_row(
            "rebalance_window",
            "Rebalance frequency",
            config.rebal_frequency,
            "The same calendar is applied to all challengers, so any advantage is not a timing artifact.",
            "Changing this value would be a separate hyperparameter study.",
        ),
        _diagnostic_row(
            "growth_asset_exposure",
            "EW risky annual contribution",
            float(risky_contrib),
            "Equity, commodity and crypto exposure can drive CAGR in risk-on periods.",
            "Return leadership must be checked against drawdown and subperiod behavior.",
        ),
        _diagnostic_row(
            "regime_dependency",
            "EW subperiods evaluated",
            int(ew_sub["Subperiod"].nunique()),
            "EW is not assumed to win all regimes; subperiod and rolling relative tables expose regime dependence.",
            "A challenger winning one regime is not automatically a new champion.",
        ),
        _diagnostic_row(
            "return_vs_drawdown",
            "EW max drawdown",
            float(ew["Max_Drawdown"]),
            "EW can lead on CAGR while carrying larger drawdowns than defensive allocations.",
            "The champion depends on objective: annual return or risk-adjusted defensibility.",
        ),
        _diagnostic_row(
            "hrp_return_tradeoff",
            "Best CAGR model",
            str(best_cagr["Strategy"]),
            "HRP-like diversification can reduce risk but may sacrifice growth exposure.",
            "HRP remains a risk candidate when drawdown control matters more than CAGR.",
        ),
        _diagnostic_row(
            "max_sharpe_instability",
            "Nested max-sharpe evidence",
            str(
                summary[summary["Strategy"].eq("Shrunk Max Sharpe Nested")][
                    "Evidence_Class"
                ].iloc[0]
            ),
            "Even shrinkage cannot remove all expected-return estimation error.",
            "Max Sharpe is diagnostic unless nested OOS evidence is stronger than EW.",
        ),
    ]
    rows.extend(class_contrib.to_dict("records"))
    return pd.DataFrame(rows)


def _diagnostic_row(
    diagnostic: str,
    metric: str,
    value: object,
    interpretation: str,
    evidence: str,
) -> Dict[str, object]:
    return {
        "Diagnostic": diagnostic,
        "Metric": metric,
        "Value": value,
        "Interpretation": interpretation,
        "Evidence": evidence,
    }


def _equal_weight_class_contribution(
    returns: pd.DataFrame,
    class_map: Dict[str, str],
) -> pd.DataFrame:
    weights = pd.Series(1.0 / returns.shape[1], index=returns.columns)
    rows = []
    for asset_class in sorted(set(class_map.values())):
        members = [
            ticker for ticker in returns.columns if class_map.get(ticker) == asset_class
        ]
        if not members:
            continue
        contribution = float(
            (returns[members].mean() * weights.loc[members]).sum()
            * TRADING_DAYS_PER_YEAR
        )
        rows.append(
            {
                "Diagnostic": f"class_contribution_{asset_class}",
                "Metric": "Approx annual return contribution",
                "Value": contribution,
                "Interpretation": f"Equal Weight contribution from {asset_class}.",
                "Evidence": "Computed from investable daily returns and equal asset weights.",
                "Asset_Class": asset_class,
                "Approx_Annual_Return_Contribution": contribution,
            }
        )
    return pd.DataFrame(rows)


def _research_alpha_leaderboard(
    summary: pd.DataFrame,
    robustness: pd.DataFrame,
    cost_robustness: pd.DataFrame,
    subperiod: pd.DataFrame,
    champion: Dict[str, object],
) -> pd.DataFrame:
    boot = robustness.set_index("Strategy") if not robustness.empty else pd.DataFrame()
    rows = []
    for _, row in summary.iterrows():
        strategy = str(row["Strategy"])
        cagr_low = _table_value(boot, strategy, "CAGR_Diff_CI_5", 0.0)
        cagr_high = _table_value(boot, strategy, "CAGR_Diff_CI_95", 0.0)
        sharpe_low = _table_value(boot, strategy, "Sharpe_Diff_CI_5", 0.0)
        sharpe_high = _table_value(boot, strategy, "Sharpe_Diff_CI_95", 0.0)
        subperiod_win_rate = _subperiod_win_rate(subperiod, strategy)
        survives_25bps = _survives_cost_bps(cost_robustness, strategy, 25)
        survives_50bps = _survives_cost_bps(cost_robustness, strategy, 50)
        evidence = _research_evidence_class(
            strategy=strategy,
            summary_row=row,
            cagr_low=cagr_low,
            sharpe_low=sharpe_low,
            survives_25bps=survives_25bps,
            survives_50bps=survives_50bps,
            subperiod_win_rate=subperiod_win_rate,
        )
        final_label = _final_label(
            strategy=strategy,
            summary_row=row,
            evidence=evidence,
            champion=champion,
            summary=summary,
        )
        rows.append(
            {
                "Strategy": strategy,
                "Model_Family": _model_family(strategy),
                "League": final_label,
                "CAGR": float(row["CAGR"]),
                "Annual_Return": float(row["Annual_Return"]),
                "Volatility": float(row["Volatility"]),
                "Sharpe": float(row["Sharpe"]),
                "Sortino": float(row["Sortino"]),
                "Calmar": float(row["Calmar"]),
                "Max_Drawdown": float(row["Max_Drawdown"]),
                "Turnover": float(row["Turnover"]),
                "Transaction_Cost_Drag": float(row["Transaction_Cost_Drag"]),
                "Beats_Equal_Weight_CAGR": bool(row["Beats_Equal_Weight_CAGR"]),
                "Beats_Equal_Weight_Sharpe": bool(row["Beats_Equal_Weight_Sharpe"]),
                "Beats_Equal_Weight_Calmar": _beats_equal_weight_metric(
                    summary, row, "Calmar"
                ),
                "Beats_Equal_Weight_After_25bps": survives_25bps,
                "Beats_Equal_Weight_After_50bps": survives_50bps,
                "Subperiod_Win_Rate": subperiod_win_rate,
                "Bootstrap_CAGR_Diff_Lower": cagr_low,
                "Bootstrap_CAGR_Diff_Upper": cagr_high,
                "Bootstrap_Sharpe_Diff_Lower": sharpe_low,
                "Bootstrap_Sharpe_Diff_Upper": sharpe_high,
                "PBO_or_Overfit_Flag": _overfit_flag(
                    strategy, evidence, cagr_low, sharpe_low, subperiod_win_rate
                ),
                "Evidence_Class": evidence,
                "Final_Label": final_label,
                "Notes": _research_note(strategy, evidence, final_label),
            }
        )
    return pd.DataFrame(rows).sort_values("CAGR", ascending=False)


def _table_value(
    indexed: pd.DataFrame, index_value: str, column: str, default: float
) -> float:
    if indexed.empty or index_value not in indexed.index or column not in indexed:
        return default
    value = indexed.loc[index_value, column]
    if isinstance(value, pd.Series):
        value = value.iloc[0]
    return float(value)


def _subperiod_win_rate(subperiod: pd.DataFrame, strategy: str) -> float:
    if subperiod.empty:
        return float("nan")
    rows = subperiod[subperiod["Strategy"].eq(strategy)]
    if rows.empty:
        return float("nan")
    return float(rows["CAGR_Diff_vs_Equal_Weight"].gt(0.0).mean())


def _survives_cost_bps(cost_robustness: pd.DataFrame, strategy: str, bps: int) -> bool:
    if strategy == "Equal Weight":
        return True
    if cost_robustness.empty:
        return False
    rows = cost_robustness[
        cost_robustness["Strategy"].eq(strategy) & cost_robustness["Cost_Bps"].eq(bps)
    ]
    return bool(not rows.empty and rows.iloc[0]["Beats_Equal_Weight_CAGR"])


def _beats_equal_weight_metric(
    summary: pd.DataFrame, row: pd.Series, metric: str
) -> bool:
    ew = summary[summary["Strategy"].eq("Equal Weight")].iloc[0]
    return bool(float(row[metric]) > float(ew[metric]) + 1e-12)


def _research_evidence_class(
    strategy: str,
    summary_row: pd.Series,
    cagr_low: float,
    sharpe_low: float,
    survives_25bps: bool,
    survives_50bps: bool,
    subperiod_win_rate: float,
) -> str:
    if strategy == "Equal Weight":
        return "Diagnostic only"
    beats_cagr = bool(summary_row["Beats_Equal_Weight_CAGR"])
    beats_sharpe = bool(summary_row["Beats_Equal_Weight_Sharpe"])
    if strategy == "Shrunk Max Sharpe Nested":
        return "Rejected: overfit risk"
    if beats_cagr and not survives_25bps:
        return "Rejected: cost-sensitive"
    if beats_cagr and pd.notna(subperiod_win_rate) and subperiod_win_rate < 0.25:
        return "Rejected: unstable"
    if (
        beats_cagr
        and beats_sharpe
        and cagr_low > 0.0
        and sharpe_low > 0.0
        and survives_25bps
        and survives_50bps
    ):
        return "Strong evidence"
    if beats_cagr and cagr_low > 0.0 and survives_25bps and survives_50bps:
        return "Moderate evidence"
    if beats_cagr:
        return "Weak evidence"
    return "Diagnostic only"


def _final_label(
    strategy: str,
    summary_row: pd.Series,
    evidence: str,
    champion: Dict[str, object],
    summary: pd.DataFrame,
) -> str:
    if strategy == "Equal Weight":
        return "Broad Default Champion"
    if evidence.startswith("Rejected:"):
        return "Rejected"
    if (
        strategy == champion.get("best_cagr_model")
        and champion.get("annual_return_challenger_wins") is True
    ):
        return "Annual Return Challenger Winner"
    if evidence == "Strong evidence" and strategy == champion.get(
        "best_risk_adjusted_model"
    ):
        return "Risk-Adjusted Champion"
    defensive_candidate = summary.sort_values("Max_Drawdown", ascending=False).iloc[0][
        "Strategy"
    ]
    if strategy == defensive_candidate and strategy != "Equal Weight":
        return "Defensive / Risk-Reduction Candidate"
    if evidence == "Diagnostic only":
        return "Diagnostic Only"
    return "Research Candidate"


def _model_family(strategy: str) -> str:
    families = {
        "Equal Weight": "Benchmark",
        "Momentum Tilt 6M/12M": "Cross-asset momentum",
        "Time-Series Momentum": "Time-series momentum",
        "Cross-Asset Relative Momentum": "Cross-asset momentum",
        "Dual Momentum Absolute": "Time-series momentum",
        "Trend-Following MA": "Trend-following",
        "Volatility-Scaled Momentum": "Volatility-scaled momentum",
        "Risk-Managed Equal Weight": "Risk-managed benchmark",
        "Regime-Aware Allocation": "Regime-aware rules",
        "Asset-Class Momentum Rotation": "Asset-class momentum rotation",
        "Signal-Aware HRP Lite": "Risk allocation with signal overlay",
        "Shrunk Max Sharpe Nested": "Shrunk expected-return optimization",
    }
    return families.get(strategy, "Research challenger")


def _overfit_flag(
    strategy: str,
    evidence: str,
    cagr_low: float,
    sharpe_low: float,
    subperiod_win_rate: float,
) -> str:
    if strategy == "Equal Weight":
        return "Benchmark; no model selection flag."
    if evidence.startswith("Rejected:"):
        return evidence
    if cagr_low <= 0.0 or sharpe_low <= 0.0:
        return "Bootstrap interval crosses zero; treat as exploratory."
    if pd.notna(subperiod_win_rate) and subperiod_win_rate < 0.50:
        return "Subperiod instability; promotion blocked."
    return "No material flag in implemented checks."


def _research_note(strategy: str, evidence: str, final_label: str) -> str:
    if strategy == "Equal Weight":
        return "Hard-to-beat broad benchmark; does not estimate expected returns."
    if final_label == "Annual Return Challenger Winner":
        return "Highest OOS CAGR challenger after implemented cost and bootstrap CAGR checks; not a broad default replacement."
    if final_label == "Rejected":
        return "Rejected for this sprint's promotion rule; retained for diagnostics and auditability."
    return f"{_strategy_note(strategy, evidence)} Final label: {final_label}."


def _model_league_summary(
    research_alpha: pd.DataFrame,
    summary: pd.DataFrame,
    champion: Dict[str, object],
) -> pd.DataFrame:
    rows = []

    def add_row(
        league: str,
        strategy: str,
        primary_metric: str,
        decision_rule: str,
        reason: str,
    ) -> None:
        match = research_alpha[research_alpha["Strategy"].eq(strategy)]
        if match.empty:
            rows.append(
                {
                    "League": league,
                    "Strategy": strategy,
                    "Primary_Metric": primary_metric,
                    "CAGR": np.nan,
                    "Sharpe": np.nan,
                    "Max_Drawdown": np.nan,
                    "Evidence_Class": "Diagnostic only",
                    "Final_Label": "Diagnostic Only",
                    "Decision_Rule": decision_rule,
                    "Reason": reason,
                }
            )
            return
        row = match.iloc[0]
        rows.append(
            {
                "League": league,
                "Strategy": strategy,
                "Primary_Metric": primary_metric,
                "CAGR": float(row["CAGR"]),
                "Sharpe": float(row["Sharpe"]),
                "Max_Drawdown": float(row["Max_Drawdown"]),
                "Evidence_Class": str(row["Evidence_Class"]),
                "Final_Label": str(row["Final_Label"]),
                "Decision_Rule": decision_rule,
                "Reason": reason,
            }
        )

    broad = (
        str(champion["best_cagr_model"])
        if bool(champion.get("replace_equal_weight_champion"))
        else "Equal Weight"
    )
    add_row(
        "Broad Default Champion",
        broad,
        "Robust default portfolio",
        "Replace Equal Weight only after CAGR, Sharpe, cost, subperiod, rolling and drawdown gates pass.",
        str(champion["decision"]),
    )
    add_row(
        "Annual Return Challenger",
        str(champion["best_cagr_model"]),
        "Highest OOS CAGR after costs",
        "Uses same walk-forward protocol and cost assumptions as Equal Weight.",
        "Annual-return status is separate from broad default champion status.",
    )
    add_row(
        "Risk-Adjusted Champion",
        str(champion["best_risk_adjusted_model"]),
        "Highest OOS Sharpe point estimate",
        "Promotion requires bootstrap Sharpe significance and cost/subperiod support.",
        "Point-estimate Sharpe is reported but not overclaimed.",
    )
    defensive = summary.sort_values("Max_Drawdown", ascending=False).iloc[0]
    add_row(
        "Defensive / Drawdown Champion",
        str(defensive["Strategy"]),
        "Least severe max drawdown",
        "Defensive status is evaluated separately from CAGR leadership.",
        "Drawdown leadership can be valuable even when CAGR is lower.",
    )
    for league in ["Research Candidate", "Diagnostic Only", "Rejected"]:
        members = research_alpha[research_alpha["Final_Label"].eq(league)][
            "Strategy"
        ].tolist()
        add_row(
            league,
            ", ".join(members) if members else "None",
            "League membership",
            "Strategies are grouped by evidence and promotion status.",
            "This row is a membership summary, not a new backtest.",
        )
    return pd.DataFrame(rows)


def _model_promotion_gate(
    research_alpha: pd.DataFrame,
    summary: pd.DataFrame,
) -> pd.DataFrame:
    ew = summary[summary["Strategy"].eq("Equal Weight")].iloc[0]
    rows = []
    for _, row in research_alpha.iterrows():
        max_drawdown_penalty = float(row["Max_Drawdown"] - ew["Max_Drawdown"])
        bootstrap_cagr_significant = bool(row["Bootstrap_CAGR_Diff_Lower"] > 0.0)
        bootstrap_sharpe_significant = bool(row["Bootstrap_Sharpe_Diff_Lower"] > 0.0)
        overfit_flag = row["PBO_or_Overfit_Flag"]
        decision, reason = _promotion_decision(
            row,
            bootstrap_cagr_significant,
            bootstrap_sharpe_significant,
            overfit_flag,
        )
        rows.append(
            {
                "Strategy": row["Strategy"],
                "Beats_EW_CAGR": bool(row["Beats_Equal_Weight_CAGR"]),
                "Beats_EW_Sharpe": bool(row["Beats_Equal_Weight_Sharpe"]),
                "Beats_EW_Calmar": bool(row["Beats_Equal_Weight_Calmar"]),
                "Survives_25bps": bool(row["Beats_Equal_Weight_After_25bps"]),
                "Survives_50bps": bool(row["Beats_Equal_Weight_After_50bps"]),
                "Subperiod_Win_Rate": float(row["Subperiod_Win_Rate"]),
                "Bootstrap_CAGR_Significant": bootstrap_cagr_significant,
                "Bootstrap_Sharpe_Significant": bootstrap_sharpe_significant,
                "Max_Drawdown_Penalty": max_drawdown_penalty,
                "Turnover_Level": _turnover_level(float(row["Turnover"])),
                "Overfit_Flag": overfit_flag,
                "Promotion_Decision": decision,
                "Reason": reason,
            }
        )
    return pd.DataFrame(rows)


def _promotion_decision(
    row: pd.Series,
    bootstrap_cagr_significant: bool,
    bootstrap_sharpe_significant: bool,
    overfit_flag: str,
) -> tuple[str, str]:
    strategy = str(row["Strategy"])
    if strategy == "Equal Weight":
        return (
            "Promote to Broad Default Champion",
            "Benchmark remains the broad default unless a challenger clears all gates.",
        )
    if str(row["Final_Label"]) == "Annual Return Challenger Winner":
        return (
            "Promote to Annual Return Challenger",
            "CAGR edge survives the implemented bootstrap CAGR and 25/50 bps cost gates.",
        )
    if str(row["Final_Label"]) == "Risk-Adjusted Champion":
        return (
            "Promote to Risk-Adjusted Champion",
            "Sharpe edge survives implemented significance and robustness checks.",
        )
    if str(row["Final_Label"]) == "Rejected" or str(overfit_flag).startswith(
        "Rejected:"
    ):
        return "Reject", "Rejected by cost, instability, or overfit-risk rule."
    if str(row["Final_Label"]) == "Research Candidate":
        return (
            "Keep as Research Candidate",
            "Positive evidence exists, but bootstrap, cost, subperiod or drawdown gates are not strong enough for promotion.",
        )
    if not bootstrap_cagr_significant and not bootstrap_sharpe_significant:
        return (
            "Keep as Diagnostic Only",
            "Implemented bootstrap intervals do not support promotion.",
        )
    return (
        "Keep as Research Candidate",
        "Some evidence exists, but promotion gates are not fully satisfied.",
    )


def _turnover_level(turnover: float) -> str:
    if turnover < 5.0:
        return "Low"
    if turnover < 15.0:
        return "Medium"
    return "High"


def _model_overfit_diagnostics(research_alpha: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in research_alpha.iterrows():
        cagr_crosses_zero = bool(
            row["Bootstrap_CAGR_Diff_Lower"] <= 0.0 <= row["Bootstrap_CAGR_Diff_Upper"]
        )
        sharpe_crosses_zero = bool(
            row["Bootstrap_Sharpe_Diff_Lower"]
            <= 0.0
            <= row["Bootstrap_Sharpe_Diff_Upper"]
        )
        risk_level = "Low"
        if str(row["Evidence_Class"]).startswith("Rejected:"):
            risk_level = "High"
        elif cagr_crosses_zero or sharpe_crosses_zero:
            risk_level = "Medium"
        rows.append(
            {
                "Strategy": row["Strategy"],
                "Bootstrap_CAGR_Crosses_Zero": cagr_crosses_zero,
                "Bootstrap_Sharpe_Crosses_Zero": sharpe_crosses_zero,
                "Subperiod_Win_Rate": row["Subperiod_Win_Rate"],
                "Turnover_Level": _turnover_level(float(row["Turnover"])),
                "PBO_or_Overfit_Flag": row["PBO_or_Overfit_Flag"],
                "Overfit_Risk_Level": risk_level,
                "Reason": (
                    "Lightweight overfit diagnostic; not a full PBO or White Reality Check."
                ),
            }
        )
    return pd.DataFrame(rows)


def _champion_summary(
    summary: pd.DataFrame,
    robustness: pd.DataFrame,
    cost_robustness: pd.DataFrame,
    subperiod: pd.DataFrame,
    rolling: pd.DataFrame,
    config: ChallengerConfig,
) -> Dict[str, object]:
    best_cagr = summary.sort_values("CAGR", ascending=False).iloc[0]
    best_sharpe = summary.sort_values("Sharpe", ascending=False).iloc[0]
    ew = summary[summary["Strategy"].eq("Equal Weight")].iloc[0]
    winning_challengers = summary[
        summary["Strategy"].ne("Equal Weight")
        & summary["Beats_Equal_Weight_CAGR"].astype(bool)
    ]
    replace_champion = False
    annual_return_challenger_wins = False
    reason = "Equal Weight remains annual-return champion under this walk-forward run."
    champion_diagnostics: Dict[str, object] = {}
    if not winning_challengers.empty:
        candidate = winning_challengers.sort_values("CAGR", ascending=False).iloc[0]
        robust = robustness[robustness["Strategy"].eq(candidate["Strategy"])]
        cost_25 = cost_robustness[
            cost_robustness["Strategy"].eq(candidate["Strategy"])
            & cost_robustness["Cost_Bps"].eq(25)
        ]
        cost_50 = cost_robustness[
            cost_robustness["Strategy"].eq(candidate["Strategy"])
            & cost_robustness["Cost_Bps"].eq(50)
        ]
        ci_positive = not robust.empty and float(robust.iloc[0]["CAGR_Diff_CI_5"]) > 0.0
        sharpe_ci_positive = (
            not robust.empty and float(robust.iloc[0]["Sharpe_Diff_CI_5"]) > 0.0
        )
        cost_25_survives = not cost_25.empty and bool(
            cost_25.iloc[0]["Beats_Equal_Weight_CAGR"]
        )
        cost_50_survives = not cost_50.empty and bool(
            cost_50.iloc[0]["Beats_Equal_Weight_CAGR"]
        )
        cost_survives = bool(cost_25_survives and cost_50_survives)
        candidate_subperiod = subperiod[subperiod["Strategy"].eq(candidate["Strategy"])]
        subperiod_count = int(candidate_subperiod["Subperiod"].nunique())
        subperiod_wins = int(
            candidate_subperiod["CAGR_Diff_vs_Equal_Weight"].gt(0.0).sum()
        )
        rolling_1y = rolling[
            rolling["Strategy"].eq(candidate["Strategy"]) & rolling["Window"].eq("1Y")
        ]["Rolling_CAGR_Diff_vs_Equal_Weight"]
        rolling_3y = rolling[
            rolling["Strategy"].eq(candidate["Strategy"]) & rolling["Window"].eq("3Y")
        ]["Rolling_CAGR_Diff_vs_Equal_Weight"]
        rolling_1y_positive = (
            float((rolling_1y > 0).mean()) if len(rolling_1y) else np.nan
        )
        rolling_3y_positive = (
            float((rolling_3y > 0).mean()) if len(rolling_3y) else np.nan
        )
        drawdown_penalty = float(candidate["Max_Drawdown"] - ew["Max_Drawdown"])
        annual_return_challenger_wins = bool(ci_positive and cost_survives)
        replace_champion = bool(
            annual_return_challenger_wins
            and sharpe_ci_positive
            and subperiod_count > 0
            and subperiod_wins >= int(np.ceil(subperiod_count / 2))
            and (pd.isna(rolling_1y_positive) or rolling_1y_positive >= 0.60)
            and (pd.isna(rolling_3y_positive) or rolling_3y_positive >= 0.60)
            and drawdown_penalty >= -0.10
        )
        champion_diagnostics = {
            "candidate": str(candidate["Strategy"]),
            "cagr_bootstrap_ci_positive": bool(ci_positive),
            "sharpe_bootstrap_ci_positive": bool(sharpe_ci_positive),
            "cost_25bps_survives": bool(cost_25_survives),
            "cost_50bps_survives": bool(cost_50_survives),
            "subperiod_wins": subperiod_wins,
            "subperiod_count": subperiod_count,
            "rolling_1y_positive_share": rolling_1y_positive,
            "rolling_3y_positive_share": rolling_3y_positive,
            "drawdown_penalty_vs_equal_weight": drawdown_penalty,
        }
        if replace_champion:
            reason = (
                f"{candidate['Strategy']} beats Equal Weight on OOS CAGR, bootstrap "
                "CAGR and Sharpe differences, 25/50 bps cost sensitivity, rolling "
                "relative performance and subperiod consistency."
            )
        elif annual_return_challenger_wins:
            reason = (
                f"{candidate['Strategy']} is the annual-return challenger winner: it "
                "beats Equal Weight on OOS CAGR, bootstrap CAGR difference, and 25/50 bps "
                "cost sensitivity. It does not replace Equal Weight as the broad "
                "champion because Sharpe/bootstrap, subperiod consistency, drawdown, "
                "or asset-universe sensitivity checks are not strong enough."
            )
        else:
            reason = (
                f"{candidate['Strategy']} beats Equal Weight on raw OOS CAGR, but "
                "robustness or cost checks are not strong enough for champion status."
            )
    return {
        "benchmark": "Equal Weight",
        "primary_metric": "out_of_sample_CAGR",
        "secondary_metrics": [
            "Sharpe",
            "Sortino",
            "Calmar",
            "Max_Drawdown",
            "Volatility",
            "Turnover",
            "Transaction_Cost_Drag",
            "Hit_Rate_By_Rebalance",
        ],
        "best_cagr_model": str(best_cagr["Strategy"]),
        "best_cagr": float(best_cagr["CAGR"]),
        "best_risk_adjusted_model": str(best_sharpe["Strategy"]),
        "best_sharpe": float(best_sharpe["Sharpe"]),
        "equal_weight_cagr": float(ew["CAGR"]),
        "equal_weight_sharpe": float(ew["Sharpe"]),
        "challengers_beating_equal_weight_cagr": winning_challengers[
            "Strategy"
        ].tolist(),
        "annual_return_challenger_wins": annual_return_challenger_wins,
        "replace_equal_weight_champion": replace_champion,
        "decision": reason,
        "champion_diagnostics": champion_diagnostics,
        "protocol": {
            "train_window": config.train_window,
            "rebal_frequency": config.rebal_frequency,
            "max_weight": config.max_weight,
            "transaction_cost_proportional": config.transaction_cost_proportional,
            "transaction_cost_spread": config.transaction_cost_spread,
            "no_look_ahead_rule": (
                "Each rebalance uses returns strictly before the traded day."
            ),
            "selection_warning": (
                "Any exploratory winner must be re-tested on future unseen data."
            ),
        },
        "lstm_not_included_reason": (
            "LSTM is excluded because this sprint requires a defensible benchmark "
            "comparison; the available sample is small for sequence models and a "
            "proper chronological retraining design would add complexity without "
            "clear evidence it improves over simple momentum."
        ),
        "black_litterman_lite_status": (
            "Skipped in this production path; a neutral-prior momentum-view variant "
            "would be too close to the implemented momentum challengers without a "
            "defensible external prior."
        ),
    }
