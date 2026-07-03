import numpy as np
import pandas as pd

from project.data_pipeline.security_universe import REQUIRED_UNIVERSE_COLUMNS
from project.projection.global_forecast_engine import run_global_forecasts
from project.projection.global_simulation_engine import run_global_simulations
from project.research.global_master_portfolio import run_master_portfolio_research
from project.research.global_statistical_diagnostics import diagnostics_bundle
from project.research.model_applicability import model_applicability_matrix


def _returns(n_assets: int = 10, periods: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(77)
    base = rng.normal(0.0004, 0.009, size=(periods, n_assets))
    base[:, 0] += 0.0002
    return pd.DataFrame(
        base,
        index=pd.date_range("2024-01-01", periods=periods, freq="B"),
        columns=[f"AST{i}" for i in range(n_assets)],
    )


def _metadata(n_assets: int = 10) -> pd.DataFrame:
    sleeves = [
        "global_equity_nasdaq",
        "global_equity_nyse",
        "global_equity_uk",
        "global_equity_japan",
        "global_equity_turkey",
        "global_equity_china_hk",
        "defensive_bonds_cash",
        "defensive_bonds_cash",
        "crypto_top100",
        "commodity_real_assets",
    ]
    regions = [
        "North America",
        "North America",
        "Europe",
        "Asia",
        "Europe / Middle East",
        "Asia",
        "North America",
        "North America",
        "Global",
        "Global",
    ]
    currencies = ["USD", "USD", "GBP", "JPY", "TRY", "HKD", "USD", "USD", "USD", "USD"]
    rows = []
    for idx in range(n_assets):
        rows.append(
            {
                "ticker": f"AST{idx}",
                "name": f"Asset {idx}",
                "sleeve": sleeves[idx % len(sleeves)],
                "region": regions[idx % len(regions)],
                "country": "Test",
                "exchange": "TEST",
                "currency": currencies[idx % len(currencies)],
                "asset_type": (
                    "equity" if sleeves[idx].startswith("global_equity") else "proxy"
                ),
                "sector": "",
                "industry": "",
                "market_cap_usd": 1000 - idx,
                "market_cap_rank": idx + 1,
                "as_of_date": "2026-06-30",
                "source": "unit",
                "data_provider": "unit",
                "investable": True,
                "benchmark_only": False,
                "signal_only": False,
                "include": True,
                "proxy_type": "direct_listing",
                "notes": "unit",
            }
        )
    return pd.DataFrame(rows, columns=REQUIRED_UNIVERSE_COLUMNS)


def test_global_diagnostics_bundle_has_expected_output_schemas():
    bundle = diagnostics_bundle(_returns(n_assets=5, periods=70))

    assert {
        "summary_statistics",
        "normality_tests",
        "correlation_matrix",
        "pca_summary",
        "covariance_estimator_comparison",
        "cluster_membership",
    }.issubset(bundle)
    assert {"ticker", "annualized_return", "annualized_volatility"}.issubset(
        bundle["summary_statistics"].columns
    )
    assert {"sample_covariance", "ledoit_wolf_shrinkage", "ewma_covariance"}.issubset(
        set(bundle["covariance_estimator_comparison"]["estimator"])
    )
    assert bundle["cluster_membership"]["ticker"].nunique() == 5


def test_model_applicability_keeps_deep_and_rl_models_out_of_production_allocation():
    matrix = model_applicability_matrix().set_index("model")

    assert matrix.loc["Black-Litterman", "current_status"] == "blocked"
    assert matrix.loc["Reinforcement Learning", "current_status"] == "not_appropriate"
    assert "small sample" in matrix.loc["LSTM/RNN optional", "when_not_appropriate"]
    assert (
        "direct buy signal" in matrix.loc["Logistic Regression", "when_not_appropriate"]
    )


def test_master_portfolio_blocks_promotion_when_fx_is_not_normalized():
    result = run_master_portfolio_research(
        _returns(),
        _metadata(),
        min_holdings=8,
        max_holdings=10,
        max_weight=0.25,
        n_random_portfolios=20,
        random_state=11,
        portfolio_constraints={
            "max_region_weight": 0.60,
            "max_cluster_weight": 0.60,
            "max_defensive_weight": 0.35,
            "max_crypto_weight": 0.15,
            "max_commodity_weight": 0.20,
        },
    )

    decision = result["decision_summary"]
    weights = result["candidate_weights"]
    final_model = decision["final_model"]
    final_audit = (
        result["constraint_audit"]
        .loc[result["constraint_audit"]["Model"].eq(final_model)]
        .iloc[0]
    )
    final_model_row = (
        result["model_comparison"]
        .loc[result["model_comparison"]["Model"].eq(final_model)]
        .iloc[0]
    )
    equal_weight_comparison = result["equal_weight_comparison"].iloc[0]

    assert decision["promotion_decision"] == "not promoted"
    assert decision["fx_normalization_status"] == "local_currency_mixed_not_promotable"
    assert "FX normalization is insufficient" in decision["reason"]
    assert np.allclose(weights.groupby("Model")["Weight"].sum().to_numpy(), 1.0)
    assert bool(final_audit["All_Constraints_Pass"])
    assert equal_weight_comparison["Candidate_CAGR"] == final_model_row["CAGR"]


def test_global_forecasts_and_simulations_emit_required_artifacts():
    returns = _returns(n_assets=5, periods=90)
    weights = pd.Series(0.2, index=returns.columns)
    metadata = _metadata(n_assets=5)

    forecasts = run_global_forecasts(returns, horizons_months=[1], random_state=9)
    simulations = run_global_simulations(
        returns,
        weights,
        metadata,
        horizons_months=[1],
        n_simulations=50,
        random_state=9,
    )

    assert {"Model", "Status"}.issubset(forecasts["regression_metrics"].columns)
    assert {"Model", "ROC_AUC", "Status"}.issubset(forecasts["roc_auc"].columns)
    assert {"Horizon_Months", "P05_Return", "Median_Return", "P95_Return"}.issubset(
        simulations["monte_carlo"].columns
    )
    assert {"Scenario", "Portfolio_Impact"}.issubset(
        simulations["stress_tests"].columns
    )
