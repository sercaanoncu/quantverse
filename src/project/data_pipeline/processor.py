"""
QuantVerse — Data Processor
=============================
Handles cleaning, alignment, missing data treatment, and
return and risk metric calculations from raw price data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Literal, Optional
import logging
import warnings

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Process raw price data into analysis-ready format.

    Handles:
    - Missing data detection and treatment
    - Date alignment across assets with different trading calendars
    - Return calculations (simple, log, multi-period)
    - Basic descriptive statistics
    - Outlier detection

    Parameters
    ----------
    prices : pd.DataFrame
        Raw price data (dates × tickers).
    """

    def __init__(self, prices: pd.DataFrame):
        if prices.empty:
            raise ValueError("Price DataFrame is empty!")
        self.raw_prices = prices.copy()
        self.prices: pd.DataFrame | None = None
        self.returns: pd.DataFrame | None = None
        self.log_returns: pd.DataFrame | None = None
        self._cleaning_report: Dict = {}

    # ─── Cleaning Pipeline ────────────────────────────────────────

    def clean(
        self,
        min_history_pct: float = 0.7,
        max_gap_days: int = 5,
        fill_method: str = "ffill",
        calendar: str = "business",
        drop_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Full cleaning pipeline.

        Parameters
        ----------
        min_history_pct : float
            Minimum percentage of non-null data required to keep an asset.
            Assets with more missing data than this threshold are dropped.
        max_gap_days : int
            Maximum consecutive missing days allowed. Gaps larger than
            this are flagged.
        fill_method : str
            Method for filling remaining gaps. ``'ffill'`` performs a bounded
            past-only carry; ``'none'`` leaves gaps unresolved.
        calendar : str
            'business' keeps Monday-Friday observations, matching 252-day
            annualization. 'calendar' keeps all dates for pure 7-day assets.
        drop_columns : list of str, optional
            Columns to remove before cleaning, e.g. non-investable signals.

        Returns
        -------
        pd.DataFrame
            Cleaned price data.
        """
        if isinstance(max_gap_days, bool):
            raise ValueError("max_gap_days must be a positive integer.")
        try:
            validated_gap_days = int(max_gap_days)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_gap_days must be a positive integer.") from exc
        if validated_gap_days <= 0 or validated_gap_days != max_gap_days:
            raise ValueError("max_gap_days must be a positive integer.")
        max_gap_days = validated_gap_days

        df = self.raw_prices.copy()
        date_index = pd.DatetimeIndex(pd.to_datetime(df.index))
        df.index = date_index
        df = df.sort_index()

        if drop_columns:
            df = df.drop(columns=[c for c in drop_columns if c in df.columns])

        if calendar == "business":
            sorted_index = pd.DatetimeIndex(df.index)
            df = df[sorted_index.dayofweek < 5]
        elif calendar != "calendar":
            raise ValueError("calendar must be 'business' or 'calendar'")

        report: dict[str, object] = {"original_shape": df.shape}

        # Step 1: Remove completely empty columns
        empty_cols = df.columns[df.isnull().all()].tolist()
        if empty_cols:
            df = df.drop(columns=empty_cols)
            logger.warning(f"Dropped {len(empty_cols)} empty columns: {empty_cols}")
        report["dropped_empty"] = empty_cols

        # Step 2: Drop assets with insufficient history
        coverage = df.notna().sum() / len(df)
        low_coverage = coverage[coverage < min_history_pct].index.tolist()
        if low_coverage:
            df = df.drop(columns=low_coverage)
            logger.warning(
                f"Dropped {len(low_coverage)} assets with <{min_history_pct*100}% "
                f"coverage: {low_coverage}"
            )
        report["dropped_low_coverage"] = low_coverage

        # Step 3: Detect large gaps
        gap_info = self._detect_gaps(df, max_gap_days)
        report["large_gaps"] = gap_info

        # Step 4: Forward-fill small gaps after calendar alignment.
        if fill_method == "ffill":
            df = df.ffill(limit=max_gap_days)
        elif fill_method == "interpolate":
            raise ValueError(
                "Time interpolation is prohibited in research inputs because "
                "an interior value can use a future endpoint. Use bounded "
                "'ffill' or 'none'."
            )
        elif fill_method not in (None, "none"):
            raise ValueError("fill_method must be 'ffill' or 'none'")

        # Step 5: Drop any remaining rows with NaN at the start
        first_valid = df.apply(lambda col: col.first_valid_index()).max()
        if first_valid is not None:
            df = df.loc[first_valid:]

        # Step 6: Fail closed on gaps that exceed the bounded fill policy.
        still_missing = df.columns[df.isnull().any()].tolist()
        if still_missing:
            for col in still_missing:
                df = df.drop(columns=[col])
                logger.warning(
                    "Dropped %s: missing prices remain after the bounded "
                    "%s policy; unbounded forward/backward filling is prohibited",
                    col,
                    fill_method,
                )

        report["final_shape"] = df.shape
        report["calendar"] = calendar
        report["date_range"] = (
            df.index[0].strftime("%Y-%m-%d"),
            df.index[-1].strftime("%Y-%m-%d"),
        )
        report["assets_retained"] = df.columns.tolist()

        self._cleaning_report = report
        self.prices = df

        logger.info(
            f"Cleaning complete: {report['original_shape']} → {report['final_shape']}. "
            f"Date range: {report['date_range'][0]} to {report['date_range'][1]}"
        )

        return df

    def _detect_gaps(self, df: pd.DataFrame, threshold: int) -> Dict:
        """Detect consecutive gaps larger than threshold."""
        gap_info = {}
        for col in df.columns:
            is_null = df[col].isnull()
            if not is_null.any():
                continue
            # Find consecutive null runs
            groups = (is_null != is_null.shift()).cumsum()
            null_runs = is_null.astype(int).groupby(groups).sum()
            large_gaps = null_runs[null_runs > threshold]
            if len(large_gaps) > 0:
                gap_info[col] = {
                    "max_gap": int(large_gaps.max()),
                    "n_large_gaps": len(large_gaps),
                }
        return gap_info

    # ─── Return Calculations ──────────────────────────────────────

    def compute_returns(
        self,
        method: str = "simple",
        period: int = 1,
    ) -> pd.DataFrame:
        """
        Compute returns from cleaned price data.

        Parameters
        ----------
        method : str
            'simple' for arithmetic returns: (P_t / P_{t-1}) - 1
            'log' for logarithmic returns: ln(P_t / P_{t-1})
        period : int
            Number of periods for return calculation.
            1 = daily, 5 = weekly, 21 = monthly.

        Returns
        -------
        pd.DataFrame
            Return series.
        """
        if self.prices is None:
            raise ValueError("Run .clean() first!")

        if method == "simple":
            returns = self.prices.pct_change(
                periods=period,
                fill_method=None,
            ).dropna()
        elif method == "log":
            ratio = self.prices / self.prices.shift(period)
            returns = pd.DataFrame(
                np.log(ratio.to_numpy(dtype=float)),
                index=ratio.index,
                columns=ratio.columns,
            ).dropna()
        else:
            raise ValueError(f"Unknown method: {method}. Use 'simple' or 'log'.")

        if period == 1:
            if method == "simple":
                self.returns = returns
            else:
                self.log_returns = returns

        return returns

    def compute_all_returns(self) -> Dict[str, pd.DataFrame]:
        """Compute daily simple, log, weekly, and monthly returns."""
        results = {}
        results["daily_simple"] = self.compute_returns("simple", 1)
        results["daily_log"] = self.compute_returns("log", 1)
        results["weekly"] = self.compute_returns("simple", 5)
        results["monthly"] = self.compute_returns("simple", 21)
        return results

    # ─── Annualization Helpers ────────────────────────────────────

    @staticmethod
    def annualize_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
        """Annualize the arithmetic mean daily simple return."""
        mean_daily = daily_returns.mean()
        return float(mean_daily) * trading_days

    @staticmethod
    def annualize_volatility(
        daily_returns: pd.Series, trading_days: int = 252
    ) -> float:
        """Annualize daily volatility."""
        return float(daily_returns.std()) * np.sqrt(trading_days)

    # ─── Descriptive Statistics ───────────────────────────────────

    def summary_statistics(
        self, returns: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Comprehensive summary statistics for all assets.

        Returns
        -------
        pd.DataFrame
            Statistics including annualized return, volatility,
            Sharpe ratio, skewness, kurtosis, max drawdown, etc.
        """
        returns = self._resolve_returns(returns)

        stats = pd.DataFrame(index=returns.columns)

        # Annualized metrics
        stats["Ann. Return (%)"] = returns.apply(
            lambda x: self.annualize_return(x) * 100
        )
        stats["Ann. Volatility (%)"] = returns.apply(
            lambda x: self.annualize_volatility(x) * 100
        )
        stats["Sharpe Ratio"] = stats["Ann. Return (%)"] / stats["Ann. Volatility (%)"]

        # Distribution metrics
        stats["Skewness"] = returns.skew()
        stats["Kurtosis"] = returns.kurtosis()  # Excess kurtosis
        stats["Min Daily (%)"] = returns.min() * 100
        stats["Max Daily (%)"] = returns.max() * 100

        # Drawdown
        stats["Max Drawdown (%)"] = returns.apply(lambda x: self._max_drawdown(x) * 100)

        # Risk metrics
        stats["VaR 95% (%)"] = returns.quantile(0.05) * 100
        stats["CVaR 95% (%)"] = returns.apply(
            lambda x: x[x <= x.quantile(0.05)].mean() * 100
        )

        # Positive/Negative days ratio
        stats["% Positive Days"] = (returns > 0).sum() / len(returns) * 100

        return stats.round(4)

    def _max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from return series."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax().clip(lower=1.0)
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())

    def compute_drawdown_series(
        self, returns: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Compute full drawdown time series for all assets."""
        returns = self._resolve_returns(returns)
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax().clip(lower=1.0)
        return (cumulative - running_max) / running_max

    # ─── Outlier Detection ────────────────────────────────────────

    def detect_outliers(
        self,
        returns: Optional[pd.DataFrame] = None,
        method: str = "zscore",
        threshold: float = 4.0,
    ) -> pd.DataFrame:
        """
        Detect outlier returns.

        Parameters
        ----------
        method : str
            'zscore' or 'iqr'
        threshold : float
            Z-score threshold (default 4.0) or IQR multiplier.

        Returns
        -------
        pd.DataFrame
            Boolean mask where True = outlier.
        """
        returns = self._resolve_returns(returns)

        if method == "zscore":
            z = (returns - returns.mean()) / returns.std()
            mask = z.abs() > threshold
            return pd.DataFrame(mask, index=returns.index, columns=returns.columns)
        elif method == "iqr":
            q1 = returns.quantile(0.25)
            q3 = returns.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            return (returns < lower) | (returns > upper)
        else:
            raise ValueError(f"Unknown method: {method}")

    # ─── Correlation Analysis ─────────────────────────────────────

    def correlation_matrix(
        self,
        returns: Optional[pd.DataFrame] = None,
        method: Literal["pearson", "kendall", "spearman"] = "pearson",
    ) -> pd.DataFrame:
        """Compute correlation matrix."""
        returns = self._resolve_returns(returns)
        return returns.corr(method=method)

    def rolling_correlation(
        self,
        asset1: str,
        asset2: str,
        window: int = 60,
        returns: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        """Compute rolling correlation between two assets."""
        returns = self._resolve_returns(returns)
        return returns[asset1].rolling(window).corr(returns[asset2])

    def _resolve_returns(
        self,
        returns: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """Return an explicit returns frame, computing daily returns if needed."""
        if returns is not None:
            return returns
        if self.returns is None:
            self.compute_returns()
        if self.returns is None:
            raise RuntimeError("Daily returns could not be computed.")
        return self.returns

    # ─── Export ───────────────────────────────────────────────────

    def get_cleaning_report(self) -> Dict:
        """Return the cleaning report from the last clean() call."""
        return self._cleaning_report

    def export_processed(self, output_dir: str = "data/processed"):
        """Export cleaned prices and returns to parquet files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if self.prices is not None:
            self.prices.to_parquet(out / "prices_clean.parquet")
        if self.returns is not None:
            self.returns.to_parquet(out / "returns_daily.parquet")
        if self.log_returns is not None:
            self.log_returns.to_parquet(out / "log_returns_daily.parquet")

        logger.info(f"Exported processed data to {output_dir}/")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Quick test with sample data
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    np.random.seed(42)
    sample = pd.DataFrame(
        np.random.randn(500, 3).cumsum(axis=0) + 100,
        index=dates,
        columns=["ASSET_A", "ASSET_B", "ASSET_C"],
    )

    processor = DataProcessor(sample)
    cleaned = processor.clean()
    returns = processor.compute_returns()
    stats = processor.summary_statistics()
    print("\nSummary Statistics:")
    print(stats.to_string())
