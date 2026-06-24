"""
Return Distribution Analysis & Statistical Testing
====================================================
Normality tests, distribution fitting, rolling statistics,
volatility clustering analysis, and stylized facts detection.
"""

import pandas as pd
import numpy as np
from scipy import stats
from arch import arch_model
from statsmodels.stats.diagnostic import acorr_ljungbox
import logging
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)


class ReturnAnalyzer:
    """Comprehensive return distribution analysis for multi-asset portfolios."""

    def __init__(self, returns: pd.DataFrame, asset_class_map: Optional[Dict] = None):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Daily simple returns (assets as columns)
        asset_class_map : dict, optional
            Mapping of ticker -> asset class name
        """
        self.returns = returns.dropna(how="all")
        self.asset_class_map = asset_class_map or {}
        self.tickers = list(returns.columns)

    # ------------------------------------------------------------------
    # 1. Normality Tests
    # ------------------------------------------------------------------
    def normality_tests(self, alpha: float = 0.05) -> pd.DataFrame:
        """
        Run multiple normality tests on each asset's return distribution.

        Tests applied:
        - Jarque-Bera: tests skewness and kurtosis jointly
        - Shapiro-Wilk: powerful for smaller samples (uses subsample if n > 5000)
        - Anderson-Darling: emphasis on distribution tails
        - D'Agostino-Pearson (K²): tests skewness and kurtosis separately

        Returns DataFrame with test statistics, p-values, and pass/fail at given alpha.
        """
        results = []
        for ticker in self.tickers:
            r = self.returns[ticker].dropna().values
            n = len(r)
            row = {"Ticker": ticker, "N": n}

            # Jarque-Bera
            jb_stat, jb_p = stats.jarque_bera(r)
            row["JB_stat"] = jb_stat
            row["JB_pvalue"] = jb_p
            row["JB_normal"] = jb_p > alpha

            # Shapiro-Wilk (subsample if too large)
            sw_sample = r if n <= 5000 else np.random.choice(r, 5000, replace=False)
            sw_stat, sw_p = stats.shapiro(sw_sample)
            row["SW_stat"] = sw_stat
            row["SW_pvalue"] = sw_p
            row["SW_normal"] = sw_p > alpha

            # Anderson-Darling
            ad_result = stats.anderson(r, dist="norm")
            # Use the 5% significance level (index 2)
            ad_critical = ad_result.critical_values[2]
            row["AD_stat"] = ad_result.statistic
            row["AD_critical_5pct"] = ad_critical
            row["AD_normal"] = ad_result.statistic < ad_critical

            # D'Agostino-Pearson K²
            if n >= 20:
                k2_stat, k2_p = stats.normaltest(r)
                row["K2_stat"] = k2_stat
                row["K2_pvalue"] = k2_p
                row["K2_normal"] = k2_p > alpha
            else:
                row["K2_stat"] = np.nan
                row["K2_pvalue"] = np.nan
                row["K2_normal"] = np.nan

            # Summary: how many tests say normal?
            normals = [row["JB_normal"], row["SW_normal"], row["AD_normal"]]
            if pd.notna(row.get("K2_normal", np.nan)):
                normals.append(row["K2_normal"])
            row["Tests_Passed"] = sum(normals)
            row["Total_Tests"] = len(normals)

            results.append(row)

        df = pd.DataFrame(results).set_index("Ticker")
        logger.info(
            f"Normality tests: {(df['Tests_Passed'] == df['Total_Tests']).sum()}/{len(df)} assets pass all tests"
        )
        return df

    # ------------------------------------------------------------------
    # 2. Distribution Fitting
    # ------------------------------------------------------------------
    def fit_distributions(
        self, distributions: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Fit multiple distributions to each asset's returns and compare via
        AIC (Akaike Information Criterion) and KS test.

        Distributions fitted:
        - Normal (Gaussian)
        - Student-t (captures heavy tails)
        - Skewed Student-t (captures asymmetry + heavy tails)
        - Generalized Extreme Value (GEV)
        - Stable (alpha-stable, Lévy)

        Returns DataFrame with fitted parameters, log-likelihood, AIC, and KS p-values.
        """
        if distributions is None:
            distributions = ["norm", "t", "skewnorm", "gennorm", "laplace"]

        results = []
        for ticker in self.tickers:
            r = self.returns[ticker].dropna().values
            n = len(r)
            best_aic = np.inf
            best_dist = None

            for dist_name in distributions:
                try:
                    dist = getattr(stats, dist_name)
                    params = dist.fit(r)
                    log_lik = np.sum(dist.logpdf(r, *params))
                    k = len(params)
                    aic = 2 * k - 2 * log_lik
                    bic = k * np.log(n) - 2 * log_lik

                    # KS test
                    ks_stat, ks_p = stats.kstest(r, dist_name, args=params)

                    row = {
                        "Ticker": ticker,
                        "Distribution": dist_name,
                        "Params": params,
                        "LogLik": log_lik,
                        "AIC": aic,
                        "BIC": bic,
                        "KS_stat": ks_stat,
                        "KS_pvalue": ks_p,
                        "N_params": k,
                    }
                    results.append(row)

                    if aic < best_aic:
                        best_aic = aic
                        best_dist = dist_name

                except Exception as e:
                    logger.warning(f"Failed to fit {dist_name} for {ticker}: {e}")

        df = pd.DataFrame(results)
        logger.info(
            f"Fitted {len(distributions)} distributions for {len(self.tickers)} assets"
        )
        return df

    def best_fit_summary(
        self, fit_results: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Return the best-fitting distribution per asset (lowest AIC)."""
        if fit_results is None:
            fit_results = self.fit_distributions()

        best = fit_results.loc[fit_results.groupby("Ticker")["AIC"].idxmin()]
        return best[
            ["Ticker", "Distribution", "AIC", "BIC", "KS_stat", "KS_pvalue"]
        ].set_index("Ticker")

    # ------------------------------------------------------------------
    # 3. Higher Moments Analysis
    # ------------------------------------------------------------------
    def higher_moments(self) -> pd.DataFrame:
        """
        Compute distribution shape metrics for each asset:
        - Skewness (Fisher)
        - Excess Kurtosis
        - Jarque-Bera statistic
        - Tail ratio (95th percentile / 5th percentile, absolute)
        """
        rows = []
        for ticker in self.tickers:
            r = self.returns[ticker].dropna()
            skew = r.skew()
            kurt = r.kurtosis()  # excess kurtosis
            jb, jb_p = stats.jarque_bera(r)

            # Tail ratio
            p95 = np.abs(r.quantile(0.95))
            p05 = np.abs(r.quantile(0.05))
            tail_ratio = p95 / p05 if p05 != 0 else np.inf

            rows.append(
                {
                    "Ticker": ticker,
                    "Skewness": skew,
                    "Excess_Kurtosis": kurt,
                    "JB_Statistic": jb,
                    "JB_pvalue": jb_p,
                    "Tail_Ratio": tail_ratio,
                    "Left_Tail_5pct": r.quantile(0.05),
                    "Right_Tail_95pct": r.quantile(0.95),
                    "Asset_Class": self.asset_class_map.get(ticker, "unknown"),
                }
            )

        return pd.DataFrame(rows).set_index("Ticker")

    # ------------------------------------------------------------------
    # 4. Rolling Statistics
    # ------------------------------------------------------------------
    def rolling_statistics(
        self, window: int = 63, annualize: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Compute rolling return statistics.

        Parameters
        ----------
        window : int
            Rolling window in trading days (default 63 ≈ 3 months)
        annualize : bool
            Whether to annualize return and volatility

        Returns
        -------
        dict with keys: 'mean', 'volatility', 'sharpe', 'skewness', 'kurtosis'
        """
        factor = 252 if annualize else 1
        sqrt_factor = np.sqrt(252) if annualize else 1

        rolling_mean = self.returns.rolling(window).mean() * factor
        rolling_vol = self.returns.rolling(window).std() * sqrt_factor
        rolling_sharpe = rolling_mean / rolling_vol
        rolling_skew = self.returns.rolling(window).skew()
        rolling_kurt = self.returns.rolling(window).kurt()

        return {
            "mean": rolling_mean,
            "volatility": rolling_vol,
            "sharpe": rolling_sharpe,
            "skewness": rolling_skew,
            "kurtosis": rolling_kurt,
        }

    # ------------------------------------------------------------------
    # 5. Volatility Clustering (GARCH)
    # ------------------------------------------------------------------
    def fit_garch(self, ticker: str, p: int = 1, q: int = 1, dist: str = "t") -> Dict:
        """
        Fit a GARCH(p,q) model to detect volatility clustering.

        Parameters
        ----------
        ticker : str
            Asset ticker
        p, q : int
            GARCH order
        dist : str
            Error distribution ('normal', 't', 'skewt', 'ged')

        Returns
        -------
        dict with model results, conditional volatility, and persistence
        """
        r = self.returns[ticker].dropna() * 100  # arch expects percentage returns
        model = arch_model(r, vol="Garch", p=p, q=q, dist=dist, mean="AR", lags=1)
        result = model.fit(disp="off")

        cond_vol = result.conditional_volatility / 100  # back to decimal
        persistence = sum(result.params.filter(like="alpha")) + sum(
            result.params.filter(like="beta")
        )

        return {
            "summary": result.summary(),
            "params": result.params,
            "cond_vol": cond_vol,
            "persistence": persistence,
            "aic": result.aic,
            "bic": result.bic,
            "loglik": result.loglikelihood,
            "std_resid": result.std_resid,
        }

    def garch_summary(
        self, tickers: Optional[List[str]] = None, p: int = 1, q: int = 1
    ) -> pd.DataFrame:
        """
        Fit GARCH(p,q) across assets and return summary table with
        persistence, alpha, beta, and information criteria.
        """
        if tickers is None:
            tickers = self.tickers

        rows = []
        for ticker in tickers:
            try:
                result = self.fit_garch(ticker, p=p, q=q)
                params = result["params"]

                rows.append(
                    {
                        "Ticker": ticker,
                        "Omega": params.get("omega", np.nan),
                        "Alpha": params.filter(like="alpha").sum(),
                        "Beta": params.filter(like="beta").sum(),
                        "Persistence": result["persistence"],
                        "AIC": result["aic"],
                        "BIC": result["bic"],
                        "Asset_Class": self.asset_class_map.get(ticker, "unknown"),
                    }
                )
            except Exception as e:
                logger.warning(f"GARCH failed for {ticker}: {e}")

        return pd.DataFrame(rows).set_index("Ticker")

    # ------------------------------------------------------------------
    # 6. Stylized Facts Detection
    # ------------------------------------------------------------------
    def stylized_facts(self) -> Dict[str, pd.DataFrame]:
        """
        Test common stylized facts of financial returns:

        1. Fat tails: Excess kurtosis > 0
        2. Negative skewness: Skewness < 0 (for equities)
        3. Volatility clustering: Ljung-Box on squared returns
        4. Leverage effect: Correlation between returns and future volatility
        5. Mean reversion of volatility: Autocorrelation of absolute returns
        """
        rows = []
        for ticker in self.tickers:
            r = self.returns[ticker].dropna()
            n = len(r)

            # Fat tails
            kurt = r.kurtosis()
            fat_tails = kurt > 0

            # Skewness
            skew = r.skew()
            neg_skew = skew < 0

            # Volatility clustering: Ljung-Box on r²
            r_sq = r**2
            lb_result = acorr_ljungbox(r_sq, lags=[10], return_df=True)
            lb_stat = lb_result["lb_stat"].values[0]
            lb_p = lb_result["lb_pvalue"].values[0]
            vol_clustering = lb_p < 0.05

            # Leverage effect: corr(r_t, |r_{t+1}|)
            abs_r_shifted = r.abs().shift(-1)
            leverage_corr = r.corr(abs_r_shifted)
            leverage_effect = leverage_corr < -0.05

            # Mean reversion of vol: autocorrelation of |r| at lag 1
            abs_r_acf = r.abs().autocorr(lag=1)

            rows.append(
                {
                    "Ticker": ticker,
                    "Excess_Kurtosis": round(kurt, 4),
                    "Fat_Tails": fat_tails,
                    "Skewness": round(skew, 4),
                    "Negative_Skew": neg_skew,
                    "LB_Stat_r2": round(lb_stat, 2),
                    "LB_pvalue_r2": round(lb_p, 6),
                    "Vol_Clustering": vol_clustering,
                    "Leverage_Corr": (
                        round(leverage_corr, 4)
                        if not np.isnan(leverage_corr)
                        else np.nan
                    ),
                    "Leverage_Effect": leverage_effect,
                    "AbsReturn_ACF1": round(abs_r_acf, 4),
                    "Asset_Class": self.asset_class_map.get(ticker, "unknown"),
                }
            )

        df = pd.DataFrame(rows).set_index("Ticker")
        logger.info(
            f"Stylized facts: {df['Fat_Tails'].sum()}/{len(df)} fat tails, "
            f"{df['Vol_Clustering'].sum()}/{len(df)} vol clustering"
        )
        return df

    # ------------------------------------------------------------------
    # 7. QQ-Plot Data
    # ------------------------------------------------------------------
    def qq_data(
        self, ticker: str, dist: str = "norm"
    ) -> Tuple[np.ndarray, np.ndarray, float, float]:
        """
        Generate QQ-plot data points for a given asset against a theoretical distribution.

        Returns (theoretical_quantiles, sample_quantiles).
        """
        r = self.returns[ticker].dropna().values
        if dist == "norm":
            (theoretical, sample), (slope, intercept, _) = stats.probplot(
                r, dist="norm"
            )
        elif dist == "t":
            # Fit t-distribution first
            df_t, loc, scale = stats.t.fit(r)
            (theoretical, sample), (slope, intercept, _) = stats.probplot(
                r, dist=stats.t, sparams=(df_t,)
            )
        else:
            (theoretical, sample), (slope, intercept, _) = stats.probplot(r, dist=dist)

        return theoretical, sample, slope, intercept
