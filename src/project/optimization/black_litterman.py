"""Black-Litterman allocation utilities.

This module implements a compact, deterministic Black-Litterman workflow for
research use. It requires market capitalizations for a valid prior and does not
claim superiority without downstream validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def market_cap_weights(market_caps: pd.Series) -> pd.Series:
    """Convert positive market capitalizations into normalized weights."""
    caps = pd.Series(market_caps, dtype=float).replace([np.inf, -np.inf], np.nan)
    if caps.isna().any() or (caps <= 0).any():
        raise ValueError(
            "Black-Litterman requires positive market caps for all assets."
        )
    weights = caps / caps.sum()
    weights.name = "Market_Cap_Weight"
    return weights


def implied_equilibrium_returns(
    covariance: pd.DataFrame,
    market_weights: pd.Series,
    risk_aversion: float = 2.5,
) -> pd.Series:
    """Compute implied equilibrium returns pi = delta * Sigma * w."""
    cov = covariance.loc[market_weights.index, market_weights.index].astype(float)
    pi = float(risk_aversion) * cov.to_numpy() @ market_weights.to_numpy()
    return pd.Series(pi, index=market_weights.index, name="Prior_Return")


def black_litterman_posterior(
    covariance: pd.DataFrame,
    market_caps: pd.Series,
    views_p: pd.DataFrame | np.ndarray | None = None,
    views_q: pd.Series | np.ndarray | None = None,
    omega: pd.DataFrame | np.ndarray | None = None,
    tau: float = 0.05,
    risk_aversion: float = 2.5,
) -> dict[str, pd.Series]:
    """Compute prior and posterior expected returns."""
    weights = market_cap_weights(market_caps)
    cov = covariance.loc[weights.index, weights.index].astype(float)
    prior = implied_equilibrium_returns(cov, weights, risk_aversion=risk_aversion)
    if views_p is None or views_q is None:
        return {
            "market_weights": weights,
            "prior_returns": prior,
            "posterior_returns": prior.copy().rename("Posterior_Return"),
        }

    sigma = cov.to_numpy(dtype=float)
    p_matrix = np.asarray(views_p, dtype=float)
    q_vector = np.asarray(views_q, dtype=float).reshape(-1)
    if p_matrix.ndim != 2 or p_matrix.shape[1] != len(weights):
        raise ValueError("views_p must have one column per asset.")
    if p_matrix.shape[0] != q_vector.shape[0]:
        raise ValueError("views_q must have one value per view.")
    tau_sigma = float(tau) * sigma
    if omega is None:
        omega_matrix = np.diag(np.diag(p_matrix @ tau_sigma @ p_matrix.T))
    else:
        omega_matrix = np.asarray(omega, dtype=float)
    middle = np.linalg.inv(p_matrix @ tau_sigma @ p_matrix.T + omega_matrix)
    posterior = prior.to_numpy() + tau_sigma @ p_matrix.T @ middle @ (
        q_vector - p_matrix @ prior.to_numpy()
    )
    return {
        "market_weights": weights,
        "prior_returns": prior,
        "posterior_returns": pd.Series(
            posterior,
            index=weights.index,
            name="Posterior_Return",
        ),
    }


def black_litterman_weights(
    covariance: pd.DataFrame,
    market_caps: pd.Series,
    views_p: pd.DataFrame | np.ndarray | None = None,
    views_q: pd.Series | np.ndarray | None = None,
    omega: pd.DataFrame | np.ndarray | None = None,
    max_weight: float = 0.10,
    tau: float = 0.05,
    risk_aversion: float = 2.5,
) -> pd.Series:
    """Build long-only capped Black-Litterman weights."""
    posterior = black_litterman_posterior(
        covariance,
        market_caps,
        views_p=views_p,
        views_q=views_q,
        omega=omega,
        tau=tau,
        risk_aversion=risk_aversion,
    )
    assets = posterior["posterior_returns"].index
    cov = covariance.loc[assets, assets].to_numpy(dtype=float)
    mu = posterior["posterior_returns"].to_numpy(dtype=float)
    x0 = _cap_and_normalize(posterior["market_weights"], max_weight).to_numpy()

    def objective(weights: np.ndarray) -> float:
        return float(0.5 * risk_aversion * weights @ cov @ weights - weights @ mu)

    result = minimize(
        objective,
        x0=x0,
        bounds=[(0.0, float(max_weight)) for _ in assets],
        constraints={"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
        method="SLSQP",
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if result.success:
        return _cap_and_normalize(pd.Series(result.x, index=assets), max_weight)
    return _cap_and_normalize(posterior["market_weights"], max_weight)


def _cap_and_normalize(weights: pd.Series, max_weight: float) -> pd.Series:
    raw = pd.Series(weights, dtype=float).clip(lower=0.0)
    if len(raw) == 0:
        raise ValueError("At least one asset is required.")
    if max_weight * len(raw) < 1.0 - 1e-12:
        raise ValueError("max_weight is infeasible for the number of assets.")
    if raw.sum() <= 0:
        raw = pd.Series(1.0, index=raw.index)
    remaining = list(raw.index)
    capped = pd.Series(0.0, index=raw.index, dtype=float)
    remaining_total = 1.0
    while remaining:
        base = raw.loc[remaining]
        provisional = base / base.sum() * remaining_total
        over = provisional[provisional > max_weight + 1e-12]
        if over.empty:
            capped.loc[remaining] = provisional
            break
        capped.loc[over.index] = max_weight
        remaining_total -= max_weight * len(over)
        remaining = [asset for asset in remaining if asset not in set(over.index)]
    capped = capped / capped.sum()
    capped.name = "Weight"
    return capped
