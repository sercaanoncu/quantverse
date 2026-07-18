"""Global security price and return matrix utilities.

The functions here are intentionally deterministic when local price CSV files
are supplied. Live downloads are optional caller behavior and are not required
by tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from project.data_pipeline.security_universe import (
    REQUIRED_UNIVERSE_COLUMNS,
    validate_security_universe_schema,
)
from project.data_pipeline.security_identity import resolve_security_master_rows

DEFAULT_FX_MAPPINGS: dict[str, dict[str, object]] = {
    "USD": {
        "currency_code": "USD",
        "fx_ticker": "",
        "quote_direction": "native_base",
        "expected_interpretation": "USD assets are already in the reporting base currency.",
        "inversion_required": False,
        "fallback_behavior": "native_base",
    },
    "EUR": {
        "currency_code": "EUR",
        "fx_ticker": "EURUSD=X",
        "quote_direction": "USD per 1 EUR",
        "expected_interpretation": "A positive return means EUR strengthened versus USD.",
        "inversion_required": False,
        "fallback_behavior": "fx_missing",
    },
    "GBP": {
        "currency_code": "GBP",
        "fx_ticker": "GBPUSD=X",
        "quote_direction": "USD per 1 GBP",
        "expected_interpretation": "A positive return means GBP strengthened versus USD.",
        "inversion_required": False,
        "fallback_behavior": "fx_missing",
    },
    "TRY": {
        "currency_code": "TRY",
        "fx_ticker": "TRY=X",
        "quote_direction": "TRY per 1 USD",
        "expected_interpretation": "Yahoo-style USDTRY quotes are inverted to get TRY against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "JPY": {
        "currency_code": "JPY",
        "fx_ticker": "JPY=X",
        "quote_direction": "JPY per 1 USD",
        "expected_interpretation": "Yahoo-style USDJPY quotes are inverted to get JPY against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "HKD": {
        "currency_code": "HKD",
        "fx_ticker": "HKD=X",
        "quote_direction": "HKD per 1 USD",
        "expected_interpretation": "Yahoo-style USDHKD quotes are inverted to get HKD against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "CNY": {
        "currency_code": "CNY",
        "fx_ticker": "CNY=X",
        "quote_direction": "CNY per 1 USD",
        "expected_interpretation": "Yahoo-style USDCNY quotes are inverted to get CNY against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "CNH": {
        "currency_code": "CNH",
        "fx_ticker": "CNH=X",
        "quote_direction": "CNH per 1 USD",
        "expected_interpretation": "Yahoo-style USDCNH quotes are inverted to get CNH against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "CAD": {
        "currency_code": "CAD",
        "fx_ticker": "CAD=X",
        "quote_direction": "CAD per 1 USD",
        "expected_interpretation": "Yahoo-style USDCAD quotes are inverted to get CAD against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "CHF": {
        "currency_code": "CHF",
        "fx_ticker": "CHF=X",
        "quote_direction": "CHF per 1 USD",
        "expected_interpretation": "Yahoo-style USDCHF quotes are inverted to get CHF against USD.",
        "inversion_required": True,
        "fallback_behavior": "fx_missing",
    },
    "AUD": {
        "currency_code": "AUD",
        "fx_ticker": "AUDUSD=X",
        "quote_direction": "USD per 1 AUD",
        "expected_interpretation": "A positive return means AUD strengthened versus USD.",
        "inversion_required": False,
        "fallback_behavior": "fx_missing",
    },
}


def load_global_universe(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Load and combine available universe CSV files."""
    frames = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        validate_security_universe_schema(frame)
        if not frame.empty:
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


def fx_mappings_from_config(
    config: dict[str, Any] | None,
) -> dict[str, dict[str, object]]:
    """Return currency-to-USD FX metadata from config plus conservative defaults."""
    mappings = {key: dict(value) for key, value in DEFAULT_FX_MAPPINGS.items()}
    raw = (config or {}).get("currency_mappings", config or {})
    for currency, value in (raw or {}).items():
        code = str(currency).upper()
        override = dict(value or {})
        merged = dict(mappings.get(code, {"currency_code": code}))
        merged.update(override)
        merged["currency_code"] = code
        merged["inversion_required"] = _as_bool(merged.get("inversion_required", False))
        mappings[code] = merged
    return mappings


def required_fx_tickers(
    universe: pd.DataFrame,
    base_currency: str = "USD",
    fx_mappings: dict[str, dict[str, object]] | None = None,
) -> list[str]:
    """List non-base FX tickers required by investable included assets."""
    mappings = fx_mappings or DEFAULT_FX_MAPPINGS
    base = str(base_currency).upper()
    if universe.empty or "currency" not in universe:
        return []
    rows = universe.loc[_included_investable_mask(universe)].copy()
    currencies = sorted(set(rows["currency"].fillna("").astype(str).str.upper()))
    tickers: list[str] = []
    for currency in currencies:
        if not currency or currency == base:
            continue
        ticker = str(mappings.get(currency, {}).get("fx_ticker", "") or "")
        if ticker:
            tickers.append(ticker)
    return list(dict.fromkeys(tickers))


