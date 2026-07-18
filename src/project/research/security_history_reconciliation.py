"""Cross-artifact count and run-identity reconciliation for QuantVerse v2."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from project.research.run_identity import (
    RUN_REGISTRY_NAME,
    read_run_manifest,
)

RECONCILIATION_COLUMNS = [
    "artifact",
    "count",
    "as_of_date",
    "run_id",
    "expected_relationship",
    "observed_relationship",
    "status",
    "explanation",
    "universe_snapshot_id",
    "generated_at",
]


def build_cross_artifact_count_reconciliation(
    processed_dir: str | Path,
    *,
    max_selected_stocks: int = 40,
    walk_forward_max_assets: int = 20,
) -> pd.DataFrame:
    """Reconcile selected, forecast, portfolio and walk-forward counts."""
    processed = Path(processed_dir)
    manifest = read_run_manifest(processed)
    scores = _read_csv(processed / "global_stock_scores.csv")
    semantic = _read_csv(processed / "global_selected_stocks_report_view.csv")
    features = _read_csv(processed / "global_feature_history_eligibility.csv")
    identity = _read_csv(processed / "global_security_identity_audit.csv")
    forecasts = _read_csv(processed / "global_stock_return_forecasts.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    walk_windows = _read_csv(processed / "global_walk_forward_window_summary.csv")
    decision = _read_json(processed / "global_final_model_decision.json")

    selected = _truthy_series(scores.get("selection_flag")).sum()
    standard_eligible = _truthy_series(
        features.get("standard_composite_score_eligible")
    ).sum()
    short_history = (
        features.get("eligibility_status", pd.Series(dtype=str))
        .astype(str)
        .eq("diagnostic_short_history")
        .sum()
    )
    forecast_eligible_tickers = set(
        identity.loc[
            _truthy_series(identity.get("forecast_eligible")), "ticker"
        ].astype(str)
    )
    selected_tickers = set(
        scores.loc[_truthy_series(scores.get("selection_flag")), "ticker"].astype(str)
    )
    forecast_input = len(selected_tickers.intersection(forecast_eligible_tickers))
    forecast_output = (
        int(forecasts["ticker"].astype(str).nunique()) if "ticker" in forecasts else 0
    )
    candidate_count = (
        int(weights["ticker"].astype(str).nunique()) if "ticker" in weights else 0
    )
    final_model = str(decision.get("final_selected_model", "")).strip()
    final_holdings = 0
    if {"model_name", "ticker", "weight"}.issubset(weights):
        final = weights.loc[weights["model_name"].astype(str).eq(final_model)].copy()
        final_holdings = int(
            (
                pd.to_numeric(final["weight"], errors="coerce").fillna(0.0).abs() > 1e-8
            ).sum()
        )
    latest_walk_count = (
        int(pd.to_numeric(walk_windows["selected_count"], errors="coerce").iloc[-1])
        if not walk_windows.empty and "selected_count" in walk_windows
        else 0
    )

    run_ids, missing_registry = _core_run_ids(processed)
    expected_run = str(manifest.get("run_id", "unavailable"))
    run_id_pass = bool(
        not missing_registry and run_ids and set(run_ids.values()) == {expected_run}
    )
    metadata = {
        "as_of_date": manifest.get("data_as_of_date", "unavailable"),
        "run_id": expected_run,
        "universe_snapshot_id": manifest.get("universe_snapshot_id", "unavailable"),
        "generated_at": manifest.get("generated_at", "unavailable"),
    }
    rows = [
        _row(
            "stocks_scored",
            len(scores),
            "count >= selected standard candidates",
            f"{len(scores)} scored; {selected} selected",
            len(scores) >= selected,
            "All scoped securities remain visible, including diagnostic rows.",
            metadata,
        ),
        _row(
            "stocks_selection_flag_true",
            selected,
            f"count <= configured max_selected_stocks ({max_selected_stocks})",
            f"{selected} selected",
            selected <= int(max_selected_stocks),
            "Only standard-history-eligible rows may carry selection_flag=true.",
            metadata,
        ),
        _row(
            "semantic_selected_stock_count",
            len(semantic),
            "count == stocks_selection_flag_true",
            f"{len(semantic)} semantic rows vs {selected} selected",
            len(semantic) == selected,
            "The report-facing selected-stock view must describe the same selection.",
            metadata,
        ),
        _row(
            "standard_scoring_eligible_count",
            standard_eligible,
            "count >= stocks_selection_flag_true",
            f"{standard_eligible} eligible vs {selected} selected",
            standard_eligible >= selected,
            "The selected set must be a subset of the standard-history-eligible set.",
            metadata,
        ),
        _row(
            "short_history_diagnostic_count",
            short_history,
            "diagnostic rows remain visible and selection_flag=false",
            f"{short_history} short-history diagnostics",
            _short_history_not_selected(scores, features),
            "Short-history securities are visible but cannot enter standard ranking.",
            metadata,
        ),
        _row(
            "forecast_input_count",
            forecast_input,
            "count == forecast_output_ticker_count",
            f"{forecast_input} eligible selected forecast inputs",
            forecast_input == forecast_output,
            "Every eligible selected ticker must have forecast rows.",
            metadata,
        ),
        _row(
            "forecast_output_ticker_count",
            forecast_output,
            "count == forecast_input_count",
            f"{forecast_output} forecast tickers",
            forecast_output == forecast_input,
            "Missing forecast tickers require an explicit ineligibility reason.",
            metadata,
        ),
        _row(
            "portfolio_candidate_count",
            candidate_count,
            "count == stocks_selection_flag_true",
            f"{candidate_count} weighted candidate tickers vs {selected} selected",
            candidate_count == selected,
            "Portfolio models must use the same current selected candidate universe.",
            metadata,
        ),
        _row(
            "final_model_holding_count",
            final_holdings,
            "count <= portfolio_candidate_count",
            f"{final_holdings} {final_model or 'unknown'} holdings vs "
            f"{candidate_count} candidates",
            0 < final_holdings <= candidate_count,
            "Zero weights may reduce final holdings; they cannot introduce new tickers.",
            metadata,
        ),
        _row(
            "walk_forward_latest_selected_count",
            latest_walk_count,
            f"count <= configured walk_forward_max_assets ({walk_forward_max_assets})",
            f"{latest_walk_count} latest-fold selections",
            0 < latest_walk_count <= int(walk_forward_max_assets),
            "Walk-forward uses its separately configured fold-level holding cap.",
            metadata,
        ),
        _row(
            "core_generated_artifact_run_ids",
            len(set(run_ids.values())),
            "exactly one run_id and no missing core registry rows",
            f"run_ids={sorted(set(run_ids.values()))}; "
            f"missing_registry={missing_registry}",
            run_id_pass,
            "Reports must not combine core artifacts from different pipeline runs.",
            metadata,
        ),
    ]
    return pd.DataFrame(rows).reindex(columns=RECONCILIATION_COLUMNS)


def _core_run_ids(processed: Path) -> tuple[dict[str, str], list[str]]:
    registry_path = processed / RUN_REGISTRY_NAME
    required = [
        "data/processed/global_security_identity_audit.csv",
        "data/processed/global_feature_history_eligibility.csv",
        "data/processed/global_stock_scores.csv",
        "data/processed/global_stock_return_forecasts.csv",
        "data/processed/global_portfolio_league_weights.csv",
        "data/processed/global_portfolio_risk_report.csv",
        "data/processed/global_final_model_decision.json",
        "data/processed/global_robustness_sensitivity.csv",
        "data/processed/global_exposure_metadata_quality.csv",
        "data/processed/global_walk_forward_window_summary.csv",
    ]
    if not registry_path.exists():
        return {}, required
    registry = pd.read_csv(registry_path, dtype=str).fillna("")
    mapping = dict(
        zip(
            registry["artifact"].astype(str),
            registry["run_id"].astype(str),
            strict=False,
        )
    )
    return (
        {artifact: mapping[artifact] for artifact in required if artifact in mapping},
        [artifact for artifact in required if artifact not in mapping],
    )


def _short_history_not_selected(
    scores: pd.DataFrame,
    features: pd.DataFrame,
) -> bool:
    if scores.empty or features.empty or "ticker" not in scores:
        return False
    short = set(
        features.loc[
            features.get("eligibility_status", pd.Series(dtype=str))
            .astype(str)
            .eq("diagnostic_short_history"),
            "ticker",
        ].astype(str)
    )
    selected = set(
        scores.loc[_truthy_series(scores.get("selection_flag")), "ticker"].astype(str)
    )
    return short.isdisjoint(selected)


def _truthy_series(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=bool)
    return series.map(lambda value: str(value).strip().lower() in {"1", "true", "yes"})


def _row(
    artifact: str,
    count: int,
    expected: str,
    observed: str,
    passed: bool,
    explanation: str,
    metadata: dict[str, str],
) -> dict[str, object]:
    return {
        "artifact": artifact,
        "count": int(count),
        "expected_relationship": expected,
        "observed_relationship": observed,
        "status": "passed" if passed else "failed",
        "explanation": explanation,
        **metadata,
    }


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
