"""Canonical configuration loading and validation for QuantVerse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

DEFAULT_CONFIG_PATH = Path("configs/base.yaml")


def project_root() -> Path:
    """Return the repository root when the package is used from this checkout."""
    return Path(__file__).resolve().parents[2]


def _resolve_config_path(config_path: str | Path | None = None) -> Path:
    path = Path(config_path or DEFAULT_CONFIG_PATH)
    if path.is_absolute():
        return path

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path

    root_path = project_root() / path
    return root_path


def _as_float(value: Any, name: str) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric or null") from exc


def _as_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _required(mapping: Dict[str, Any], key: str) -> Dict[str, Any]:
    section = mapping.get(key)
    if not isinstance(section, dict):
        raise ValueError(f"Missing required config section: {key}")
    return section


def _flatten_tickers(
    universe: Dict[str, Any], investable: Optional[bool] = None
) -> list[str]:
    tickers: list[str] = []
    for class_name, class_data in universe.items():
        is_investable = bool(class_data.get("investable", class_name != "signals"))
        if investable is not None and is_investable != investable:
            continue
        tickers.extend(class_data.get("tickers", []) or [])
    return tickers


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


@dataclass(frozen=True)
class QuantVerseConfig:
    """Loaded and validated QuantVerse configuration."""

    path: Path
    raw: Dict[str, Any]

    @property
    def universe(self) -> Dict[str, Any]:
        return _required(self.raw, "universe")

    @property
    def investable_tickers(self) -> list[str]:
        return _flatten_tickers(self.universe, investable=True)

    @property
    def signal_tickers(self) -> list[str]:
        return _flatten_tickers(self.universe, investable=False)

    def section(self, name: str) -> Dict[str, Any]:
        return _required(self.raw, name)

    def pipeline_kwargs(self) -> Dict[str, Any]:
        data = self.section("data")
        risk_free = self.section("risk_free")
        portfolio = self.section("portfolio")
        backtest = self.section("backtest")
        reports = self.section("reports")
        regime = self.section("regime")
        ml = self.section("ml")
        validation = self.raw.get("validation", {})

        return {
            "config_path": str(self.path),
            "start_date": data.get("start_date", "2015-01-01"),
            "end_date": data.get("end_date"),
            "cache_dir": data.get("cache_dir", "data/cache"),
            "output_dir": data.get("output_dir", "data/processed"),
            "notebook_output_dir": data.get(
                "notebook_output_dir", "notebooks/data/processed"
            ),
            "risk_free_rate": _as_float(
                risk_free.get("manual_annual_rate"), "risk_free.manual_annual_rate"
            ),
            "risk_free_proxy": risk_free.get("proxy", "^IRX"),
            "fallback_risk_free_rate": float(
                risk_free.get("fallback_annual_rate", 0.04)
            ),
            "expected_return_shrinkage": float(
                portfolio.get("expected_return_shrinkage", 0.50)
            ),
            "max_position_weight": float(portfolio.get("max_position_weight", 0.25)),
            "min_history_pct": float(data.get("min_history_pct", 0.70)),
            "train_window": _as_int(
                backtest.get("train_window", 504), "backtest.train_window"
            ),
            "rebal_frequency": _as_int(
                backtest.get("rebal_frequency", 63), "backtest.rebal_frequency"
            ),
            "transaction_cost_proportional": float(
                backtest.get("transaction_cost_proportional", 0.0010)
            ),
            "transaction_cost_spread": float(
                backtest.get("transaction_cost_spread", 0.0005)
            ),
            "mirror_notebook_data": bool(data.get("mirror_notebook_data", True)),
            "primary_selection_rule": portfolio.get(
                "primary_selection_rule", "walk_forward_oos_sharpe"
            ),
            "reports_root_dir": reports.get("root_dir", "reports"),
            "reports_tables_dir": reports.get("tables_dir", "reports/tables"),
            "reports_figures_dir": reports.get("figures_dir", "reports/figures"),
            "pdf_output_path": reports.get(
                "pdf_output", "output/pdf/quantverse_analysis_report.pdf"
            ),
            "html_output_path": reports.get(
                "html_output", "output/html/quantverse_report.html"
            ),
            "adaptive_train_window": _as_int(
                regime.get("adaptive_train_window", 252), "regime.adaptive_train_window"
            ),
            "adaptive_rebal_frequency": _as_int(
                regime.get("adaptive_rebal_frequency", 21),
                "regime.adaptive_rebal_frequency",
            ),
            "ml_enabled": bool(ml.get("enabled", True)),
            "ml_n_splits": _as_int(ml.get("n_splits", 5), "ml.n_splits"),
            "ml_event_quantile": float(ml.get("event_quantile", 0.10)),
            "ml_event_lookback": _as_int(
                ml.get("event_lookback", 252), "ml.event_lookback"
            ),
            "ml_min_train_size": _as_int(
                ml.get("min_train_size", 504), "ml.min_train_size"
            ),
            "random_seed": _as_int(ml.get("random_seed", 42), "ml.random_seed"),
            "var_exception_alpha": float(validation.get("var_exception_alpha", 0.05)),
            "var_exception_lookback": _as_int(
                validation.get("var_exception_lookback", 252),
                "validation.var_exception_lookback",
            ),
            "bootstrap_samples": _as_int(
                validation.get("bootstrap_samples", 300),
                "validation.bootstrap_samples",
            ),
            "bootstrap_block_size": _as_int(
                validation.get("bootstrap_block_size", 21),
                "validation.bootstrap_block_size",
            ),
        }

    def validate(self) -> None:
        for section in [
            "project",
            "data",
            "risk_free",
            "portfolio",
            "backtest",
            "reports",
            "universe",
        ]:
            _required(self.raw, section)

        all_tickers = _flatten_tickers(self.universe, investable=None)
        dupes = _duplicates(all_tickers)
        if dupes:
            raise ValueError(f"Duplicate tickers in universe: {dupes}")

        if not self.investable_tickers:
            raise ValueError("Universe must contain at least one investable ticker")
        if not self.signal_tickers:
            raise ValueError("Universe must contain non-investable market signals")

        overlap = sorted(set(self.investable_tickers).intersection(self.signal_tickers))
        if overlap:
            raise ValueError(f"Tickers cannot be both investable and signal: {overlap}")

        risk_free_proxy = self.section("risk_free").get("proxy")
        if risk_free_proxy and risk_free_proxy not in self.signal_tickers:
            raise ValueError(
                "risk_free.proxy must be listed under non-investable signals"
            )

        kwargs = self.pipeline_kwargs()
        max_weight = float(kwargs["max_position_weight"])
        if not 0 < max_weight <= 1:
            raise ValueError("portfolio.max_position_weight must be in (0, 1]")
        if max_weight * len(self.investable_tickers) < 1:
            raise ValueError("portfolio.max_position_weight is infeasible")

        shrinkage = float(kwargs["expected_return_shrinkage"])
        if not 0 <= shrinkage <= 1:
            raise ValueError("portfolio.expected_return_shrinkage must be in [0, 1]")

        if not 0 < float(kwargs["min_history_pct"]) <= 1:
            raise ValueError("data.min_history_pct must be in (0, 1]")
        if kwargs["train_window"] <= 0 or kwargs["rebal_frequency"] <= 0:
            raise ValueError("backtest windows must be positive")
        if not 0 < kwargs["ml_event_quantile"] < 0.5:
            raise ValueError("ml.event_quantile must be between 0 and 0.5")
        if not 0 < kwargs["var_exception_alpha"] < 0.5:
            raise ValueError("validation.var_exception_alpha must be between 0 and 0.5")
        if kwargs["var_exception_lookback"] <= 0:
            raise ValueError("validation.var_exception_lookback must be positive")
        if kwargs["bootstrap_samples"] <= 0 or kwargs["bootstrap_block_size"] <= 0:
            raise ValueError("bootstrap validation settings must be positive")


def load_config(config_path: str | Path | None = None) -> QuantVerseConfig:
    """Load and validate the canonical QuantVerse YAML configuration."""
    path = _resolve_config_path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"QuantVerse config not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"QuantVerse config must be a mapping: {path}")

    config = QuantVerseConfig(path=path, raw=raw)
    config.validate()
    return config
