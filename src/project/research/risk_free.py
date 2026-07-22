"""Chronological market risk-free hurdle construction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR


def fetch_market_risk_free_series(
    dates: pd.Index,
    *,
    proxy: str = "^IRX",
    fill_limit_days: int = 5,
) -> pd.DataFrame:
    """Fetch and align a quoted annual T-bill rate without future filling."""
    index = pd.DatetimeIndex(pd.to_datetime(dates, errors="coerce"))
    index = index[index.notna()].unique().sort_values()
    if index.empty:
        raise ValueError("Risk-free alignment requires valid portfolio dates.")
    try:
        import yfinance as yf

        raw = yf.download(
            proxy,
            start=(index.min() - pd.Timedelta(days=10)).date().isoformat(),
            end=(index.max() + pd.Timedelta(days=2)).date().isoformat(),
            auto_adjust=False,
            progress=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not fetch market risk-free proxy {proxy}.") from exc
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if raw.empty or "Close" not in raw:
        raise RuntimeError(f"Market risk-free proxy {proxy} returned no Close series.")
    annual = pd.to_numeric(raw["Close"].squeeze(), errors="coerce") / 100.0
    annual.index = pd.to_datetime(annual.index, errors="coerce").tz_localize(None)
    annual = annual.loc[annual.index.notna()].sort_index().dropna()
    if annual.empty or bool((annual <= -1.0).any()):
        raise RuntimeError("Market risk-free annual rates are empty or invalid.")
    aligned = annual.reindex(index).ffill(limit=int(fill_limit_days))
    if aligned.isna().any():
        missing = aligned.index[aligned.isna()]
        raise RuntimeError(
            "Risk-free series cannot be aligned without future filling; "
            f"missing_dates={len(missing)} first={missing.min().date()}."
        )
    daily = (1.0 + aligned) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
    return pd.DataFrame(
        {
            "Date": index,
            "annual_rate": aligned.to_numpy(dtype=float),
            "daily_hurdle": daily.to_numpy(dtype=float),
            "proxy": proxy,
            "alignment_policy": f"past_only_forward_fill_limit_{fill_limit_days}_rows",
        }
    )


def read_risk_free_series(path: str | Path) -> pd.DataFrame:
    """Read and validate the persisted market risk-free evidence."""
    frame = pd.read_csv(path)
    required = {"Date", "annual_rate", "daily_hurdle", "proxy", "alignment_policy"}
    if not required.issubset(frame.columns):
        raise ValueError("Risk-free evidence is missing required columns.")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["annual_rate"] = pd.to_numeric(frame["annual_rate"], errors="coerce")
    frame["daily_hurdle"] = pd.to_numeric(frame["daily_hurdle"], errors="coerce")
    if frame[list(required - {"proxy", "alignment_policy"})].isna().any().any():
        raise ValueError("Risk-free evidence contains invalid dates or rates.")
    if not np.isfinite(frame[["annual_rate", "daily_hurdle"]].to_numpy()).all():
        raise ValueError("Risk-free evidence must be finite.")
    return frame.sort_values("Date").reset_index(drop=True)
