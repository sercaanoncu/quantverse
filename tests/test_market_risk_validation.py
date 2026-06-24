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
