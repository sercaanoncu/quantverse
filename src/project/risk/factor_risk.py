"""
Factor Risk Decomposition
===========================
Decompose portfolio risk into systematic (factor) and
idiosyncratic (asset-specific) components.
"""

import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
import logging
from typing import Dict, Optional, List

from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


class FactorRiskDecomposer:
    """
    Decompose portfolio risk into factor contributions.

    Approaches:
    1. PCA-based statistical factors
    2. Asset-class factor model
    3. Marginal risk contributions
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        weights: pd.Series,
        asset_class_map: Optional[Dict] = None,
    ):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.weights = align_portfolio_weights(
            weights,
            self.tickers,
            context="Factor-risk portfolio",
        )
        self.asset_class_map = asset_class_map or {}

        self.portfolio_returns = pd.Series(
            self.returns.values @ self.weights.values, index=self.returns.index
        )

    # ------------------------------------------------------------------
    # 1. Marginal Risk Contribution
    # ------------------------------------------------------------------
    def marginal_risk_contribution(self) -> pd.DataFrame:
        """
        Compute each asset's contribution to portfolio volatility.

        MRC_i = w_i · (Σw)_i / σ_p
        Total Risk = Σ MRC_i = σ_p
        """
        Sigma = self.returns.cov().values * 252
        w = self.weights.values
        port_vol = np.sqrt(w @ Sigma @ w)
        if not np.isfinite(port_vol) or port_vol <= 1e-12:
            raise ValueError(
                "Marginal risk contribution is undefined for zero or invalid "
                "portfolio volatility"
            )

        marginal = Sigma @ w / port_vol  # ∂σ/∂w
        risk_contrib = w * marginal
        pct_contrib = risk_contrib / port_vol * 100

        return pd.DataFrame(
            {
                "Weight_%": w * 100,
                "Marginal_Risk": marginal,
                "Risk_Contribution": risk_contrib,
                "Pct_of_Risk": pct_contrib,
                "Asset_Class": [
                    self.asset_class_map.get(t, "unknown") for t in self.tickers
                ],
            },
            index=self.tickers,
        ).sort_values("Pct_of_Risk", ascending=False)

    # ------------------------------------------------------------------
    # 2. Asset Class Risk Attribution
    # ------------------------------------------------------------------
    def asset_class_risk(self) -> pd.DataFrame:
        """
        Aggregate risk contributions by asset class.
        """
        mrc = self.marginal_risk_contribution()

        ac_risk = (
            mrc.groupby("Asset_Class")
            .agg(
                {
                    "Weight_%": "sum",
                    "Risk_Contribution": "sum",
                    "Pct_of_Risk": "sum",
                }
            )
            .sort_values("Pct_of_Risk", ascending=False)
        )

        ac_risk["Risk_Weight_Ratio"] = ac_risk["Pct_of_Risk"] / ac_risk["Weight_%"]
        return ac_risk

    # ------------------------------------------------------------------
    # 3. PCA Factor Decomposition
    # ------------------------------------------------------------------
    def pca_factor_decomposition(self, n_factors: int = 5) -> Dict:
        """
        Decompose portfolio risk using PCA-extracted statistical factors.

        R_p = Σ β_k · F_k + ε

        Systematic risk = from factors
        Idiosyncratic risk = residual
        """
        pca = PCA(n_components=n_factors)
        factors = pca.fit_transform(self.returns.values)
        factor_df = pd.DataFrame(
            factors,
            index=self.returns.index,
            columns=[f"PC{i+1}" for i in range(n_factors)],
        )

        # Regress portfolio returns on factors
        reg = LinearRegression().fit(factor_df.values, self.portfolio_returns.values)
        betas = reg.coef_
        r_squared = reg.score(factor_df.values, self.portfolio_returns.values)

        # Factor risk contributions — use R² to ensure systematic + idiosyncratic = 100%
        total_var = np.var(self.portfolio_returns.values)
        systematic_var = r_squared * total_var
        idiosyncratic_var = (1 - r_squared) * total_var
        factor_var = np.var(factor_df.values, axis=0)

        factor_contributions = pd.DataFrame(
            {
                "Beta": betas,
                "Factor_Vol": np.sqrt(factor_var) * np.sqrt(252),
                "Var_Explained": pca.explained_variance_ratio_[:n_factors],
                "Risk_Contribution_%": (betas**2 * factor_var / total_var) * 100,
            },
            index=[f"PC{i+1}" for i in range(n_factors)],
        )

        return {
            "factor_contributions": factor_contributions,
            "r_squared": r_squared,
            "systematic_risk_%": systematic_var / total_var * 100,
            "idiosyncratic_risk_%": idiosyncratic_var / total_var * 100,
            "total_vol_annual": np.sqrt(total_var * 252),
            "systematic_vol_annual": np.sqrt(systematic_var * 252),
            "idiosyncratic_vol_annual": np.sqrt(max(idiosyncratic_var, 0) * 252),
        }

    # ------------------------------------------------------------------
    # 4. Risk Concentration Metrics
    # ------------------------------------------------------------------
    def concentration_metrics(self) -> Dict:
        """
        Compute portfolio concentration metrics:
        - HHI (Herfindahl-Hirschman Index) for weights and risk
        - Effective number of bets (ENB)
        - Diversification ratio
        """
        mrc = self.marginal_risk_contribution()
        w = self.weights.values
        Sigma = self.returns.cov().values * 252

        # Weight HHI
        hhi_weight = float((w**2).sum())

        # Risk HHI
        rc_pct = mrc["Pct_of_Risk"].values / 100
        hhi_risk = float((rc_pct**2).sum())

        # Effective number of bets
        enb_weight = 1 / hhi_weight if hhi_weight > 0 else len(w)
        enb_risk = 1 / hhi_risk if hhi_risk > 0 else len(w)

        # Diversification ratio
        weighted_vols = np.abs(w) * np.sqrt(np.diag(Sigma))
        port_vol = np.sqrt(w @ Sigma @ w)
        div_ratio = weighted_vols.sum() / port_vol if port_vol > 0 else 1

        return {
            "HHI_Weight": hhi_weight,
            "HHI_Risk": hhi_risk,
            "ENB_Weight": enb_weight,
            "ENB_Risk": enb_risk,
            "Diversification_Ratio": div_ratio,
            "N_Assets": len(w),
            "N_Active": int((np.abs(w) > 0.001).sum()),
        }
