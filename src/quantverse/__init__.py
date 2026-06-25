"""Professional public namespace for QuantVerse.

The historical implementation package is still named :mod:`project`. QuantVerse
keeps that package for backward compatibility while exposing the same stable
modules through the public :mod:`quantverse` namespace.
"""

from __future__ import annotations

import importlib
import sys

_ALIASES = [
    "config",
    "constants",
    "pipeline",
    "backtest",
    "backtest.attribution",
    "backtest.backtester",
    "backtest.metrics",
    "backtest.rebalancing",
    "covariance",
    "covariance.estimators",
    "covariance.evaluation",
    "data_pipeline",
    "data_pipeline.fetcher",
    "data_pipeline.processor",
    "data_pipeline.universe",
    "exploratory",
    "exploratory.correlation",
    "exploratory.return_analysis",
    "exploratory.visualizations",
    "ml",
    "ml.downside_risk",
    "optimization",
    "optimization.constraints",
    "optimization.cvar_optimization",
    "optimization.hierarchical",
    "optimization.mean_variance",
    "optimization.risk_parity",
    "regime",
    "regime.adaptive_allocator",
    "regime.clustering_regime",
    "regime.hmm_regime",
    "regime.volatility_regime",
    "reporting",
    "reporting.dashboard_data",
    "reporting.pdf_report",
    "reporting.report_generator",
    "reporting.tearsheet",
    "risk",
    "risk.drawdown",
    "risk.factor_risk",
    "risk.tail_risk",
    "risk.validation",
    "risk.var_cvar",
    "simulation",
    "simulation.monte_carlo",
    "simulation.scenario_analysis",
    "simulation.stress_testing",
]


def _install_aliases() -> None:
    for module_name in _ALIASES:
        public_name = f"{__name__}.{module_name}"
        if public_name not in sys.modules:
            sys.modules[public_name] = importlib.import_module(f"project.{module_name}")


_install_aliases()

from project.pipeline import PipelineConfig, run_full_pipeline  # noqa: E402

__all__ = ["PipelineConfig", "run_full_pipeline"]
