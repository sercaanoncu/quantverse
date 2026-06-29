"""Global portfolio simulation helpers."""

from __future__ import annotations

import pandas as pd

from project.projection.portfolio_projection import (
    monte_carlo_projection,
    stress_test_portfolio,
)


def run_global_simulations(
    returns: pd.DataFrame,
    weights: pd.Series,
    metadata: pd.DataFrame,
    horizons_months: list[int],
    n_simulations: int,
    random_state: int,
) -> dict[str, pd.DataFrame]:
    """Run Monte Carlo, scenario and stress outputs for a global candidate."""
    projection = monte_carlo_projection(
        returns,
        weights,
        horizons_months=horizons_months,
        n_simulations=n_simulations,
        random_state=random_state,
    )
    stress = stress_test_portfolio(weights, metadata)
    scenario = stress.rename(
        columns={"Portfolio_Impact": "Scenario_Portfolio_Impact"}
    ).assign(Scenario_Type="stylized_global")
    return {
        "monte_carlo": projection,
        "scenario_analysis": scenario,
        "stress_tests": stress,
    }
