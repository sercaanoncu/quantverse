"""
QuantVerse — Multi-Source Data Fetcher
=======================================
Handles downloading, caching, and managing financial data
from multiple sources (yfinance, etc.) across all asset classes.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging
import json
import hashlib

from .universe import AssetUniverse

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Multi-asset data fetcher with caching support.

    Fetches OHLCV data from yfinance for equities, ETFs, crypto,
    and commodities. Supports local caching to avoid redundant API calls.

    Parameters
    ----------
    universe : AssetUniverse
        The asset universe to fetch data for.
    cache_dir : str
        Directory to store cached data.
    start_date : str
        Start date for data download (YYYY-MM-DD).
    end_date : str or None
        End date for data download. None = today.
    """

    def __init__(
        self,
        universe: Optional[AssetUniverse] = None,
        cache_dir: str = "data/cache",
        start_date: str = "2015-01-01",
        end_date: Optional[str] = None,
    ):
        if universe is not None:
            self.universe = universe
        else:
            try:
                self.universe = AssetUniverse.from_config()
            except FileNotFoundError:
                self.universe = AssetUniverse.default()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # Storage for fetched data
        self._price_data: Optional[pd.DataFrame] = None
        self._volume_data: Optional[pd.DataFrame] = None
        self._metadata: Dict = {}

    def _cache_key(self, tickers: List[str]) -> str:
        """Generate a unique cache key based on tickers and date range."""
        key_str = f"{sorted(tickers)}_{self.start_date}_{self.end_date}"
        return hashlib.md5(key_str.encode()).hexdigest()[:12]

    def _get_cache_path(self, tickers: List[str], data_type: str) -> Path:
        """Get the cache file path for given parameters."""
        key = self._cache_key(tickers)
        return self.cache_dir / f"{data_type}_{key}.parquet"

    def _load_from_cache(
        self, tickers: List[str], data_type: str
    ) -> Optional[pd.DataFrame]:
        """Load data from cache if it exists and is fresh (< 24h old)."""
        cache_path = self._get_cache_path(tickers, data_type)
        if cache_path.exists():
            # Check if cache is fresh (less than 24 hours old)
            cache_age = datetime.now().timestamp() - cache_path.stat().st_mtime
            if cache_age < 86400:  # 24 hours
                logger.info(f"Loading {data_type} from cache: {cache_path.name}")
                return pd.read_parquet(cache_path)
        return None

    def _save_to_cache(self, df: pd.DataFrame, tickers: List[str], data_type: str):
        """Save data to parquet cache."""
        cache_path = self._get_cache_path(tickers, data_type)
        df.to_parquet(cache_path)
        logger.info(f"Cached {data_type}: {cache_path.name}")

    def fetch_prices(
        self,
        tickers: Optional[List[str]] = None,
        use_cache: bool = True,
        price_type: str = "Adj Close",
        include_signals: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch adjusted closing prices for all or selected tickers.

        Parameters
        ----------
        tickers : list of str, optional
            Specific tickers to fetch. None = all tickers in universe.
        use_cache : bool
            Whether to use local cache.
        price_type : str
            Price column to extract ('Adj Close', 'Close', 'Open', 'High', 'Low').
        include_signals : bool
            If True, include non-investable signal tickers such as VIX/yields.
            Portfolio construction defaults to investable assets only.

        Returns
        -------
        pd.DataFrame
            DataFrame with dates as index and tickers as columns.
        """
        if tickers is None:
            tickers = (
                self.universe.all_tickers
                if include_signals
                else self.universe.investable_tickers
            )

        # Try cache first
        if use_cache:
            cached = self._load_from_cache(tickers, "prices")
            if cached is not None:
                self._price_data = cached
                return cached

        logger.info(
            f"Downloading prices for {len(tickers)} assets "
            f"({self.start_date} to {self.end_date})..."
        )

        # Download in batches to handle large universes
        all_prices = {}
        failed_tickers = []
        batch_size = 20

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i : i + batch_size]
            try:
                data = yf.download(
                    batch,
                    start=self.start_date,
                    end=self.end_date,
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )

                # Determine the column to extract
                # With auto_adjust=True, yfinance renames "Adj Close" → "Close"
                col = "Close" if price_type == "Adj Close" else price_type

                if len(batch) == 1:
                    # yfinance returns single-level columns for 1 ticker
                    if col in data.columns:
                        all_prices[batch[0]] = data[col]
                    elif "Close" in data.columns:
                        all_prices[batch[0]] = data["Close"]
                else:
                    # Multi-ticker download returns multi-level columns
                    level0 = data.columns.get_level_values(0)
                    use_col = col if col in level0 else "Close"
                    if use_col in level0:
                        close_data = data[use_col]
                        for ticker in batch:
                            if ticker in close_data.columns:
                                series = close_data[ticker].dropna()
                                if len(series) > 0:
                                    all_prices[ticker] = series
                                else:
                                    failed_tickers.append(ticker)
                            else:
                                failed_tickers.append(ticker)

            except Exception as e:
                logger.warning(f"Failed to download batch {batch}: {e}")
                failed_tickers.extend(batch)

        if failed_tickers:
            logger.warning(f"Failed tickers ({len(failed_tickers)}): {failed_tickers}")

        # Combine into DataFrame
        prices = pd.DataFrame(all_prices)
        prices.index = pd.to_datetime(prices.index)
        prices = prices.sort_index()

        # Cache results
        if use_cache and not prices.empty:
            self._save_to_cache(prices, tickers, "prices")

        self._price_data = prices
        self._log_fetch_summary(prices, failed_tickers)

        return prices

    def fetch_signals(self, use_cache: bool = True) -> pd.DataFrame:
        """Fetch non-investable market signal series separately."""
        return self.fetch_prices(
            tickers=self.universe.signal_tickers,
            use_cache=use_cache,
            price_type="Adj Close",
            include_signals=True,
        )

    def fetch_ohlcv(
        self,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch full OHLCV data for selected tickers.

        Returns
        -------
        dict
            Mapping of ticker -> OHLCV DataFrame.
        """
        if tickers is None:
            tickers = self.universe.investable_tickers

        ohlcv_data = {}
        for ticker in tickers:
            try:
                data = yf.download(
                    ticker,
                    start=self.start_date,
                    end=self.end_date,
                    auto_adjust=True,
                    progress=False,
                )
                if not data.empty:
                    # Flatten multi-level columns if present
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)
                    ohlcv_data[ticker] = data
            except Exception as e:
                logger.warning(f"Failed to fetch OHLCV for {ticker}: {e}")

        return ohlcv_data

    def fetch_benchmark(self, benchmark: str = "SPY") -> pd.DataFrame:
        """Fetch benchmark data for comparison."""
        data = yf.download(
            benchmark,
            start=self.start_date,
            end=self.end_date,
            auto_adjust=True,
            progress=False,
        )
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data["Close"].to_frame(name=benchmark)

    def fetch_risk_free_rate(self, proxy: str = "^IRX") -> pd.Series:
        """
        Fetch risk-free rate proxy (13-week T-bill rate).

        Returns annualized daily risk-free rate as decimal.
        """
        try:
            data = yf.download(
                proxy,
                start=self.start_date,
                end=self.end_date,
                progress=False,
            )
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if data.empty or "Close" not in data:
                raise ValueError(f"empty risk-free data for {proxy}")
            # ^IRX is quoted in percentage, convert to daily decimal
            rf = data["Close"] / 100 / 252
            rf = rf.squeeze().dropna()
            if rf.empty:
                raise ValueError(
                    f"risk-free series has no valid observations for {proxy}"
                )
            return rf
        except Exception as exc:
            logger.warning("Could not fetch risk-free rate %s: %s", proxy, exc)
            raise RuntimeError(f"Could not fetch risk-free rate for {proxy}") from exc

    def _log_fetch_summary(self, prices: pd.DataFrame, failed: List[str]):
        """Log a summary of the fetch operation."""
        if prices.empty:
            logger.error("No data fetched!")
            return

        n_assets = prices.shape[1]
        n_days = prices.shape[0]
        date_range = f"{prices.index[0].strftime('%Y-%m-%d')} to {prices.index[-1].strftime('%Y-%m-%d')}"
        missing_pct = prices.isnull().sum().sum() / prices.size * 100

        logger.info(
            f"Fetched {n_assets} assets, {n_days} trading days ({date_range}). "
            f"Missing: {missing_pct:.1f}%. Failed: {len(failed)} tickers."
        )

    def get_asset_info(self, tickers: Optional[List[str]] = None) -> pd.DataFrame:
        """Get basic info (name, sector, market cap) for tickers."""
        if tickers is None:
            tickers = self.universe.investable_tickers[:10]  # Limit for speed

        info_list = []
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                info = t.info
                info_list.append(
                    {
                        "ticker": ticker,
                        "name": info.get("shortName", "N/A"),
                        "sector": info.get("sector", "N/A"),
                        "market_cap": info.get("marketCap", None),
                        "currency": info.get("currency", "USD"),
                    }
                )
            except Exception:
                info_list.append({"ticker": ticker, "name": "N/A"})

        return pd.DataFrame(info_list).set_index("ticker")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Quick test
    fetcher = DataFetcher(start_date="2020-01-01")
    prices = fetcher.fetch_prices(tickers=["SPY", "BTC-USD", "GLD", "TLT"])
    print(f"\nShape: {prices.shape}")
    print(f"\nLast 5 days:\n{prices.tail()}")
