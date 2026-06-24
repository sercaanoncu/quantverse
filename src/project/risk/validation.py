"""Market-risk validation diagnostics."""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
from scipy.stats import chi2


def var_exception_tests(
    strategy_returns: pd.DataFrame,
    alpha: float = 0.05,
    lookback: int = 252,
) -> pd.DataFrame:
    """Run rolling historical VaR exception tests for return series.

    VaR is estimated from prior observations only. The test is research-grade and
    intended to detect whether observed one-day breaches are broadly consistent
    with the configured historical VaR exceedance probability.
    """
    rows = []
    for strategy in strategy_returns.columns:
        returns = strategy_returns[strategy].dropna()
        if len(returns) <= lookback:
            rows.append(_insufficient_row(strategy, alpha, lookback, len(returns)))
            continue

        threshold = returns.rolling(lookback).quantile(alpha).shift(1)
        aligned = pd.DataFrame({"return": returns, "threshold": threshold}).dropna()
        if aligned.empty:
            rows.append(_insufficient_row(strategy, alpha, lookback, len(returns)))
            continue

        exceptions = (aligned["return"] < aligned["threshold"]).astype(int)
        n_obs = int(len(exceptions))
        n_exc = int(exceptions.sum())
        expected = float(alpha * n_obs)
        exc_rate = float(n_exc / n_obs) if n_obs else np.nan

        kupiec = _kupiec_pof(n_obs=n_obs, n_exc=n_exc, alpha=alpha)
        christoffersen = _christoffersen_independence(exceptions)
        rows.append(
            {
                "Strategy": strategy,
                "VaR_Method": "rolling_historical_prior_window",
                "Alpha": alpha,
                "Lookback_Days": lookback,
                "Observations": n_obs,
                "Exceptions": n_exc,
                "Expected_Exceptions": expected,
                "Exception_Rate": exc_rate,
                "Kupiec_LR": kupiec["lr"],
                "Kupiec_p_value": kupiec["p_value"],
                "Kupiec_Result": _test_label(kupiec["p_value"]),
                "Christoffersen_LR": christoffersen["lr"],
                "Christoffersen_p_value": christoffersen["p_value"],
                "Christoffersen_Result": christoffersen["result"],
                "Interpretation": _exception_interpretation(exc_rate, alpha),
            }
        )
    return pd.DataFrame(rows)


def _kupiec_pof(n_obs: int, n_exc: int, alpha: float) -> Dict[str, float]:
    if n_obs <= 0:
        return {"lr": np.nan, "p_value": np.nan}
    if n_exc == 0:
        phat = 1e-12
    elif n_exc == n_obs:
        phat = 1 - 1e-12
    else:
        phat = n_exc / n_obs

    log_null = (n_obs - n_exc) * np.log(1 - alpha) + n_exc * np.log(alpha)
    log_alt = (n_obs - n_exc) * np.log(1 - phat) + n_exc * np.log(phat)
    lr = max(0.0, -2.0 * (log_null - log_alt))
    return {"lr": float(lr), "p_value": float(1 - chi2.cdf(lr, df=1))}


def _christoffersen_independence(exceptions: pd.Series) -> Dict[str, float | str]:
    values = exceptions.astype(int).to_numpy()
    if len(values) < 2 or values.sum() == 0 or values.sum() == len(values):
        return {
            "lr": np.nan,
            "p_value": np.nan,
            "result": "Inconclusive: not enough exception-state variation",
        }

    prev = values[:-1]
    curr = values[1:]
    n00 = int(((prev == 0) & (curr == 0)).sum())
    n01 = int(((prev == 0) & (curr == 1)).sum())
    n10 = int(((prev == 1) & (curr == 0)).sum())
    n11 = int(((prev == 1) & (curr == 1)).sum())
    if (n00 + n01) == 0 or (n10 + n11) == 0:
        return {
            "lr": np.nan,
            "p_value": np.nan,
            "result": "Inconclusive: missing transition class",
        }

    pi = (n01 + n11) / max(n00 + n01 + n10 + n11, 1)
    pi0 = n01 / (n00 + n01)
    pi1 = n11 / (n10 + n11)
    eps = 1e-12
    pi = float(np.clip(pi, eps, 1 - eps))
    pi0 = float(np.clip(pi0, eps, 1 - eps))
    pi1 = float(np.clip(pi1, eps, 1 - eps))

    log_independent = (n00 + n10) * np.log(1 - pi) + (n01 + n11) * np.log(pi)
    log_markov = (
        n00 * np.log(1 - pi0)
        + n01 * np.log(pi0)
        + n10 * np.log(1 - pi1)
        + n11 * np.log(pi1)
    )
    lr = max(0.0, -2.0 * (log_independent - log_markov))
    p_value = float(1 - chi2.cdf(lr, df=1))
    return {
        "lr": float(lr),
        "p_value": p_value,
        "result": _test_label(p_value),
    }


def _test_label(p_value: float) -> str:
    if pd.isna(p_value):
        return "Inconclusive"
    return "Reject at 5%" if p_value < 0.05 else "Do not reject at 5%"


def _exception_interpretation(exception_rate: float, alpha: float) -> str:
    if pd.isna(exception_rate):
        return "Insufficient data"
    if exception_rate > alpha * 1.5:
        return "High exception rate; VaR may understate realized downside risk"
    if exception_rate < alpha * 0.5:
        return "Low exception rate; VaR may be conservative for this period"
    return "Exception frequency is broadly near the configured VaR tail rate"


def _insufficient_row(
    strategy: str,
    alpha: float,
    lookback: int,
    n_obs: int,
) -> Dict[str, object]:
    return {
        "Strategy": strategy,
        "VaR_Method": "rolling_historical_prior_window",
        "Alpha": alpha,
        "Lookback_Days": lookback,
        "Observations": n_obs,
        "Exceptions": np.nan,
        "Expected_Exceptions": np.nan,
        "Exception_Rate": np.nan,
        "Kupiec_LR": np.nan,
        "Kupiec_p_value": np.nan,
        "Kupiec_Result": "Inconclusive",
        "Christoffersen_LR": np.nan,
        "Christoffersen_p_value": np.nan,
        "Christoffersen_Result": "Inconclusive",
        "Interpretation": "Insufficient observations after VaR lookback",
    }
