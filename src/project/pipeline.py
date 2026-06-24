"""End-to-end QuantVerse production pipeline.

This module rebuilds the analysis artifacts without relying on notebook state.
Asset inclusion is based on investability and data quality, not realized return.
"""

from __future__ import annotations

import json
import logging
import pickle
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from project.backtest import PortfolioBacktester
from project.backtest.rebalancing import TransactionCosts
from project.config import load_config
from project.covariance.estimators import CovarianceEstimator
from project.data_pipeline.fetcher import DataFetcher
from project.data_pipeline.processor import DataProcessor
from project.data_pipeline.universe import AssetUniverse
from project.ml import evaluate_downside_risk_model, save_downside_risk_figures
from project.optimization import (
    CVaROptimizer,
    HRPOptimizer,
    MeanVarianceOptimizer,
    PortfolioConstraints,
    RiskParityOptimizer,
)
from project.regime import (
    AdaptiveAllocator,
    ClusteringRegimeDetector,
    HMMRegimeDetector,
    VolatilityRegimeDetector,
)
from project.risk import DrawdownAnalyzer, FactorRiskDecomposer, VaRCVaRCalculator

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for a reproducible QuantVerse run."""

    config_path: Optional[str] = "configs/base.yaml"
    start_date: str = "2015-01-01"
    end_date: Optional[str] = None
    cache_dir: str = "data/cache"
    output_dir: str = "data/processed"
    notebook_output_dir: str = "notebooks/data/processed"
    risk_free_rate: Optional[float] = None
    risk_free_proxy: str = "^IRX"
    fallback_risk_free_rate: float = 0.04
    expected_return_shrinkage: float = 0.50
    max_position_weight: float = 0.25
    min_history_pct: float = 0.70
    train_window: int = 504
    rebal_frequency: int = 63
    transaction_cost_proportional: float = 0.0010
    transaction_cost_spread: float = 0.0005
    mirror_notebook_data: bool = True
    primary_selection_rule: str = "walk_forward_oos_sharpe"
    reports_root_dir: str = "reports"
    reports_tables_dir: str = "reports/tables"
    reports_figures_dir: str = "reports/figures"
    pdf_output_path: str = "output/pdf/quantverse_analysis_report.pdf"
    adaptive_train_window: int = 252
    adaptive_rebal_frequency: int = 21
    ml_enabled: bool = True
    ml_n_splits: int = 5
    ml_event_quantile: float = 0.10
    ml_event_lookback: int = 252
    ml_min_train_size: int = 504
    random_seed: int = 42

    @classmethod
    def from_yaml(
        cls,
        config_path: str = "configs/base.yaml",
        **overrides,
    ) -> "PipelineConfig":
        """Build pipeline configuration from the canonical YAML file."""
        loaded = load_config(config_path)
        values = loaded.pipeline_kwargs()
        values.update(
            {key: value for key, value in overrides.items() if value is not None}
        )
        return cls(**values)


def run_full_pipeline(config: Optional[PipelineConfig] = None) -> Dict:
    """Run data, optimization, risk, backtest, and regime analysis."""
    config = config or PipelineConfig()
    np.random.seed(config.random_seed)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    Path(config.reports_tables_dir).mkdir(parents=True, exist_ok=True)
    Path(config.reports_figures_dir).mkdir(parents=True, exist_ok=True)

    if config.config_path:
        loaded_config = load_config(config.config_path)
        universe = AssetUniverse.from_config(str(loaded_config.path))
    else:
        universe = AssetUniverse.default()
    fetcher = DataFetcher(
        universe=universe,
        cache_dir=config.cache_dir,
        start_date=config.start_date,
        end_date=config.end_date,
    )
    prices = fetcher.fetch_prices(use_cache=True)
    if prices.empty:
        raise RuntimeError("No price data fetched")

    risk_free_rate, risk_free_meta = _resolve_risk_free_rate(fetcher, config)

    processor = DataProcessor(prices)
    cleaned = processor.clean(
        min_history_pct=config.min_history_pct,
        calendar="business",
    )
    returns = processor.compute_returns("simple")
    processor.compute_returns("log")
    processor.export_processed(str(output_dir))

    class_map = _write_asset_class_map(output_dir, universe, cleaned.columns)
    data_quality = _write_data_quality_artifacts(
        output_dir=output_dir,
        reports_tables_dir=Path(config.reports_tables_dir),
        reports_figures_dir=Path(config.reports_figures_dir),
        prices=prices,
        cleaned=cleaned,
        returns=returns,
        universe=universe,
    )
    signal_meta = _write_signal_artifacts(fetcher, output_dir, returns.index)
    market_signals_path = output_dir / "market_signals.parquet"
    market_signals = (
        pd.read_parquet(market_signals_path) if market_signals_path.exists() else None
    )
    cov_annual = _build_covariance_artifacts(output_dir, returns)
    expected_returns = _build_expected_return_artifacts(
        output_dir=output_dir,
        returns=returns,
        shrinkage=config.expected_return_shrinkage,
    )
    constraints = PortfolioConstraints.default_long_only(
        max_weight=config.max_position_weight
    )

    portfolios = _build_portfolios(
        returns=returns,
        expected_returns=expected_returns,
        cov_annual=cov_annual,
        constraints=constraints,
        risk_free_rate=risk_free_rate,
    )
    weights, portfolio_summary = _write_portfolio_artifacts(
        output_dir, returns, portfolios, class_map
    )
    risk_metrics = _write_risk_artifacts(output_dir, returns, weights, class_map)
    backtests = _write_backtest_artifacts(
        output_dir, returns, class_map, config, risk_free_rate
    )
    diagnostics = _write_diagnostic_artifacts(
        output_dir, portfolio_summary, backtests, config
    )
    regimes = _write_regime_artifacts(
        output_dir, returns, class_map, config, risk_free_rate
    )
    ml_summary = _write_ml_artifacts(output_dir, returns, market_signals, config)

    metadata = {
        "config_path": str(config.config_path) if config.config_path else None,
        "prices_shape": list(cleaned.shape),
        "returns_shape": list(returns.shape),
        "date_range": [str(returns.index[0].date()), str(returns.index[-1].date())],
        "data_as_of": str(returns.index[-1].date()),
        "risk_free_rate": risk_free_rate,
        "risk_free_metadata": risk_free_meta,
        "expected_return_shrinkage": config.expected_return_shrinkage,
        "max_position_weight": config.max_position_weight,
        "train_window": config.train_window,
        "rebal_frequency": config.rebal_frequency,
        "transaction_cost_proportional": config.transaction_cost_proportional,
        "transaction_cost_spread": config.transaction_cost_spread,
        "primary_selection_rule": config.primary_selection_rule,
        "weekend_rows": int((returns.index.dayofweek >= 5).sum()),
        "signals_in_returns": [
            ticker for ticker in universe.signal_tickers if ticker in returns.columns
        ],
        "signal_metadata": signal_meta,
        "dropped_assets": sorted(
            set(universe.investable_tickers) - set(cleaned.columns)
        ),
        "drop_reason": (
            "Dropped assets failed the minimum history coverage rule; assets are "
            "not dropped because realized return was low."
        ),
        "portfolio_count": int(len(portfolio_summary)),
        "risk_metric_count": int(len(risk_metrics)),
        "backtest_count": int(len(backtests)),
        "diagnostic_count": int(len(diagnostics)),
        "regime_columns": list(regimes.get("regime_labels", pd.DataFrame()).columns),
        "data_quality_rows": int(len(data_quality)),
        "ml_downside_risk": ml_summary,
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    if config.mirror_notebook_data:
        _mirror_notebook_processed_data(output_dir, Path(config.notebook_output_dir))

    logger.info("QuantVerse pipeline complete: %s", metadata)
    return metadata


def _write_asset_class_map(
    output_dir: Path,
    universe: AssetUniverse,
    columns: pd.Index,
) -> Dict[str, str]:
    class_map = universe.get_asset_class_map()
    investable_map = {
        ticker: asset_class
        for ticker, asset_class in class_map.items()
        if ticker in columns and asset_class != "signals"
    }
    with open(output_dir / "asset_class_map.json", "w", encoding="utf-8") as f:
        json.dump(investable_map, f, indent=2)
    return investable_map


def _write_data_quality_artifacts(
    output_dir: Path,
    reports_tables_dir: Path,
    reports_figures_dir: Path,
    prices: pd.DataFrame,
    cleaned: pd.DataFrame,
    returns: pd.DataFrame,
    universe: AssetUniverse,
) -> pd.DataFrame:
    """Write data quality tables and an availability matrix."""
    rows = []
    analysis_end = returns.index[-1] if not returns.empty else prices.index.max()
    total_raw_rows = max(len(prices), 1)

    for ticker in universe.investable_tickers:
        raw = prices[ticker] if ticker in prices.columns else pd.Series(dtype=float)
        raw_valid = raw.dropna()
        included = ticker in returns.columns
        first_valid = (
            raw_valid.index[0].date().isoformat() if not raw_valid.empty else None
        )
        last_valid = (
            raw_valid.index[-1].date().isoformat() if not raw_valid.empty else None
        )
        stale_days = (
            int((analysis_end - raw_valid.index[-1]).days)
            if not raw_valid.empty
            else None
        )
        coverage_pct = float(raw_valid.shape[0] / total_raw_rows * 100)
        if included:
            reason = "included"
        elif raw_valid.empty:
            reason = "provider_missing_or_empty"
        else:
            reason = "failed_min_history_or_cleaning_rule"

        rows.append(
            {
                "Ticker": ticker,
                "Asset_Class": universe.get_asset_class_map().get(ticker, "unknown"),
                "Raw_Observations": int(raw_valid.shape[0]),
                "Raw_Coverage_Pct": coverage_pct,
                "First_Valid_Date": first_valid,
                "Last_Valid_Date": last_valid,
                "Stale_Days_At_Analysis_End": stale_days,
                "Included_In_Returns": bool(included),
                "Return_Observations": (
                    int(returns[ticker].dropna().shape[0]) if included else 0
                ),
                "Decision_Reason": reason,
            }
        )

    quality = pd.DataFrame(rows).sort_values(
        ["Included_In_Returns", "Ticker"], ascending=[False, True]
    )
    quality.to_parquet(output_dir / "data_quality_report.parquet")
    quality.to_csv(output_dir / "data_quality_report.csv", index=False)
    reports_tables_dir.mkdir(parents=True, exist_ok=True)
    quality.to_csv(reports_tables_dir / "data_quality_report.csv", index=False)

    _plot_availability_matrix(
        prices=prices,
        tickers=universe.investable_tickers,
        output_dir=output_dir,
        reports_figures_dir=reports_figures_dir,
    )
    return quality


def _plot_availability_matrix(
    prices: pd.DataFrame,
    tickers: list[str],
    output_dir: Path,
    reports_figures_dir: Path,
) -> None:
    """Save a compact data availability heatmap."""
    available = [ticker for ticker in tickers if ticker in prices.columns]
    if not available or prices.empty:
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap

        matrix = prices[available].notna().T.astype(int)
        fig_height = max(5.0, len(available) * 0.18)
        fig, ax = plt.subplots(figsize=(12, fig_height))
        ax.imshow(
            matrix.values,
            aspect="auto",
            interpolation="nearest",
            cmap=ListedColormap(["#f2b6a0", "#2f6f4f"]),
        )
        ax.set_yticks(range(len(available)))
        ax.set_yticklabels(available, fontsize=7)
        step = max(1, len(matrix.columns) // 8)
        x_positions = list(range(0, len(matrix.columns), step))
        ax.set_xticks(x_positions)
        ax.set_xticklabels(
            [str(matrix.columns[pos].date()) for pos in x_positions],
            rotation=35,
            ha="right",
            fontsize=7,
        )
        ax.set_title("Investable universe data availability")
        ax.set_xlabel("Date")
        ax.set_ylabel("Ticker")
        fig.tight_layout()
        reports_figures_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_figures_dir / "data_availability_matrix.png"
        fig.savefig(report_path, dpi=160, bbox_inches="tight")
        fig.savefig(
            output_dir / "data_availability_matrix.png", dpi=160, bbox_inches="tight"
        )
        plt.close(fig)
    except Exception as exc:  # pragma: no cover - visual artifact only
        logger.warning("Data availability plot skipped: %s", exc)


def _resolve_risk_free_rate(
    fetcher: DataFetcher,
    config: PipelineConfig,
) -> tuple[float, Dict]:
    """Use a current market proxy unless the caller explicitly fixes the rate."""
    if config.risk_free_rate is not None:
        return float(config.risk_free_rate), {
            "source": "manual_config",
            "proxy": None,
            "quote_date": None,
            "quote_percent": None,
        }

    try:
        daily = fetcher.fetch_risk_free_rate(proxy=config.risk_free_proxy)
        if isinstance(daily, pd.Series):
            daily = daily.dropna()
            if daily.empty:
                raise ValueError("empty risk-free series")
            last_daily = float(daily.iloc[-1])
            annual = (1.0 + last_daily) ** 252 - 1.0
            quote_date = str(daily.index[-1].date())
        else:
            last_daily = float(daily)
            annual = (1.0 + last_daily) ** 252 - 1.0
            quote_date = None

        return annual, {
            "source": "yfinance",
            "proxy": config.risk_free_proxy,
            "quote_date": quote_date,
            "quote_percent": annual * 100,
        }
    except Exception as exc:  # pragma: no cover - network/provider dependent
        fallback = float(config.fallback_risk_free_rate)
        logger.warning("Risk-free rate fallback used: %s", exc)
        return fallback, {
            "source": "fallback",
            "proxy": config.risk_free_proxy,
            "quote_date": None,
            "quote_percent": fallback * 100,
            "reason": str(exc),
        }


def _write_signal_artifacts(
    fetcher: DataFetcher,
    output_dir: Path,
    analysis_index: pd.Index,
) -> Dict:
    """Save non-investable market signals separately from portfolio returns."""
    try:
        signals = fetcher.fetch_signals(use_cache=True)
        if signals.empty:
            raise ValueError("empty signal data")
        signals = signals.sort_index().loc[: analysis_index[-1]].ffill()
        signals = signals.loc[signals.index >= analysis_index[0]]
        signals.to_parquet(output_dir / "market_signals.parquet")
        return {
            "columns": list(signals.columns),
            "date_range": [
                str(signals.index[0].date()),
                str(signals.index[-1].date()),
            ],
            "included_in_portfolio": False,
        }
    except Exception as exc:  # pragma: no cover - network/provider dependent
        logger.warning("Market signals skipped: %s", exc)
        return {"columns": [], "date_range": None, "error": str(exc)}


def _build_covariance_artifacts(
    output_dir: Path, returns: pd.DataFrame
) -> pd.DataFrame:
    estimator = CovarianceEstimator(returns)
    cov_results = estimator.estimate_all()
    with open(output_dir / "covariance_estimates.pkl", "wb") as f:
        pickle.dump(cov_results, f)
    lw_daily = cov_results["Ledoit-Wolf"]["covariance"]
    lw_daily.to_parquet(output_dir / "covariance_lw.parquet")
    return lw_daily * 252


def _build_expected_return_artifacts(
    output_dir: Path,
    returns: pd.DataFrame,
    shrinkage: float,
) -> pd.Series:
    """Estimate annual returns with cross-sectional shrinkage to reduce noise."""
    if not 0.0 <= shrinkage <= 1.0:
        raise ValueError("expected_return_shrinkage must be between 0 and 1")

    raw = returns.mean() * 252
    target = float(raw.median())
    shrunk = (1.0 - shrinkage) * raw + shrinkage * target
    table = pd.DataFrame(
        {
            "Raw_Historical_Mean_Annual": raw,
            "Shrinkage_Target_Median": target,
            "Shrinkage": shrinkage,
            "Production_Estimate": shrunk,
        }
    )
    table.to_parquet(output_dir / "expected_returns.parquet")
    return shrunk


def _build_portfolios(
    returns: pd.DataFrame,
    expected_returns: pd.Series,
    cov_annual: pd.DataFrame,
    constraints: PortfolioConstraints,
    risk_free_rate: float,
) -> Dict[str, Dict]:
    portfolios: Dict[str, Dict] = {}

    def record(name: str, fn) -> None:
        portfolios[name] = fn()
        result = portfolios[name]
        logger.info(
            "%s: return=%.2f%% vol=%.2f%% sharpe=%.2f max_w=%.2f%%",
            name,
            result["return"] * 100,
            result["volatility"] * 100,
            result["sharpe"],
            result["max_weight"] * 100,
        )

    mv = MeanVarianceOptimizer(
        expected_returns,
        cov_annual,
        risk_free_rate=risk_free_rate,
    )
    record("Equal Weight", mv.equal_weight)
    record("Min Variance", lambda: mv.minimum_variance(constraints))
    record("Max Sharpe", lambda: mv.maximum_sharpe(constraints))
    record(
        "HRP",
        lambda: HRPOptimizer(returns, cov_matrix=cov_annual).optimize(
            constraints=constraints
        ),
    )
    record(
        "Risk Parity",
        lambda: RiskParityOptimizer(
            cov_annual,
            expected_returns=expected_returns,
        ).optimize(constraints=constraints),
    )
    record(
        "Inv Volatility",
        lambda: RiskParityOptimizer(
            cov_annual,
            expected_returns=expected_returns,
        ).inverse_volatility(),
    )
    record(
        "Min CVaR",
        lambda: CVaROptimizer(
            returns,
            expected_returns=expected_returns,
            alpha=0.05,
            risk_free_rate=risk_free_rate,
        ).minimum_cvar(constraints),
    )
    return portfolios


def _write_portfolio_artifacts(
    output_dir: Path,
    returns: pd.DataFrame,
    portfolios: Dict[str, Dict],
    class_map: Dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    weights = (
        pd.DataFrame({name: result["weights"] for name, result in portfolios.items()})
        .reindex(returns.columns)
        .fillna(0)
    )
    weights.to_parquet(output_dir / "portfolio_weights.parquet")
    weights.to_csv(output_dir / "portfolio_weights_matrix.csv", float_format="%.8f")

    holdings_rows = []
    for ticker in weights.index:
        for portfolio in weights.columns:
            weight = float(weights.loc[ticker, portfolio])
            holdings_rows.append(
                {
                    "Portfolio": portfolio,
                    "Ticker": ticker,
                    "Asset_Class": class_map.get(ticker, "unknown"),
                    "Weight": weight,
                    "Weight_Percent": weight * 100,
                    "Included": bool(abs(weight) > 1e-8),
                }
            )
    holdings = pd.DataFrame(holdings_rows)
    holdings.to_parquet(output_dir / "portfolio_holdings_long.parquet")
    holdings.to_csv(
        output_dir / "portfolio_holdings_long.csv",
        index=False,
        float_format="%.8f",
    )

    summary = pd.DataFrame(
        {
            name: {
                "Return (%)": result["return"] * 100,
                "Volatility (%)": result["volatility"] * 100,
                "Sharpe": result["sharpe"],
                "N Assets": result["n_assets"],
                "Max Weight (%)": result["max_weight"] * 100,
                "HHI": result["concentration"],
            }
            for name, result in portfolios.items()
        }
    ).T
    summary.to_parquet(output_dir / "portfolio_summary.parquet")
    return weights, summary


def _write_risk_artifacts(
    output_dir: Path,
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    class_map: Dict[str, str],
) -> pd.DataFrame:
    rows = {}
    for strategy in weights.columns:
        w = weights[strategy]
        calc = VaRCVaRCalculator(returns, weights=w)
        hist = calc.historical(alpha=0.05)
        dd = DrawdownAnalyzer(returns, weights=w).summary()
        concentration = FactorRiskDecomposer(
            returns,
            w,
            class_map,
        ).concentration_metrics()
        port_returns = pd.Series(returns.values @ w.values, index=returns.index)
        rows[strategy] = {
            "Ann_Vol_%": port_returns.std() * np.sqrt(252) * 100,
            "VaR_5%": hist["VaR"] * 100,
            "CVaR_5%": hist["CVaR"] * 100,
            "VaR_Annual": hist["VaR_annual"],
            "CVaR_Annual": hist["CVaR_annual"],
            "Max_DD_%": dd["Max_Drawdown_%"],
            "Calmar": dd["Calmar_Ratio"],
            "Ulcer_Index": dd["Ulcer_Index"],
            "Div_Ratio": concentration["Diversification_Ratio"],
            "ENB_Risk": concentration["ENB_Risk"],
        }
    risk = pd.DataFrame(rows).T
    risk.to_parquet(output_dir / "risk_metrics.parquet")
    return risk


def _write_backtest_artifacts(
    output_dir: Path,
    returns: pd.DataFrame,
    class_map: Dict[str, str],
    config: PipelineConfig,
    risk_free_rate: float,
) -> pd.DataFrame:
    backtester = PortfolioBacktester(
        returns,
        class_map,
        costs=TransactionCosts(
            proportional=config.transaction_cost_proportional,
            spread=config.transaction_cost_spread,
        ),
        risk_free_rate=risk_free_rate,
        max_position_weight=config.max_position_weight,
    )
    results = backtester.run_all_strategies(
        train_window=config.train_window,
        rebal_frequency=config.rebal_frequency,
    )
    pd.DataFrame(
        {name: result["returns"] for name, result in results.items()}
    ).to_parquet(output_dir / "backtest_returns.parquet")
    summary = pd.DataFrame(
        {
            name: {
                "CAGR": result["metrics"]["CAGR"],
                "Volatility": result["metrics"]["Annualized Volatility"],
                "Sharpe": result["metrics"]["Sharpe Ratio"],
                "Max_Drawdown": result["metrics"]["Max Drawdown"],
                "Calmar": result["metrics"]["Calmar Ratio"],
                "N_Rebalances": result["n_rebalances"],
                "Total_Turnover": result["total_turnover"],
                "Total_Cost": result["total_cost"],
                "Annualized_Cost_Drag_%": result["annualized_cost_drag_%"],
            }
            for name, result in results.items()
        }
    ).T
    summary.to_parquet(output_dir / "backtest_summary.parquet")
    return summary


def _write_diagnostic_artifacts(
    output_dir: Path,
    portfolio_summary: pd.DataFrame,
    backtest_summary: pd.DataFrame,
    config: PipelineConfig,
) -> pd.DataFrame:
    """Compare in-sample optimization output with walk-forward evidence."""
    name_map = {
        "Inv Volatility": "Inverse Vol",
    }
    rows = {}
    for static_name, static_row in portfolio_summary.iterrows():
        bt_name = name_map.get(static_name, static_name)
        if bt_name not in backtest_summary.index:
            continue

        bt_row = backtest_summary.loc[bt_name]
        static_sharpe = float(static_row["Sharpe"])
        oos_sharpe = float(bt_row["Sharpe"])
        static_return = float(static_row["Return (%)"]) / 100
        oos_return = float(bt_row["CAGR"])
        sharpe_gap = static_sharpe - oos_sharpe
        return_gap = static_return - oos_return

        if sharpe_gap >= 0.75:
            gap_level = "High"
            interpretation = (
                "In-sample result is materially stronger than walk-forward evidence; "
                "treat as overfitting/estimation-risk warning."
            )
        elif sharpe_gap >= 0.35:
            gap_level = "Medium"
            interpretation = (
                "In-sample advantage partly survives, but robustness is uncertain."
            )
        else:
            gap_level = "Low"
            interpretation = (
                "In-sample and walk-forward evidence are broadly consistent."
            )

        if oos_sharpe >= 0.60 and bt_row["Max_Drawdown"] > -0.25:
            evidence_tier = "Primary research candidate"
        elif oos_sharpe >= 0.25 and bt_row["Max_Drawdown"] > -0.35:
            evidence_tier = "Secondary research candidate"
        else:
            evidence_tier = "Diagnostic only"

        rows[static_name] = {
            "Backtest_Name": bt_name,
            "Static_Return": static_return,
            "Static_Sharpe": static_sharpe,
            "OOS_CAGR": oos_return,
            "OOS_Sharpe": oos_sharpe,
            "OOS_Max_Drawdown": float(bt_row["Max_Drawdown"]),
            "Annualized_Cost_Drag_%": float(bt_row["Annualized_Cost_Drag_%"]),
            "Sharpe_Gap": sharpe_gap,
            "Return_Gap": return_gap,
            "Gap_Level": gap_level,
            "Evidence_Tier": evidence_tier,
            "Interpretation": interpretation,
        }

    diagnostics = pd.DataFrame(rows).T
    diagnostics.to_parquet(output_dir / "model_diagnostics.parquet")

    if not diagnostics.empty:
        best_oos = diagnostics["OOS_Sharpe"].idxmax()
        largest_gap = diagnostics["Sharpe_Gap"].idxmax()
        primary = diagnostics[
            diagnostics["Evidence_Tier"].eq("Primary research candidate")
        ]
        if not primary.empty:
            decision_candidate = primary["OOS_Sharpe"].idxmax()
        else:
            decision_candidate = best_oos
        summary = {
            "primary_ranking_metric": config.primary_selection_rule,
            "best_oos_strategy": best_oos,
            "best_oos_sharpe": float(diagnostics.loc[best_oos, "OOS_Sharpe"]),
            "risk_screened_candidate": decision_candidate,
            "risk_screened_candidate_tier": str(
                diagnostics.loc[decision_candidate, "Evidence_Tier"]
            ),
            "risk_screened_candidate_oos_sharpe": float(
                diagnostics.loc[decision_candidate, "OOS_Sharpe"]
            ),
            "risk_screened_candidate_max_drawdown": float(
                diagnostics.loc[decision_candidate, "OOS_Max_Drawdown"]
            ),
            "largest_in_sample_gap_strategy": largest_gap,
            "largest_sharpe_gap": float(diagnostics.loc[largest_gap, "Sharpe_Gap"]),
            "decision_rule": (
                "Use walk-forward evidence as the primary decision layer. "
                "Static optimization results are training-sample diagnostics, not "
                "standalone investment conclusions."
            ),
            "config_path": config.config_path,
        }
        (output_dir / "decision_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

    return diagnostics


def _write_regime_artifacts(
    output_dir: Path,
    returns: pd.DataFrame,
    class_map: Dict[str, str],
    config: PipelineConfig,
    risk_free_rate: float,
) -> Dict[str, pd.DataFrame]:
    portfolio_returns = returns.mean(axis=1)
    vol_regimes = VolatilityRegimeDetector(returns).detect(portfolio_returns)
    regime_labels = pd.DataFrame({"Vol_Regime": vol_regimes["Regime"]})

    try:
        hmm = HMMRegimeDetector(returns, n_regimes=3).fit(portfolio_returns)
        regime_labels["HMM_Regime"] = hmm.get_regime_series()
    except Exception as exc:  # pragma: no cover - depends on stochastic HMM convergence
        logger.warning("HMM regime detection skipped: %s", exc)

    try:
        clustering = ClusteringRegimeDetector(returns, n_regimes=3).fit(
            portfolio_returns
        )
        regime_labels["Cluster_Regime"] = clustering.get_regime_series()
    except Exception as exc:  # pragma: no cover - depends on sklearn convergence
        logger.warning("Clustering regime detection skipped: %s", exc)

    regime_labels.to_parquet(output_dir / "regime_labels.parquet")

    allocator = AdaptiveAllocator(
        returns,
        class_map,
        risk_free_rate=risk_free_rate,
    )
    adaptive_returns = {}
    for mode, label in [("rule_based", "Adaptive_Rule"), ("optimized", "Adaptive_Opt")]:
        adaptive_returns[label] = allocator.adaptive_backtest(
            regime_labels["Vol_Regime"].dropna(),
            mode=mode,
            train_window=config.adaptive_train_window,
            rebal_frequency=config.adaptive_rebal_frequency,
        )["returns"]
    adaptive = pd.DataFrame(adaptive_returns)
    adaptive.to_parquet(output_dir / "adaptive_returns.parquet")
    return {"regime_labels": regime_labels, "adaptive_returns": adaptive}


def _write_ml_artifacts(
    output_dir: Path,
    returns: pd.DataFrame,
    market_signals: Optional[pd.DataFrame],
    config: PipelineConfig,
) -> Dict:
    """Write honest downside-risk ML diagnostics."""
    if not config.ml_enabled:
        return {"status": "disabled"}

    try:
        result = evaluate_downside_risk_model(
            returns=returns,
            market_signals=market_signals,
            n_splits=config.ml_n_splits,
            event_quantile=config.ml_event_quantile,
            event_lookback=config.ml_event_lookback,
            min_train_size=config.ml_min_train_size,
            random_seed=config.random_seed,
        )
        result.metrics.to_parquet(output_dir / "ml_downside_risk_metrics.parquet")
        result.metrics.to_csv(output_dir / "ml_downside_risk_metrics.csv", index=False)
        Path(config.reports_tables_dir).mkdir(parents=True, exist_ok=True)
        result.metrics.to_csv(
            Path(config.reports_tables_dir) / "ml_downside_risk_metrics.csv",
            index=False,
        )

        if not result.predictions.empty:
            result.predictions.to_parquet(
                output_dir / "ml_downside_risk_predictions.parquet"
            )
        if not result.feature_importance.empty:
            result.feature_importance.to_parquet(
                output_dir / "ml_downside_risk_feature_importance.parquet"
            )
            result.feature_importance.to_csv(
                output_dir / "ml_downside_risk_feature_importance.csv",
                index=False,
            )

        figures = save_downside_risk_figures(result, config.reports_figures_dir)
        mean_row = (
            result.metrics[result.metrics["Fold"].astype(str).eq("mean")]
            if "Fold" in result.metrics
            else pd.DataFrame()
        )
        summary = {
            "status": result.status,
            "reason": result.reason,
            "model": "balanced_logistic_regression",
            "event_definition": (
                f"next-day equal-weight return below prior rolling "
                f"{config.ml_event_quantile:.0%} quantile"
            ),
            "figures": figures,
        }
        if not mean_row.empty:
            row = mean_row.iloc[0]
            for key in ["ROC_AUC", "PR_AUC", "Baseline_PR_AUC", "Brier", "F1"]:
                if key in row and pd.notna(row[key]):
                    summary[key.lower()] = float(row[key])
        return summary
    except Exception as exc:  # pragma: no cover - diagnostic should not halt pipeline
        logger.warning("Downside-risk ML diagnostics skipped: %s", exc)
        status = pd.DataFrame([{"Status": "skipped", "Reason": str(exc)}])
        status.to_parquet(output_dir / "ml_downside_risk_metrics.parquet")
        status.to_csv(output_dir / "ml_downside_risk_metrics.csv", index=False)
        return {"status": "skipped", "reason": str(exc)}


def _mirror_notebook_processed_data(
    output_dir: Path, notebook_output_dir: Path
) -> None:
    notebook_output_dir.mkdir(parents=True, exist_ok=True)
    for filename in [
        "prices_clean.parquet",
        "returns_daily.parquet",
        "log_returns_daily.parquet",
        "asset_class_map.json",
    ]:
        shutil.copy2(output_dir / filename, notebook_output_dir / filename)
