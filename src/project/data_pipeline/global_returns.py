"""Global security price and return matrix utilities.

The functions here are intentionally deterministic when local price CSV files
are supplied. Live downloads are optional caller behavior and are not required
by tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from project.data_pipeline.security_universe import (
    REQUIRED_UNIVERSE_COLUMNS,
    validate_security_universe_schema,
)


def load_global_universe(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Load and combine available universe CSV files."""
    frames = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        validate_security_universe_schema(frame)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=REQUIRED_UNIVERSE_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def load_price_matrix(path: str | Path) -> pd.DataFrame:
    """Load a wide adjusted-close price matrix from CSV."""
    price_path = Path(path)
    if not price_path.exists():
        raise FileNotFoundError(f"Price CSV not found: {price_path}")
    raw = pd.read_csv(price_path)
    if raw.empty:
        return pd.DataFrame()
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    prices = raw.apply(pd.to_numeric, errors="coerce")
    prices.index = pd.to_datetime(prices.index, errors="coerce")
    prices = prices.loc[prices.index.notna()].sort_index()
    return prices.dropna(axis=1, how="all")


def build_returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Convert adjusted-close prices into simple daily returns."""
    clean = prices.apply(pd.to_numeric, errors="coerce").sort_index()
    clean = clean.loc[:, clean.notna().any()]
    return clean.pct_change(fill_method=None).replace(
        [float("inf"), -float("inf")], pd.NA
    )


def build_log_returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Convert adjusted-close prices into log returns for diagnostics."""
    clean = prices.apply(pd.to_numeric, errors="coerce").sort_index()
    clean = clean.loc[:, clean.notna().any()]
    log_prices = np.log(clean.where(clean > 0))
    return log_prices.diff().replace([float("inf"), -float("inf")], pd.NA)


def coverage_report(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    min_observations: int = 20,
) -> pd.DataFrame:
    """Report price coverage and explicit drop reasons for each asset."""
    tickers = (
        universe["ticker"].dropna().astype(str).drop_duplicates().tolist()
        if "ticker" in universe
        else list(prices.columns)
    )
    rows = []
    for ticker in tickers:
        observations = int(prices[ticker].notna().sum()) if ticker in prices else 0
        included = observations >= int(min_observations)
        rows.append(
            {
                "ticker": ticker,
                "price_observations": observations,
                "included_in_returns": bool(included),
                "drop_reason": "" if included else "insufficient_price_coverage",
            }
        )
    return pd.DataFrame(rows)


def filter_prices_by_coverage(
    prices: pd.DataFrame,
    report: pd.DataFrame,
) -> pd.DataFrame:
    """Keep only assets that passed coverage checks."""
    keep = report.loc[report["included_in_returns"], "ticker"].astype(str).tolist()
    return prices[[ticker for ticker in keep if ticker in prices]].copy()


def fx_normalization_report(
    universe: pd.DataFrame,
    base_currency: str = "USD",
) -> pd.DataFrame:
    """Explain current FX treatment for every asset."""
    if universe.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "currency",
                "base_currency",
                "fx_normalization_status",
                "warning",
            ]
        )
    rows = []
    for _, row in universe.iterrows():
        currency = str(row.get("currency", "") or "")
        normalized = currency.upper() == str(base_currency).upper()
        rows.append(
            {
                "ticker": row.get("ticker", ""),
                "currency": currency,
                "base_currency": base_currency,
                "fx_normalization_status": (
                    "native_base" if normalized else "not_implemented"
                ),
                "warning": (
                    ""
                    if normalized
                    else "Full FX normalization is not implemented in this sprint."
                ),
            }
        )
    return pd.DataFrame(rows)


def return_outlier_report(
    returns: pd.DataFrame,
    absolute_threshold: float = 0.25,
) -> pd.DataFrame:
    """Flag extreme one-day simple returns for review."""
    rows = []
    clean = returns.apply(pd.to_numeric, errors="coerce")
    for ticker, series in clean.items():
        outliers = series[series.abs() >= float(absolute_threshold)].dropna()
        for dt, value in outliers.items():
            rows.append(
                {
                    "date": dt,
                    "ticker": ticker,
                    "return": float(value),
                    "absolute_threshold": float(absolute_threshold),
                    "issue": "large_absolute_daily_return",
                    "severity": "warning",
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "date",
            "ticker",
            "return",
            "absolute_threshold",
            "issue",
            "severity",
        ],
    )


def fetch_prices_with_yfinance(
    tickers: list[str],
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Optional yfinance adjusted-close fetcher used only when explicitly called."""
    if not tickers:
        return pd.DataFrame()
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()
    frames = []
    unique_tickers = list(dict.fromkeys(str(ticker) for ticker in tickers))
    for start_idx in range(0, len(unique_tickers), 50):
        batch = unique_tickers[start_idx : start_idx + 50]
        data = yf.download(
            batch,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
        close = _extract_close(data, batch)
        if not close.empty:
            frames.append(close)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).loc[
        :, ~pd.concat(frames, axis=1).columns.duplicated()
    ]


def _extract_close(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"]
        elif "Adj Close" in data.columns.get_level_values(0):
            close = data["Adj Close"]
        else:
            return pd.DataFrame()
    else:
        close = data[["Close"]] if "Close" in data else data
        if len(tickers) == 1:
            close.columns = tickers
    return close.apply(pd.to_numeric, errors="coerce")
