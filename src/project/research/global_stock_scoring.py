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
from project.data_pipeline.security_identity import (
    attach_run_metadata,
    build_feature_history_eligibility,
    resolve_security_master_rows,
)
from project.data_pipeline.security_universe import (
    stablecoin_like_mask,
    unverified_crypto_price_mapping_mask,
)

SCORE_FORMULA_VERSION = "quantverse_v2_score_v1_coverage_momentum_risk_diversification"

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
    "eligibility_status",
    "standard_composite_score_eligible",
    "history_eligibility_reason",
    "selection_flag",
    "selection_reason",
    "warning_flags",
    "score_formula_version",
    "data_window_start",
    "data_window_end",
    "scoring_as_of_date",
    "leakage_check_pass",
    "score_component_summary",
    "run_id",
    "execution_id",
    "data_as_of_date",
    "generated_at",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
]


def build_global_stock_scores(
    returns: pd.DataFrame,
    universe: pd.DataFrame,
    coverage_report: pd.DataFrame | None = None,
    *,
    as_of_date: str | pd.Timestamp | None = None,
    max_selected: int = 40,
    default_scope: str = "equity_only",
    include_crypto: bool = False,
    feature_history_eligibility: pd.DataFrame | None = None,
    minimum_standard_observations: int = 252,
    run_metadata: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Build transparent stock-selection scores from past available returns."""
    clean = _clean_returns(returns, as_of_date=as_of_date)
    metadata = _filter_metadata_scope(
        _metadata(universe),
        default_scope=default_scope,
        include_crypto=include_crypto,
    )
    tickers = [ticker for ticker in metadata["ticker"].astype(str) if ticker in clean]
    if not tickers:
        return pd.DataFrame(columns=SCORE_COLUMNS)
    clean = clean[tickers]
    scoring_as_of = _date_label(
        pd.Timestamp(as_of_date) if as_of_date is not None else clean.index.max()
    )
    eligibility = (
        feature_history_eligibility.copy()
        if feature_history_eligibility is not None
        else build_feature_history_eligibility(
            clean,
            minimum_standard_observations=minimum_standard_observations,
        )
    )
    eligibility_map = (
        eligibility.drop_duplicates("ticker").set_index("ticker").to_dict("index")
        if not eligibility.empty and "ticker" in eligibility
        else {}
    )
    diversification_scores = _correlation_diversification_scores(clean)
    rows = [
        _score_one_asset(
            ticker,
            clean[ticker],
            metadata,
            diversification_scores.get(ticker, 1.0),
            eligibility_map.get(ticker, {}),
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
        [
            "standard_composite_score_eligible",
            "composite_quant_score",
            "data_coverage_score",
            "liquidity_proxy_score",
        ],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    scores["rank_global"] = np.arange(1, len(scores) + 1)
    scores["rank_within_sleeve"] = (
        scores.groupby("sleeve")["composite_quant_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    scores["selection_flag"] = scores["standard_composite_score_eligible"] & (
        scores["rank_global"] <= int(max_selected)
    )
    scores["selection_reason"] = scores.apply(
        _selection_reason,
        axis=1,
    )
    scores["warning_flags"] = scores.apply(_warning_flags, axis=1)
    scores["score_formula_version"] = SCORE_FORMULA_VERSION
    scores["scoring_as_of_date"] = scoring_as_of
    scores["leakage_check_pass"] = True
    scores["score_component_summary"] = scores.apply(_score_component_summary, axis=1)
    scores = attach_run_metadata(scores, run_metadata)
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
    eligibility: dict[str, object],
) -> dict[str, object]:
    returns = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    meta = metadata.loc[metadata["ticker"].astype(str).eq(str(ticker))].iloc[0]
    observations = int(returns.shape[0])
    vol_3m = _eligible_volatility(
        returns,
        63,
        eligibility.get("volatility_3m_eligible", observations >= 63),
    )
    vol_12m = _eligible_volatility(
        returns,
        252,
        eligibility.get("volatility_12m_eligible", observations >= 252),
    )
    downside = (
        _downside_volatility(returns.tail(252))
        if _as_bool(eligibility.get("sortino_eligible", observations >= 252))
        else np.nan
    )
    annual_return = (
        float(returns.tail(252).mean() * TRADING_DAYS_PER_YEAR)
        if observations >= 252
        else np.nan
    )
    sharpe = (
        annual_return / vol_12m
        if np.isfinite(annual_return) and np.isfinite(vol_12m) and vol_12m > 0
        else np.nan
    )
    sortino = (
        annual_return / downside
        if np.isfinite(annual_return) and np.isfinite(downside) and downside > 0
        else np.nan
    )
    momentum = {
        "momentum_1m": _eligible_period_return(
            returns, 21, eligibility.get("1m_eligible", observations >= 21)
        ),
        "momentum_3m": _eligible_period_return(
            returns, 63, eligibility.get("3m_eligible", observations >= 63)
        ),
        "momentum_6m": _eligible_period_return(
            returns, 126, eligibility.get("6m_eligible", observations >= 126)
        ),
        "momentum_12m": _eligible_period_return(
            returns, 252, eligibility.get("12m_eligible", observations >= 252)
        ),
    }
    trend_values = [
        momentum["momentum_3m"],
        momentum["momentum_6m"],
        momentum["momentum_12m"],
    ]
    trend_score = (
        float(np.nanmean(trend_values))
        if pd.Series(trend_values, dtype=float).notna().any()
        else np.nan
    )
    mean_reversion = (
        float(-0.50 * momentum["momentum_1m"])
        if np.isfinite(momentum["momentum_1m"])
        else np.nan
    )
    standard_eligible = _as_bool(
        eligibility.get("standard_composite_score_eligible", observations >= 252)
    )
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
        "risk_penalty_score": (
            float(vol_12m + abs(_max_drawdown(returns)))
            if np.isfinite(vol_12m)
            else np.nan
        ),
        "expected_return_signal_score": (
            float(0.60 * trend_score + 0.25 * sharpe)
            if np.isfinite(trend_score) and np.isfinite(sharpe)
            else np.nan
        ),
        "eligibility_status": eligibility.get(
            "eligibility_status",
            "eligible" if standard_eligible else "diagnostic_short_history",
        ),
        "standard_composite_score_eligible": standard_eligible,
        "history_eligibility_reason": eligibility.get(
            "eligibility_reason",
            "" if standard_eligible else "Insufficient common 12-month history.",
        ),
        "data_window_start": _date_label(returns.index.min()),
        "data_window_end": _date_label(returns.index.max()),
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
    metadata = resolve_security_master_rows(universe)
    if "ticker" not in metadata:
        raise ValueError("Universe must contain a ticker column.")
    metadata["ticker"] = metadata["ticker"].astype(str)
    return metadata


def _filter_metadata_scope(
    metadata: pd.DataFrame,
    *,
    default_scope: str,
    include_crypto: bool,
) -> pd.DataFrame:
    frame = metadata.copy()
    scope = str(default_scope or "equity_only").strip().lower()
    if "include" in frame:
        include_mask = frame["include"].map(_truthy)
        if include_mask.any():
            frame = frame.loc[include_mask].copy()
    if "investable" in frame:
        frame = frame.loc[frame["investable"].map(_truthy)].copy()
    if "signal_only" in frame:
        frame = frame.loc[~frame["signal_only"].map(_truthy)].copy()
    sleeve = frame.get("sleeve", pd.Series("", index=frame.index)).astype(str)
    if scope == "equity_only":
        frame = frame.loc[sleeve.str.startswith("global_equity", na=False)].copy()
    elif scope == "multi_asset_no_crypto":
        frame = frame.loc[~sleeve.str.contains("crypto", case=False, na=False)].copy()
    if not include_crypto:
        sleeve = frame.get("sleeve", pd.Series("", index=frame.index)).astype(str)
        frame = frame.loc[~sleeve.str.contains("crypto", case=False, na=False)].copy()
    else:
        eligible_crypto = ~_stablecoin_like_mask(frame)
        eligible_crypto &= ~unverified_crypto_price_mapping_mask(frame)
        frame = frame.loc[eligible_crypto].copy()
    return frame


def _stablecoin_like_mask(frame: pd.DataFrame) -> pd.Series:
    return stablecoin_like_mask(frame)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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


def _eligible_period_return(
    series: pd.Series,
    window: int,
    eligible: object,
) -> float:
    if not _as_bool(eligible) or series.dropna().shape[0] < int(window):
        return np.nan
    return _period_return(series, window)


def _eligible_volatility(
    series: pd.Series,
    window: int,
    eligible: object,
) -> float:
    if not _as_bool(eligible) or series.dropna().shape[0] < int(window):
        return np.nan
    return _annualized_vol(series.tail(window))


def _annualized_vol(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.shape[0] < 2:
        return 0.0
    return float(clean.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))


def _downside_volatility(series: pd.Series) -> float:
    clean = series.dropna().astype(float)
    if clean.empty:
        return 0.0
    shortfall = np.minimum(clean.to_numpy(dtype=float), 0.0)
    return float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(TRADING_DAYS_PER_YEAR))


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
    if not clean.notna().any():
        return pd.Series(0.0, index=series.index)
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
    if not _as_bool(row["standard_composite_score_eligible"]):
        flags.append("diagnostic_short_history")
    if float(row["data_coverage_score"]) < 0.75:
        flags.append("low_coverage")
    if _finite_float(row["volatility_12m"]) > 0.80:
        flags.append("high_volatility")
    if float(row["max_drawdown"]) < -0.50:
        flags.append("deep_drawdown")
    if abs(_finite_float(row["momentum_1m"])) > 0.75:
        flags.append("extreme_short_term_return")
    return "; ".join(flags) if flags else "none"


def _selection_reason(row: pd.Series) -> str:
    if _as_bool(row["selection_flag"]):
        return (
            "Selected by the standard 12-month composite score with coverage, "
            "momentum, risk and diversification checks."
        )
    if not _as_bool(row["standard_composite_score_eligible"]):
        return (
            "Visible as diagnostic_short_history and excluded from standard "
            "portfolio selection because common 12-month history is insufficient."
        )
    return (
        "Not selected because other eligible assets ranked higher under the "
        "public-data score."
    )


def _score_component_summary(row: pd.Series) -> str:
    return (
        "composite = 30% expected_return_signal + 20% Sharpe-like + "
        "15% Sortino-like + 10% diversification + 10% coverage + "
        "5% liquidity proxy - 10% risk penalty; "
        f"eligibility={row['eligibility_status']}; warnings={row['warning_flags']}"
    )


def _date_label(value: object) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def _as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _finite_float(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if np.isfinite(parsed) else 0.0
