"""QuantVerse v2 public-data global stock scoring engine.

The scoring layer is deterministic and works from an already prepared USD
returns matrix. It does not download data, fabricate ranks, or turn scores into
investment advice. Scores are cross-sectional research diagnostics used by the
v2 portfolio league and walk-forward engine.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR

SCORE_COLUMNS = [
    "ticker",
    "name",
    "sleeve",
    "region",
    "country",
    "currency",
    "source_provider",
    "exact_proxy_status",
    "observations",
    "data_coverage_score",
    "liquidity_proxy_score",
    "momentum_1m",
    "momentum_3m",
    "momentum_6m",
    "momentum_12m",
    "volatility_3m",
    "volatility_12m",
    "downside_volatility",
    "max_drawdown",
    "sharpe_like_score",
    "sortino_like_score",
    "trend_score",
    "mean_reversion_score",
    "correlation_diversification_score",
    "risk_penalty_score",
    "expected_return_signal_score",
    "composite_quant_score",
    "rank_global",
    "rank_within_sleeve",
    "selection_flag",
    "selection_reason",
    "warning_flags",
]


def build_global_stock_scores(
    returns: pd.DataFrame,
    universe: pd.DataFrame,
    coverage_report: pd.DataFrame | None = None,
    *,
    as_of_date: str | pd.Timestamp | None = None,
    max_selected: int = 40,
) -> pd.DataFrame:
    """Build transparent stock-selection scores from past available returns."""
    clean = _clean_returns(returns, as_of_date=as_of_date)
    metadata = _metadata(universe)
    tickers = [ticker for ticker in metadata["ticker"].astype(str) if ticker in clean]
    if not tickers:
        return pd.DataFrame(columns=SCORE_COLUMNS)
    clean = clean[tickers]
    diversification_scores = _correlation_diversification_scores(clean)
    rows = [
        _score_one_asset(
            ticker,
            clean[ticker],
            metadata,
            diversification_scores.get(ticker, 1.0),
        )
        for ticker in tickers
    ]
    scores = pd.DataFrame(rows)
    scores = _merge_coverage(scores, coverage_report)
    scores["data_coverage_score"] = scores["data_coverage_score"].fillna(
        scores["observations"] / max(float(clean.shape[0]), 1.0)
    )
    scores["liquidity_proxy_score"] = _market_cap_percentile(metadata, scores["ticker"])
    scores = _add_composite_score(scores)
    scores = scores.sort_values(
        ["composite_quant_score", "data_coverage_score", "liquidity_proxy_score"],
        ascending=False,
    ).reset_index(drop=True)
    scores["rank_global"] = np.arange(1, len(scores) + 1)
    scores["rank_within_sleeve"] = (
        scores.groupby("sleeve")["composite_quant_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    scores["selection_flag"] = scores["rank_global"] <= int(max_selected)
    scores["selection_reason"] = np.where(
        scores["selection_flag"],
        "Selected by transparent composite score with coverage, momentum, risk and diversification checks.",
        "Not selected because other assets ranked higher under the public-data score.",
    )
    scores["warning_flags"] = scores.apply(_warning_flags, axis=1)
    return scores[SCORE_COLUMNS]


def write_global_stock_scores(scores: pd.DataFrame, output_path: str | Path) -> None:
    """Write stock scores with stable column order."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scores.reindex(columns=SCORE_COLUMNS).to_csv(path, index=False)


def _score_one_asset(
    ticker: str,
    series: pd.Series,
    metadata: pd.DataFrame,
    diversification: float,
) -> dict[str, object]:
    returns = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    meta = metadata.loc[metadata["ticker"].astype(str).eq(str(ticker))].iloc[0]
    observations = int(returns.shape[0])
    vol_3m = _annualized_vol(returns.tail(63))
    vol_12m = _annualized_vol(returns.tail(252))
    downside = _downside_volatility(returns)
    annual_return = float(returns.mean() * TRADING_DAYS_PER_YEAR) if observations else 0
    sharpe = annual_return / vol_12m if vol_12m > 0 else 0.0
    sortino = annual_return / downside if downside > 0 else 0.0
    momentum = {
        "momentum_1m": _period_return(returns, 21),
        "momentum_3m": _period_return(returns, 63),
        "momentum_6m": _period_return(returns, 126),
        "momentum_12m": _period_return(returns, 252),
    }
    trend_score = float(
        np.nanmean(
            [
                momentum["momentum_3m"],
                momentum["momentum_6m"],
                momentum["momentum_12m"],
            ]
        )
    )
    mean_reversion = float(-0.50 * momentum["momentum_1m"])
    return {
        "ticker": ticker,
        "name": meta.get("name", ticker),
        "sleeve": meta.get("sleeve", ""),
        "region": meta.get("region", ""),
        "country": meta.get("country", ""),
        "currency": meta.get("currency", ""),
        "source_provider": meta.get("data_provider", meta.get("source", "")),
        "exact_proxy_status": meta.get("source_method", meta.get("proxy_type", "")),
        "observations": observations,
        "data_coverage_score": np.nan,
        "liquidity_proxy_score": np.nan,
        **momentum,
        "volatility_3m": vol_3m,
        "volatility_12m": vol_12m,
        "downside_volatility": downside,
        "max_drawdown": _max_drawdown(returns),
        "sharpe_like_score": float(sharpe),
        "sortino_like_score": float(sortino),
        "trend_score": trend_score,
        "mean_reversion_score": mean_reversion,
        "correlation_diversification_score": diversification,
        "risk_penalty_score": float(vol_12m + abs(_max_drawdown(returns))),
        "expected_return_signal_score": float(0.60 * trend_score + 0.25 * sharpe),
    }


