"""Shared portfolio-weight alignment and validation contract."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def align_portfolio_weights(
    weights: pd.Series,
    tickers: Iterable[str],
    *,
    context: str = "Portfolio",
    require_sum_one: bool = True,
    tolerance: float = 1e-8,
) -> pd.Series:
    """Align weights without silently dropping a nonzero portfolio position."""
    supplied = pd.Series(weights, copy=True)
    if supplied.index.has_duplicates:
        duplicates = supplied.index[supplied.index.duplicated()].astype(str).unique()
        raise ValueError(
            f"{context} weights contain duplicate tickers: " + ", ".join(duplicates)
        )

    numeric = pd.to_numeric(supplied, errors="coerce")
    if numeric.isna().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError(f"{context} weights must be finite")
    ticker_index = pd.Index(list(tickers))
    missing_nonzero = numeric[
        ~numeric.index.isin(ticker_index) & numeric.abs().gt(tolerance)
    ]
    if not missing_nonzero.empty:
        raise ValueError(
            f"{context} weights contain assets missing from returns: "
            + ", ".join(map(str, missing_nonzero.index))
        )

    aligned = numeric.reindex(ticker_index).fillna(0.0).astype(float)
    if require_sum_one and not np.isclose(
        float(aligned.sum()), 1.0, atol=tolerance, rtol=0.0
    ):
        raise ValueError(f"{context} weights must sum to 1")
    return aligned
