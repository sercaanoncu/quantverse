import numpy as np
import pandas as pd
import pytest

from project.simulation.monte_carlo import MonteCarloSimulator
from project.simulation.stress_testing import StressTester


def _returns(rows=80):
    rng = np.random.default_rng(101)
    return pd.DataFrame(
        rng.normal(0.0004, 0.012, size=(rows, 3)),
        index=pd.bdate_range("2024-01-02", periods=rows),
        columns=["A", "B", "C"],
    )


def test_monte_carlo_rejects_nonzero_weight_without_return_series():
    with pytest.raises(ValueError, match="missing from returns"):
        MonteCarloSimulator(
            _returns(),
            pd.Series({"A": 0.4, "B": 0.3, "C": 0.2, "MISSING": 0.1}),
            n_sims=10,
            horizon_days=5,
        )


def test_parametric_monte_carlo_preserves_positive_wealth():
    simulator = MonteCarloSimulator(
        _returns(),
        pd.Series({"A": 0.4, "B": 0.3, "C": 0.3}),
        n_sims=25,
        horizon_days=10,
        seed=9,
    )

    normal = simulator.simulate_normal()
    student = simulator.simulate_student_t(df=5)

    assert (normal["wealth_paths"] > 0).all()
    assert (student["wealth_paths"] > 0).all()
    assert normal["calibration_space"] == "log_returns_for_parametric_methods"
    assert normal["tail_risk_convention"] == "positive_terminal_loss_magnitude"


def test_bootstrap_accepts_history_length_block_and_is_reproducible():
    returns = _returns(rows=20)
    weights = pd.Series({"A": 0.4, "B": 0.3, "C": 0.3})
    first = MonteCarloSimulator(
        returns,
        weights,
        n_sims=5,
        horizon_days=5,
        seed=5,
    ).simulate_bootstrap(block_size=20)
    second = MonteCarloSimulator(
        returns,
        weights,
        n_sims=5,
        horizon_days=5,
        seed=5,
    ).simulate_bootstrap(block_size=20)

    np.testing.assert_allclose(first["wealth_paths"], second["wealth_paths"])


def test_stress_tester_rejects_incomplete_weight_mapping():
    returns = _returns()
    with pytest.raises(ValueError, match="missing from returns"):
        StressTester(
            returns,
            (1 + returns).cumprod(),
            pd.Series({"A": 0.5, "B": 0.2, "C": 0.2, "MISSING": 0.1}),
            {ticker: "equity" for ticker in returns.columns},
        )