def _add_composite_score(scores: pd.DataFrame) -> pd.DataFrame:
    scored = scores.copy()
    components = {
        "expected_return_signal_score": 0.30,
        "sharpe_like_score": 0.20,
        "sortino_like_score": 0.15,
        "correlation_diversification_score": 0.10,
        "data_coverage_score": 0.10,
        "liquidity_proxy_score": 0.05,
        "risk_penalty_score": -0.10,
    }
    composite = pd.Series(0.0, index=scored.index)
    for column, weight in components.items():
        composite = composite + weight * _robust_z(scored[column])
    scored["composite_quant_score"] = composite.replace([np.inf, -np.inf], 0.0).fillna(
        0.0
    )
    return scored


def _merge_coverage(
    scores: pd.DataFrame,
    coverage_report: pd.DataFrame | None,
) -> pd.DataFrame:
    if coverage_report is None or coverage_report.empty:
        return scores
    coverage = coverage_report.copy()
    ticker_col = "ticker" if "ticker" in coverage else "Ticker"
    if ticker_col not in coverage:
        return scores
    coverage[ticker_col] = coverage[ticker_col].astype(str)
    possible = [
        "coverage_ratio",
        "Coverage_Ratio",
        "price_coverage_ratio",
        "observations_ratio",
    ]
    score_col = next((column for column in possible if column in coverage), None)
    if score_col is None:
        observation_col = next(
            (
                column
                for column in ["observations", "price_observations"]
                if column in coverage
            ),
            None,
        )
        if observation_col is None:
            return scores
        max_obs = max(
            float(pd.to_numeric(coverage[observation_col], errors="coerce").max()), 1.0
        )
        coverage["coverage_score"] = (
            pd.to_numeric(coverage[observation_col], errors="coerce") / max_obs
        )
        score_col = "coverage_score"
    mapped = coverage.drop_duplicates(ticker_col).set_index(ticker_col)[score_col]
    scores = scores.copy()
    scores["data_coverage_score"] = scores["ticker"].map(mapped).astype(float)
    return scores


def _metadata(universe: pd.DataFrame) -> pd.DataFrame:
    metadata = universe.copy()
    if "ticker" not in metadata:
        raise ValueError("Universe must contain a ticker column.")
    metadata["ticker"] = metadata["ticker"].astype(str)
    return metadata.drop_duplicates("ticker", keep="first")


def _clean_returns(
    returns: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(clean.columns[0])
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    if as_of_date is not None:
        clean = clean.loc[clean.index <= pd.Timestamp(as_of_date)]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    clean = clean.dropna(axis=1, how="all").dropna(how="all")
    return clean


def _period_return(series: pd.Series, window: int) -> float:
    clean = series.dropna().tail(window)
    if clean.empty:
        return 0.0
    return float((1.0 + clean).prod() - 1.0)


def _annualized_vol(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.shape[0] < 2:
        return 0.0
    return float(clean.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def _downside_volatility(series: pd.Series) -> float:
    downside = series.dropna()
    downside = downside[downside < 0]
    if downside.shape[0] < 2:
        return 0.0
    return float(downside.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def _max_drawdown(series: pd.Series) -> float:
    clean = series.dropna().astype(float)
    if clean.empty:
        return 0.0
    wealth = (1.0 + clean).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(drawdown.min())


def _correlation_diversification_scores(matrix: pd.DataFrame) -> pd.Series:
    if matrix.shape[1] <= 1:
        return pd.Series(1.0, index=matrix.columns)
    corr = matrix.corr().abs().replace([np.inf, -np.inf], np.nan)
    corr_array = corr.to_numpy(dtype=float, copy=True)
    np.fill_diagonal(corr_array, np.nan)
    corr = pd.DataFrame(corr_array, index=corr.index, columns=corr.columns)
    return (1.0 - corr.mean(skipna=True)).fillna(1.0)


def _market_cap_percentile(metadata: pd.DataFrame, tickers: pd.Series) -> pd.Series:
    if "market_cap_usd" not in metadata:
        return pd.Series(0.5, index=tickers.index)
    caps = pd.to_numeric(
        metadata.drop_duplicates("ticker").set_index("ticker")["market_cap_usd"],
        errors="coerce",
    )
    ranked = caps.rank(pct=True).fillna(0.5)
    return tickers.map(ranked).fillna(0.5).astype(float)


def _robust_z(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    median = clean.median()
    mad = (clean - median).abs().median()
    if not np.isfinite(mad) or mad <= 1e-12:
        std = clean.std(ddof=0)
        if not np.isfinite(std) or std <= 1e-12:
            return pd.Series(0.0, index=series.index)
        return ((clean - clean.mean()) / std).fillna(0.0).clip(-5, 5)
    return (0.6745 * (clean - median) / mad).fillna(0.0).clip(-5, 5)


def _warning_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if float(row["data_coverage_score"]) < 0.75:
        flags.append("low_coverage")
    if float(row["volatility_12m"]) > 0.80:
        flags.append("high_volatility")
    if float(row["max_drawdown"]) < -0.50:
        flags.append("deep_drawdown")
    if abs(float(row["momentum_1m"])) > 0.75:
        flags.append("extreme_short_term_return")
    return "; ".join(flags) if flags else "none"
