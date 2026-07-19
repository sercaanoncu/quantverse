import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from project.research.global_portfolio_league import (
    REQUIRED_MODELS,
    build_portfolio_league,
)
from project.research.global_stock_scoring import build_global_stock_scores

import scripts.run_quantverse_v2_demo as demo

VALID_STATUSES = {
    "actually_run",
    "benchmark_only",
    "diagnostic_only",
    "blocked_by_data",
    "blocked_by_implementation",
    "future_candidate",
}


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(22)
    base = rng.normal(0.0004, 0.01, size=(260, 4))
    base[:, 0] = rng.normal(0.0002, 0.003, size=260)
    base[:, 1] = base[:, 0] * 0.8 + rng.normal(0.0, 0.004, size=260)
    return pd.DataFrame(
        base,
        index=pd.date_range("2024-01-01", periods=260, freq="B"),
        columns=["LOW", "CORR", "MID", "HIGH"],
    )


def _universe(with_caps: bool = True) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["LOW", "CORR", "MID", "HIGH"],
            "name": ["LOW", "CORR", "MID", "HIGH"],
            "sleeve": ["global_equity_us"] * 4,
            "region": ["North America"] * 4,
            "country": ["United States"] * 4,
            "currency": ["USD"] * 4,
            "data_provider": ["unit"] * 4,
            "source": ["unit"] * 4,
            "source_method": ["public_provider_current"] * 4,
            "market_cap_usd": [4, 3, 2, 1] if with_caps else [np.nan] * 4,
        }
    )


def test_model_league_statuses_final_model_and_gmv_variance_are_valid():
    returns = _returns()
    scores = build_global_stock_scores(returns, _universe(), max_selected=4)
    league, weights, _status = build_portfolio_league(
        returns,
        scores,
        forecasts=None,
        metadata=_universe(),
        max_assets=4,
        max_weight=0.80,
        risk_free_rate_annual=0.03,
        risk_free_policy="unit_test_fixed_rate",
    )

    assert set(league["model_name"]) == set(REQUIRED_MODELS)
    assert set(league["actual_status"]).issubset(VALID_STATUSES)
    assert set(league["risk_free_rate_annual"]) == {0.03}
    assert set(league["risk_free_policy"]) == {"unit_test_fixed_rate"}

    final = demo._final_model(league)
    final_status = league.loc[league["model_name"].eq(final), "actual_status"].iloc[0]
    assert final_status in {"actually_run", "benchmark_only"}

    pivot = weights.pivot(index="ticker", columns="model_name", values="weight").fillna(
        0.0
    )
    matrix = returns[pivot.index].dropna(how="any")
    cov = LedoitWolf().fit(matrix.to_numpy(dtype=float)).covariance_
    ew = pivot["Equal Weight"].to_numpy()
    gmv = pivot["GMV"].to_numpy()
    assert float(gmv @ cov @ gmv) <= float(ew @ cov @ ew) + 1e-10

    policy = league.loc[league["model_name"].eq("Policy Constrained")].iloc[0]
    assert policy["actual_status"] == "diagnostic_only"
    assert not bool(policy["promotion_eligible"])


def test_black_litterman_cannot_be_promoted_without_market_cap_priors():
    returns = _returns()
    universe = _universe(with_caps=False)
    scores = build_global_stock_scores(returns, universe, max_selected=4)
    league, _weights, _status = build_portfolio_league(
        returns,
        scores,
        forecasts=None,
        metadata=universe,
        max_assets=4,
        max_weight=0.80,
    )

    row = league.loc[league["model_name"].eq("Black-Litterman")].iloc[0]
    assert row["actual_status"] == "blocked_by_data"
    assert not bool(row["promotion_eligible"])
