import inspect

import numpy as np
import pandas as pd

from project.research.global_portfolio_league import (
    REQUIRED_MODELS,
    build_portfolio_league,
)
from project.research.global_return_forecasting import build_return_forecasts
from project.research.global_stock_scoring import build_global_stock_scores


def test_portfolio_league_default_holdings_count_matches_canonical_contract():
    parameters = inspect.signature(build_portfolio_league).parameters
    assert parameters["max_assets"].default == 20


def _returns(n_assets: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    return pd.DataFrame(
        rng.normal(0.0006, 0.01, size=(260, n_assets)),
        index=pd.date_range("2024-01-01", periods=260, freq="B"),
        columns=[f"AST{i}" for i in range(n_assets)],
    )


def _universe(n_assets: int = 8, with_caps: bool = True) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"AST{i}" for i in range(n_assets)],
            "name": [f"Asset {i}" for i in range(n_assets)],
            "sleeve": ["global_equity_us"] * n_assets,
            "region": ["North America"] * n_assets,
            "country": ["United States"] * n_assets,
            "currency": ["USD"] * n_assets,
            "data_provider": ["unit"] * n_assets,
            "source": ["unit"] * n_assets,
            "source_method": ["public_provider_current"] * n_assets,
            "market_cap_usd": (
                np.arange(n_assets, 0, -1) * 1_000_000 if with_caps else np.nan
            ),
        }
    )


def test_portfolio_league_contains_required_models_and_valid_run_weights():
    returns = _returns()
    universe = _universe()
    scores = build_global_stock_scores(returns, universe, max_selected=6)
    forecasts = build_return_forecasts(returns, horizons={"12M": 252})
    league, weights, status = build_portfolio_league(
        returns,
        scores,
        forecasts,
        universe,
        max_assets=6,
        max_weight=0.25,
    )

    assert set(REQUIRED_MODELS) == set(league["model_name"])
    assert set(REQUIRED_MODELS) == set(status["model_name"])
    executable = league.loc[
        league["actual_status"].isin(["actually_run", "benchmark_only"])
    ]
    assert not executable.empty
    grouped = weights.loc[weights["model_name"].isin(executable["model_name"])].groupby(
        "model_name"
    )["weight"]
    assert np.allclose(grouped.sum().to_numpy(), 1.0)
    assert (grouped.min().to_numpy() >= -1e-10).all()
    assert weights["weight"].max() <= 0.25 + 1e-8


def test_portfolio_league_blocks_black_litterman_without_market_caps():
    returns = _returns()
    universe = _universe(with_caps=False)
    scores = build_global_stock_scores(returns, universe, max_selected=6)
    league, _weights, _status = build_portfolio_league(
        returns,
        scores,
        forecasts=None,
        metadata=universe,
        max_assets=6,
        max_weight=0.25,
    )

    black_litterman = league.loc[league["model_name"].eq("Black-Litterman")].iloc[0]
    forecast_enhanced = league.loc[
        league["model_name"].eq("Forecast-Enhanced Constrained Portfolio")
    ].iloc[0]
    assert black_litterman["actual_status"] == "blocked_by_data"
    assert forecast_enhanced["actual_status"] == "blocked_by_data"
