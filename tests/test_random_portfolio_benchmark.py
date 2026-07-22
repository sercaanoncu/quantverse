import numpy as np
import pandas as pd
import pytest

from project.research.global_model_selection import (
    build_random_percentile_report,
    simulate_constrained_random_distribution,
)


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(5)
    return pd.DataFrame(
        rng.normal(0.0005, 0.01, size=(80, 6)),
        columns=[f"A{i}" for i in range(6)],
    )


def test_random_portfolios_sum_to_one_and_respect_max_weight():
    randoms = simulate_constrained_random_distribution(
        _returns(), n_portfolios=25, max_weight=0.30, random_state=7
    )

    assert np.allclose(randoms["weight_sum"], 1.0)
    assert (randoms["max_weight_observed"] <= 0.30 + 1e-10).all()
    assert set(randoms["sampling_method"]) == {
        "iid_uniform_raw_scores_projected_to_capped_simplex"
    }
    assert set(randoms["benchmark_scope"]) == {"full_sample_static_weights_diagnostic"}


def test_random_portfolio_simulation_is_reproducible():
    first = simulate_constrained_random_distribution(
        _returns(), n_portfolios=10, max_weight=0.30, random_state=9
    )
    second = simulate_constrained_random_distribution(
        _returns(), n_portfolios=10, max_weight=0.30, random_state=9
    )

    pd.testing.assert_frame_equal(first, second)


def test_percentile_calculation_known_case_and_fields_exist():
    league = pd.DataFrame(
        [
            {
                "model_name": "Candidate",
                "annualized_return": 0.20,
                "volatility": 0.10,
                "sharpe": 1.0,
                "max_drawdown": -0.10,
                "cvar_95": -0.02,
            }
        ]
    )
    randoms = pd.DataFrame(
        {
            "annualized_return": [0.10, 0.20, 0.30],
            "volatility": [0.20, 0.10, 0.05],
            "sharpe": [0.0, 1.0, 2.0],
            "max_drawdown": [-0.20, -0.10, -0.05],
            "cvar_95": [-0.05, -0.02, -0.01],
        }
    )

    report = build_random_percentile_report(league, randoms).iloc[0]

    assert report["sharpe_percentile"] == pytest.approx(2 / 3)
    assert report["volatility_percentile"] == pytest.approx(2 / 3)
    assert {
        "return_percentile",
        "volatility_percentile",
        "sharpe_percentile",
        "max_drawdown_percentile",
        "cvar_percentile",
    }.issubset(report.index)
