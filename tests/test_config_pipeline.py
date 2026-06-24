import pandas as pd
import pytest

from project.config import load_config
from project.data_pipeline.universe import AssetUniverse
from project.pipeline import PipelineConfig, _write_portfolio_artifacts


def test_canonical_config_loads_and_separates_signals():
    config = load_config("configs/base.yaml")
    all_tickers = config.investable_tickers + config.signal_tickers

    assert len(all_tickers) == len(set(all_tickers))
    assert "^IRX" in config.signal_tickers
    assert "^IRX" not in config.investable_tickers
    assert "DX-Y.NYB" in config.signal_tickers

    universe = AssetUniverse.from_config(str(config.path))
    assert "^IRX" in universe.signal_tickers
    assert "^IRX" not in universe.investable_tickers


def test_pipeline_config_is_derived_from_canonical_yaml():
    pipeline_config = PipelineConfig.from_yaml("configs/base.yaml")

    assert pipeline_config.config_path.endswith(
        "configs\\base.yaml"
    ) or pipeline_config.config_path.endswith("configs/base.yaml")
    assert pipeline_config.risk_free_proxy == "^IRX"
    assert pipeline_config.fallback_risk_free_rate == pytest.approx(0.04)
    assert pipeline_config.max_position_weight == pytest.approx(0.25)
    assert pipeline_config.transaction_cost_proportional == pytest.approx(0.001)
    assert pipeline_config.transaction_cost_spread == pytest.approx(0.0005)


def test_portfolio_artifacts_sum_to_one_and_exclude_signals(tmp_path):
    returns = pd.DataFrame(
        {"AAA": [0.01, 0.02], "BBB": [0.00, 0.01]},
        index=pd.date_range("2024-01-01", periods=2, freq="B"),
    )
    portfolios = {
        "Example": {
            "weights": pd.Series({"AAA": 0.60, "BBB": 0.40}),
            "return": 0.10,
            "volatility": 0.12,
            "sharpe": 0.50,
            "n_assets": 2,
            "max_weight": 0.60,
            "concentration": 0.52,
        }
    }
    class_map = {"AAA": "equity", "BBB": "fixed_income", "^VIX": "signals"}

    weights, _ = _write_portfolio_artifacts(tmp_path, returns, portfolios, class_map)
    holdings = pd.read_csv(tmp_path / "portfolio_holdings_long.csv")

    assert "^VIX" not in weights.index
    assert weights["Example"].sum() == pytest.approx(1.0)
    assert holdings.groupby("Portfolio")["Weight"].sum().iloc[0] == pytest.approx(1.0)
