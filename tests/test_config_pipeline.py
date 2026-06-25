import pandas as pd
import pytest
import yaml
from pathlib import Path

from project.config import load_config
from project.data_pipeline.processor import DataProcessor
from project.data_pipeline.universe import AssetUniverse
from project.pipeline import (
    PipelineConfig,
    _portable_path,
    _resolve_risk_free_rate,
    _write_portfolio_artifacts,
)


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
    assert pipeline_config.var_exception_alpha == pytest.approx(0.05)
    assert pipeline_config.bootstrap_samples > 0


def test_portable_metadata_path_does_not_expose_local_absolute_root():
    config_path = Path("configs/base.yaml").resolve()

    assert _portable_path(str(config_path)) == "configs/base.yaml"


def test_invalid_config_rejects_duplicate_tickers(tmp_path):
    config = load_config("configs/base.yaml")
    raw = dict(config.raw)
    raw["universe"] = {
        **raw["universe"],
        "signals": {
            **raw["universe"]["signals"],
            "tickers": raw["universe"]["signals"]["tickers"] + ["XLK"],
        },
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate tickers"):
        load_config(path)


def test_invalid_config_rejects_bad_var_alpha(tmp_path):
    config = load_config("configs/base.yaml")
    raw = dict(config.raw)
    raw["validation"] = {**raw.get("validation", {}), "var_exception_alpha": 0.75}
    path = tmp_path / "bad_alpha.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="var_exception_alpha"):
        load_config(path)


def test_risk_free_fallback_is_explicit_when_fetcher_fails():
    class FailingFetcher:
        def fetch_risk_free_rate(self, proxy):
            raise RuntimeError(f"provider unavailable for {proxy}")

    config = PipelineConfig(fallback_risk_free_rate=0.031, risk_free_proxy="^IRX")

    rate, metadata = _resolve_risk_free_rate(FailingFetcher(), config)

    assert rate == pytest.approx(0.031)
    assert metadata["source"] == "fallback"
    assert metadata["proxy"] == "^IRX"
    assert "provider unavailable" in metadata["reason"]


def test_data_cleaning_drops_low_coverage_not_low_return():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    prices = pd.DataFrame(
        {
            "LOW_RETURN": [100, 99, 98, 97, 96, 95, 94, 93, 92, 91],
            "LOW_COVERAGE": [100, None, None, None, None, None, None, None, None, 101],
        },
        index=dates,
    )

    processor = DataProcessor(prices)
    cleaned = processor.clean(min_history_pct=0.8, fill_method="none")

    assert "LOW_RETURN" in cleaned.columns
    assert "LOW_COVERAGE" not in cleaned.columns
    assert processor._cleaning_report["dropped_low_coverage"] == ["LOW_COVERAGE"]


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


def test_portfolio_holdings_schema_and_long_only_contract(tmp_path):
    returns = pd.DataFrame(
        {"AAA": [0.01, 0.02], "BBB": [0.00, 0.01]},
        index=pd.date_range("2024-01-01", periods=2, freq="B"),
    )
    portfolios = {
        "LongOnly": {
            "weights": pd.Series({"AAA": 0.75, "BBB": 0.25}),
            "return": 0.10,
            "volatility": 0.12,
            "sharpe": 0.50,
            "n_assets": 2,
            "max_weight": 0.75,
            "concentration": 0.625,
        }
    }
    class_map = {"AAA": "equity", "BBB": "fixed_income"}

    weights, _ = _write_portfolio_artifacts(tmp_path, returns, portfolios, class_map)
    holdings = pd.read_csv(tmp_path / "portfolio_holdings_long.csv")

    assert {"Portfolio", "Ticker", "Asset_Class", "Weight", "Weight_Percent"}.issubset(
        holdings.columns
    )
    assert (weights["LongOnly"] >= 0).all()
    assert weights["LongOnly"].max() <= 0.75
