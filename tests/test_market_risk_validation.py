import numpy as np
import pandas as pd

from project.risk.validation import var_exception_tests


def test_var_exception_tests_reports_exception_counts():
    returns = pd.DataFrame(
        {
            "Strategy": [
                *([0.001] * 252),
                -0.05,
                *([0.001] * 20),
                -0.06,
                *([0.001] * 20),
            ]
        },
        index=pd.date_range("2020-01-01", periods=294, freq="B"),
    )

    result = var_exception_tests(returns, alpha=0.05, lookback=252)

    assert len(result) == 1
    assert result.loc[0, "Strategy"] == "Strategy"
    assert result.loc[0, "Observations"] > 0
    assert result.loc[0, "Exceptions"] >= 1
    assert np.isfinite(result.loc[0, "Kupiec_LR"])
    assert result.loc[0, "Kupiec_Result"] in {
        "Reject at 5%",
        "Do not reject at 5%",
    }


def test_var_exception_tests_handles_insufficient_history():
    returns = pd.DataFrame(
        {"Strategy": [0.001, -0.002]},
        index=pd.date_range("2024-01-01", periods=2, freq="B"),
    )

    result = var_exception_tests(returns, alpha=0.05, lookback=252)

    assert result.loc[0, "Kupiec_Result"] == "Inconclusive"
    assert "Insufficient" in result.loc[0, "Interpretation"]


def test_var_exception_expected_count_matches_alpha_and_observations():
    returns = pd.DataFrame(
        {"Strategy": [0.001, -0.002, 0.003, -0.004, 0.002, -0.001] * 60},
        index=pd.date_range("2021-01-01", periods=360, freq="B"),
    )

    result = var_exception_tests(returns, alpha=0.10, lookback=30)
    row = result.iloc[0]

    assert row["Expected_Exceptions"] == row["Observations"] * 0.10


def test_var_exception_tests_no_divide_by_zero_with_no_exceptions():
    returns = pd.DataFrame(
        {"Strategy": [0.001] * 320},
        index=pd.date_range("2021-01-01", periods=320, freq="B"),
    )

    result = var_exception_tests(returns, alpha=0.05, lookback=30)

    assert result.loc[0, "Exceptions"] == 0
    assert result.loc[0, "Kupiec_Result"] in {
        "Reject at 5%",
        "Do not reject at 5%",
        "Inconclusive",
    }


def test_var_exception_christoffersen_output_is_stable():
    returns = pd.DataFrame(
        {"Strategy": [0.01, -0.03, 0.01, -0.04, 0.01, 0.01, -0.05] * 60},
        index=pd.date_range("2021-01-01", periods=420, freq="B"),
    )

    result = var_exception_tests(returns, alpha=0.20, lookback=20)

    assert "Christoffersen_Result" in result.columns
    assert result.loc[0, "Christoffersen_Result"] in {
        "Reject at 5%",
        "Do not reject at 5%",
        "Inconclusive",
    }