def normalize_returns_to_base(
    local_returns: pd.DataFrame,
    universe: pd.DataFrame,
    fx_prices: pd.DataFrame | None = None,
    *,
    base_currency: str = "USD",
    fx_mappings: dict[str, dict[str, object]] | None = None,
    max_forward_fill_days: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convert local simple returns to base-currency simple returns.

    The conversion uses simple-return compounding:
    ``usd_return = (1 + local_asset_return) * (1 + fx_return_to_usd) - 1``.
    FX returns must represent the local currency return against the base
    currency. When an FX quote is supplied in the inverse direction, the quote
    price is inverted before returns are computed.
    """
    mappings = fx_mappings or DEFAULT_FX_MAPPINGS
    base = str(base_currency).upper()
    local = local_returns.apply(pd.to_numeric, errors="coerce").sort_index()
    fx_price_frame = (
        pd.DataFrame(index=local.index)
        if fx_prices is None
        else fx_prices.apply(pd.to_numeric, errors="coerce").sort_index()
    )
    usd_columns: dict[str, pd.Series] = {}
    report_rows: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []
    metadata = (
        resolve_security_master_rows(universe).set_index("ticker")
        if not universe.empty and "ticker" in universe
        else pd.DataFrame()
    )
    tickers = list(local.columns)
    for ticker in tickers:
        row = (
            metadata.loc[ticker]
            if ticker in metadata.index
            else pd.Series(dtype=object)
        )
        currency = str(row.get("currency", base) or base).upper()
        mapping = dict(mappings.get(currency, {}))
        asset_series = local[ticker]
        asset_obs = int(asset_series.notna().sum())
        flags = _row_flags(row)
        if flags["signal_only"]:
            usd_columns[ticker] = pd.Series(np.nan, index=local.index, dtype=float)
            status = "signal_only"
            warning = "Signal-only assets are not treated as investable FX promotion blockers."
            fx_return = pd.Series(index=local.index, dtype=float)
        elif not flags["investable"]:
            usd_columns[ticker] = pd.Series(np.nan, index=local.index, dtype=float)
            status = "not_investable"
            warning = "Asset is not an included investable row."
            fx_return = pd.Series(index=local.index, dtype=float)
        elif currency == base:
            usd_columns[ticker] = asset_series.copy()
            status = "native_base"
            warning = ""
            fx_return = pd.Series(0.0, index=local.index, dtype=float)
        elif not mapping or not str(mapping.get("fx_ticker", "") or ""):
            usd_columns[ticker] = pd.Series(np.nan, index=local.index, dtype=float)
            status = "fx_missing"
            warning = f"No configured FX mapping for {currency}."
            fx_return = pd.Series(index=local.index, dtype=float)
        else:
            fx_ticker = str(mapping.get("fx_ticker", "") or "")
            fx_return = _fx_return_to_base(
                fx_price_frame,
                fx_ticker=fx_ticker,
                invert=_as_bool(mapping.get("inversion_required", False)),
                target_index=local.index,
                max_forward_fill_days=max_forward_fill_days,
            )
            aligned = asset_series.notna() & fx_return.notna()
            if int(aligned.sum()) == 0:
                usd_columns[ticker] = pd.Series(np.nan, index=local.index, dtype=float)
                status = "fx_missing"
                warning = f"FX series {fx_ticker} is missing or has no aligned returns."
            else:
                converted = ((1.0 + asset_series) * (1.0 + fx_return)) - 1.0
                usd_columns[ticker] = converted.where(aligned, np.nan)
                status = "fx_normalized"
                warning = ""
        fx_ticker = str(mapping.get("fx_ticker", "") or "")
        fx_obs = int(fx_return.notna().sum())
        aligned_obs = int((asset_series.notna() & fx_return.notna()).sum())
        missing_fx_dates = int((asset_series.notna() & fx_return.isna()).sum())
        report_rows.append(
            {
                "ticker": ticker,
                "currency": currency,
                "base_currency": base,
                "fx_ticker": fx_ticker,
                "fx_source": str(mapping.get("source", "yfinance") or "yfinance"),
                "quote_direction": str(mapping.get("quote_direction", "") or ""),
                "expected_interpretation": str(
                    mapping.get("expected_interpretation", "") or ""
                ),
                "inversion_required": _as_bool(
                    mapping.get("inversion_required", False)
                ),
                "fallback_behavior": str(
                    mapping.get("fallback_behavior", "fx_missing") or "fx_missing"
                ),
                "asset_return_observations": asset_obs,
                "fx_return_observations": fx_obs,
                "aligned_return_observations": aligned_obs,
                "fx_missing_dates": missing_fx_dates,
                "fx_coverage_ratio": (
                    float(aligned_obs / asset_obs) if asset_obs else np.nan
                ),
                "investable": flags["investable"],
                "signal_only": flags["signal_only"],
                "include": flags["include"],
                "benchmark_only": flags["benchmark_only"],
                "fx_normalization_status": status,
                "warning": warning,
            }
        )
    for currency in sorted(
        set(
            universe.get("currency", pd.Series(dtype=str))
            .fillna("")
            .astype(str)
            .str.upper()
        )
    ):
        mapping = dict(mappings.get(currency, {}))
        ticker = str(mapping.get("fx_ticker", "") or "")
        if not currency:
            continue
        if currency == base:
            status = "native_base"
            observations = 0
            first_date = ""
            last_date = ""
        elif ticker and ticker in fx_price_frame:
            series = fx_price_frame[ticker].dropna()
            observations = int(series.shape[0])
            first_date = str(series.index.min().date()) if observations else ""
            last_date = str(series.index.max().date()) if observations else ""
            status = "available" if observations else "missing"
        else:
            observations = 0
            first_date = ""
            last_date = ""
            status = "missing"
        coverage_rows.append(
            {
                "currency": currency,
                "base_currency": base,
                "fx_ticker": ticker,
                "fx_source": str(mapping.get("source", "yfinance") or "yfinance"),
                "quote_direction": str(mapping.get("quote_direction", "") or ""),
                "expected_interpretation": str(
                    mapping.get("expected_interpretation", "") or ""
                ),
                "inversion_required": _as_bool(
                    mapping.get("inversion_required", False)
                ),
                "price_observations": observations,
                "first_date": first_date,
                "last_date": last_date,
                "coverage_status": status,
                "fallback_behavior": str(
                    mapping.get("fallback_behavior", "fx_missing") or "fx_missing"
                ),
            }
        )
    usd = pd.DataFrame(usd_columns, index=local.index)
    return usd, pd.DataFrame(report_rows), pd.DataFrame(coverage_rows)


def simple_to_log_returns(simple_returns: pd.DataFrame) -> pd.DataFrame:
    """Convert simple returns into log returns for diagnostics."""
    clean = simple_returns.apply(pd.to_numeric, errors="coerce")
    return np.log1p(clean.where(clean > -1.0)).replace(
        [float("inf"), -float("inf")], pd.NA
    )


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
    empty_returns = pd.DataFrame(
        index=pd.RangeIndex(0),
        columns=universe["ticker"].dropna().astype(str).drop_duplicates().tolist(),
    )
    _, report, _ = normalize_returns_to_base(
        empty_returns,
        universe,
        pd.DataFrame(),
        base_currency=base_currency,
    )
    return report


def _fx_return_to_base(
    fx_prices: pd.DataFrame,
    *,
    fx_ticker: str,
    invert: bool,
    target_index: pd.Index,
    max_forward_fill_days: int,
) -> pd.Series:
    if fx_ticker not in fx_prices:
        return pd.Series(index=target_index, dtype=float)
    prices = pd.to_numeric(fx_prices[fx_ticker], errors="coerce").sort_index()
    prices.index = pd.to_datetime(prices.index, errors="coerce")
    prices = prices.loc[prices.index.notna()]
    if invert:
        prices = 1.0 / prices.where(prices > 0)
    if int(max_forward_fill_days) > 0:
        aligned = prices.reindex(pd.DatetimeIndex(target_index))
        aligned = aligned.ffill(limit=int(max_forward_fill_days))
        returns = aligned.pct_change(fill_method=None)
    else:
        returns = prices.pct_change(fill_method=None).reindex(
            pd.DatetimeIndex(target_index)
        )
    return returns.replace([float("inf"), -float("inf")], pd.NA)


def _included_investable_mask(frame: pd.DataFrame) -> pd.Series:
    mask = _bool_column(frame, "include", default=True) & _bool_column(
        frame, "investable", default=True
    )
    mask &= ~_bool_column(frame, "benchmark_only", default=False)
    mask &= ~_bool_column(frame, "signal_only", default=False)
    return mask


def _bool_column(frame: pd.DataFrame, column: str, *, default: bool) -> pd.Series:
    if column not in frame:
        return pd.Series(default, index=frame.index)
    return frame[column].map(_as_bool)


def _row_flags(row: pd.Series) -> dict[str, bool]:
    include = _as_bool(row.get("include", True))
    investable_flag = _as_bool(row.get("investable", True))
    benchmark_only = _as_bool(row.get("benchmark_only", False))
    signal_only = _as_bool(row.get("signal_only", False))
    return {
        "include": include,
        "benchmark_only": benchmark_only,
        "signal_only": signal_only,
        "investable": bool(
            include and investable_flag and not benchmark_only and not signal_only
        ),
    }


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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
