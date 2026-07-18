import numpy as np
import pandas as pd

from project.research.global_walk_forward import run_public_data_walk_forward


def _returns(n_assets: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(19)
    return pd.DataFrame(
        rng.normal(0.0005, 0.011, size=(330, n_assets)),
        index=pd.date_range("2024-01-01", periods=330, freq="B"),
        columns=[f"AST{i}" for i in range(n_assets)],
    )


def _universe(n_assets: int = 7) -> pd.DataFrame:
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
            "market_cap_usd": np.arange(n_assets, 0, -1) * 1_000_000,
        }
    )


def test_walk_forward_uses_chronological_windows_and_writes_core_tables():
    result = run_public_data_walk_forward(
        _returns(),
        _universe(),
        train_window_days=252,
        test_window_days=21,
        step_days=21,
        max_assets=6,
        max_weight=0.25,
        max_folds=2,
    )

    validation = result["validation"]
    summary = result["summary"]
    comparison = result["model_comparison"]
    weights = result["weights"]
    turnover = result["turnover"]

    assert summary["walk_forward_status"] == "completed_public_data_current_universe"
    assert not validation.empty
    assert (
        pd.to_datetime(validation["train_end"])
        .lt(pd.to_datetime(validation["test_start"]))
        .all()
    )
    assert "Equal Weight" in set(comparison["model_name"])
    assert not weights.empty
    assert not turnover.empty
    assert validation["limitation"].str.contains("not institutional PIT").all()


def test_equity_walk_forward_uses_equity_calendar_not_crypto_weekends():
    index = pd.date_range("2024-01-01", periods=430, freq="D")
    rng = np.random.default_rng(20)
    returns = pd.DataFrame(index=index)
    business = index.dayofweek < 5
    for ticker in ["EQ0", "EQ1", "EQ2"]:
        returns[ticker] = np.where(
            business,
            rng.normal(0.0004, 0.01, size=len(index)),
            np.nan,
        )
    returns["BTC-USD"] = rng.normal(0.0005, 0.02, size=len(index))
    universe = pd.concat(
        [
            _universe(3).assign(ticker=["EQ0", "EQ1", "EQ2"]),
            pd.DataFrame(
                {
                    "ticker": ["BTC-USD"],
                    "name": ["Bitcoin"],
                    "sleeve": ["crypto"],
                    "region": ["Global"],
                    "country": ["Global"],
                    "currency": ["USD"],
                    "data_provider": ["unit"],
                    "source": ["unit"],
                    "source_method": ["public_provider_current"],
                    "market_cap_usd": [1_000_000],
                }
            ),
        ],
        ignore_index=True,
    )

    result = run_public_data_walk_forward(
        returns,
        universe,
        train_window_days=252,
        test_window_days=21,
        step_days=21,
        max_assets=3,
        max_weight=0.50,
        max_folds=1,
        default_scope="equity_only",
        include_crypto=False,
    )

    assert result["summary"]["walk_forward_status"] == (
        "completed_public_data_current_universe"
    )
    assert int(result["window_summary"]["selected_count"].iloc[0]) == 3
