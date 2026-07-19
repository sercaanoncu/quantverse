import numpy as np
import pandas as pd

from project.data_pipeline.global_returns import normalize_returns_to_base
from project.data_pipeline.security_universe import REQUIRED_UNIVERSE_COLUMNS
from project.research.global_master_portfolio import run_master_portfolio_research


def _universe(rows: list[dict[str, object]]) -> pd.DataFrame:
    defaults = {
        "name": "Asset",
        "sleeve": "global_equity_us",
        "region": "Global",
        "country": "Test",
        "exchange": "TEST",
        "asset_type": "equity",
        "sector": "",
        "industry": "",
        "market_cap_usd": 1000,
        "market_cap_rank": 1,
        "as_of_date": "2026-07-01",
        "source": "unit",
        "data_provider": "unit",
        "investable": True,
        "benchmark_only": False,
        "signal_only": False,
        "include": True,
        "proxy_type": "direct_listing",
        "notes": "unit",
    }
    completed = []
    for idx, row in enumerate(rows, start=1):
        merged = {**defaults, **row}
        merged["market_cap_rank"] = idx
        completed.append(merged)
    return pd.DataFrame(completed, columns=REQUIRED_UNIVERSE_COLUMNS)


def test_usd_asset_remains_unchanged_after_fx_normalization():
    dates = pd.date_range("2024-01-01", periods=3)
    local = pd.DataFrame({"AAA": [np.nan, 0.01, -0.02]}, index=dates)
    universe = _universe([{"ticker": "AAA", "currency": "USD"}])

    usd, report, _ = normalize_returns_to_base(local, universe, pd.DataFrame())

    pd.testing.assert_series_equal(usd["AAA"], local["AAA"], check_names=False)
    assert (
        report.loc[report["ticker"].eq("AAA"), "fx_normalization_status"].iloc[0]
        == "native_base"
    )


def test_eur_asset_uses_simple_return_fx_compounding():
    dates = pd.date_range("2024-01-01", periods=2)
    local = pd.DataFrame({"EUR_ASSET": [np.nan, 0.10]}, index=dates)
    fx_prices = pd.DataFrame({"EURUSD=X": [1.00, 1.05]}, index=dates)
    universe = _universe([{"ticker": "EUR_ASSET", "currency": "EUR"}])

    usd, report, _ = normalize_returns_to_base(local, universe, fx_prices)

    assert np.isclose(usd.loc[dates[-1], "EUR_ASSET"], 0.155)
    assert (
        report.loc[report["ticker"].eq("EUR_ASSET"), "fx_normalization_status"].iloc[0]
        == "fx_normalized"
    )


def test_inverted_fx_quote_direction_is_respected():
    dates = pd.date_range("2024-01-01", periods=2)
    local = pd.DataFrame({"JPY_ASSET": [np.nan, 0.10]}, index=dates)
    fx_prices = pd.DataFrame({"JPY=X": [100.0, 95.0]}, index=dates)
    universe = _universe([{"ticker": "JPY_ASSET", "currency": "JPY"}])

    usd, report, _ = normalize_returns_to_base(local, universe, fx_prices)

    expected_fx_return = (1 / 95.0) / (1 / 100.0) - 1
    expected = (1 + 0.10) * (1 + expected_fx_return) - 1
    assert np.isclose(usd.loc[dates[-1], "JPY_ASSET"], expected)
    assert bool(
        report.loc[report["ticker"].eq("JPY_ASSET"), "inversion_required"].iloc[0]
    )


def test_missing_fx_series_marks_asset_fx_missing():
    dates = pd.date_range("2024-01-01", periods=2)
    local = pd.DataFrame({"EUR_ASSET": [np.nan, 0.10]}, index=dates)
    universe = _universe([{"ticker": "EUR_ASSET", "currency": "EUR"}])

    usd, report, coverage = normalize_returns_to_base(local, universe, pd.DataFrame())

    assert usd["EUR_ASSET"].isna().all()
    row = report.loc[report["ticker"].eq("EUR_ASSET")].iloc[0]
    assert row["fx_normalization_status"] == "fx_missing"
    assert row["fx_ticker"] == "EURUSD=X"
    assert "missing" in str(row["warning"]).lower()
    assert (
        coverage.loc[coverage["currency"].eq("EUR"), "coverage_status"].iloc[0]
        == "missing"
    )


