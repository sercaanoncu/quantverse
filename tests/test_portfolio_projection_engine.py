import numpy as np
import pandas as pd

from project.projection.portfolio_projection import (
    correlation_diagnostics,
    estimator_comparison,
    monte_carlo_projection,
    stress_test_portfolio,
)
from project.projection.return_forecasting import (
    downside_roc,
    forecast_asset_returns,
    forecast_model_league,
    optional_model_status,
)


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(12)
    return pd.DataFrame(
        rng.normal(0.0004, 0.01, size=(180, 4)),
        index=pd.date_range("2024-01-01", periods=180, freq="B"),
        columns=["AAA", "BBB", "CCC", "DDD"],
    )


def test_forecast_models_and_optional_status_are_schema_stable():
    forecasts = forecast_asset_returns(_returns(), horizons_months=[1], random_state=7)
    league = forecast_model_league(forecasts)
    status = optional_model_status()

    assert {
        "Ticker",
        "Horizon_Months",
        "Model",
        "Forecast_Return",
        "Task_Type",
    }.issubset(forecasts.columns)
    assert {"Model", "Status", "Task_Type", "Mean_Forecast"}.issubset(league.columns)
    assert {"xgboost", "lightgbm", "tensorflow"}.issubset(status)


def test_roc_is_classification_only_and_quant_outputs_have_stable_schema():
    returns = _returns()
    weights = pd.Series(0.25, index=returns.columns)
    roc = downside_roc(returns)
    projection = monte_carlo_projection(
        returns,
        weights,
        horizons_months=[1, 3],
        n_simulations=50,
        random_state=4,
    )
    diagnostics = correlation_diagnostics(returns)
    estimators = estimator_comparison(returns)
    metadata = pd.DataFrame(
        {
            "ticker": returns.columns,
            "sleeve": [
                "global_equity_us",
                "crypto",
                "commodity_real_assets",
                "defensive_bonds_cash",
            ],
            "currency": ["USD", "USD", "USD", "EUR"],
        }
    )
    stress = stress_test_portfolio(weights, metadata)

    assert set(roc["Task_Type"].dropna().unique()).issubset(
        {"classification_downside_event"}
    )
    assert {"VaR_95", "CVaR_95", "Probability_Of_Loss"}.issubset(projection.columns)
    assert "correlation_matrix" in diagnostics
    assert {"Estimator", "Status"}.issubset(estimators.columns)
    assert {"Scenario", "Portfolio_Impact"}.issubset(stress.columns)