def test_calendar_mismatch_is_reported_without_long_silent_fill():
    dates = pd.date_range("2024-01-01", periods=4)
    local = pd.DataFrame({"GBP_ASSET": [np.nan, 0.02, 0.03, 0.04]}, index=dates)
    fx_prices = pd.DataFrame(
        {"GBPUSD=X": [1.20, 1.26]},
        index=pd.to_datetime(["2024-01-01", "2024-01-04"]),
    )
    universe = _universe([{"ticker": "GBP_ASSET", "currency": "GBP"}])

    _, report, _ = normalize_returns_to_base(
        local,
        universe,
        fx_prices,
        max_forward_fill_days=0,
    )

    row = report.loc[report["ticker"].eq("GBP_ASSET")].iloc[0]
    assert row["fx_normalization_status"] == "fx_normalized"
    assert int(row["fx_missing_dates"]) > 0


def test_signal_only_assets_do_not_require_investable_fx_treatment():
    dates = pd.date_range("2024-01-01", periods=2)
    local = pd.DataFrame({"EUR_SIGNAL": [np.nan, 0.10]}, index=dates)
    universe = _universe(
        [
            {
                "ticker": "EUR_SIGNAL",
                "currency": "EUR",
                "investable": False,
                "signal_only": True,
            }
        ]
    )

    _, report, _ = normalize_returns_to_base(local, universe, pd.DataFrame())

    assert (
        report.loc[report["ticker"].eq("EUR_SIGNAL"), "fx_normalization_status"].iloc[0]
        == "signal_only"
    )


def test_missing_fx_blocks_global_master_promotion_for_selected_non_usd_asset():
    dates = pd.date_range("2024-01-01", periods=80, freq="B")
    returns = pd.DataFrame(
        {
            "USD_A": np.repeat(0.001, len(dates)),
            "EUR_A": np.repeat(0.0012, len(dates)),
            "USD_B": np.repeat(0.0008, len(dates)),
            "USD_C": np.repeat(0.0007, len(dates)),
            "BTC_A": np.repeat(0.0006, len(dates)),
        },
        index=dates,
    )
    metadata = _universe(
        [
            {"ticker": "USD_A", "currency": "USD", "sleeve": "global_equity_us"},
            {"ticker": "EUR_A", "currency": "EUR", "sleeve": "global_equity_europe"},
            {"ticker": "USD_B", "currency": "USD", "sleeve": "defensive_bonds_cash"},
            {"ticker": "USD_C", "currency": "USD", "sleeve": "commodity_real_assets"},
            {"ticker": "BTC_A", "currency": "USD", "sleeve": "crypto_top100"},
        ]
    )
    fx_report = pd.DataFrame(
        [
            {"ticker": "USD_A", "fx_normalization_status": "native_base"},
            {"ticker": "EUR_A", "fx_normalization_status": "fx_missing"},
            {"ticker": "USD_B", "fx_normalization_status": "native_base"},
            {"ticker": "USD_C", "fx_normalization_status": "native_base"},
            {"ticker": "BTC_A", "fx_normalization_status": "native_base"},
        ]
    )

    result = run_master_portfolio_research(
        returns,
        metadata,
        min_holdings=5,
        max_holdings=5,
        max_weight=0.40,
        n_random_portfolios=10,
        random_state=3,
        portfolio_constraints={
            "max_region_weight": 1.0,
            "max_cluster_weight": 1.0,
            "max_defensive_weight": 0.40,
            "max_crypto_weight": 0.40,
            "max_commodity_weight": 0.40,
        },
        fx_report=fx_report,
    )

    decision = result["decision_summary"]
    assert decision["promotion_decision"] == "not promoted"
    assert decision["fx_normalization_status"] == "local_currency_mixed_not_promotable"
    assert "FX normalization is insufficient" in decision["reason"]
