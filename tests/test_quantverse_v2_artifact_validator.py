import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.pdfgen import canvas

from project.research.global_visual_analytics import build_visual_analytics_outputs
from project.research.run_identity import register_artifacts
from scripts.build_quantverse_v2_excel_output import _write_selected_stocks_sheet
from scripts.validate_quantverse_v2_artifacts import (
    _portable_exception_details,
    _portfolio_input_violations,
    _stable_frame_hash,
    validate_artifacts,
)


def _write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path))
    for index, line in enumerate(text.splitlines()):
        pdf.drawString(72, 760 - index * 18, line)
    pdf.showPage()
    pdf.save()


def _write_publication_manifest(
    root: Path,
    path: Path,
    run_metadata: dict[str, str],
    artifacts: list[Path],
    publication_type: str,
) -> None:
    rows = []
    for artifact in artifacts:
        rows.append(
            {
                "artifact": artifact.relative_to(root).as_posix(),
                "size_bytes": artifact.stat().st_size,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        )
    path.write_text(
        json.dumps(
            {
                "publication_status": "complete",
                "publication_id": "fixture-publication",
                "publication_type": publication_type,
                **run_metadata,
                "artifacts": rows,
            }
        ),
        encoding="utf-8",
    )


def test_artifact_exception_details_do_not_expose_local_absolute_paths():
    separator = "\\"
    path = Path(
        "C:"
        + separator
        + "Users"
        + separator
        + "example"
        + separator
        + "Desktop"
        + separator
        + "quantverse"
        + separator
        + "output"
        + separator
        + "report.pdf"
    )
    details = _portable_exception_details(FileNotFoundError(str(path)), path)

    assert details == "error_type=FileNotFoundError; artifact=report.pdf"


def test_artifact_validator_passes_on_minimal_valid_fixture(tmp_path):
    processed = tmp_path / "data" / "processed"
    output = tmp_path / "output"
    processed.mkdir(parents=True)
    universe_dir = tmp_path / "data" / "universe"
    universe_dir.mkdir(parents=True)
    (output / "html").mkdir(parents=True)
    (output / "excel").mkdir(parents=True)
    (output / "pdf").mkdir(parents=True)
    (output / "thesis").mkdir(parents=True)
    pd.DataFrame({"ticker": ["A", "B"]}).to_csv(
        universe_dir / "current_global_equity_universe.csv",
        index=False,
    )
    for filename in [
        "global_master_equal_weight_comparison.csv",
        "global_master_random_portfolio_benchmark.csv",
        "global_exact_proxy_classification_report.csv",
    ]:
        pd.DataFrame({"value": [1.0]}).to_csv(
            processed / filename,
            index=False,
        )
    run_metadata = {
        "run_id": "qv2-2026-07-09-fixture",
        "execution_id": "qv2-2026-07-09-fixture",
        "data_as_of_date": "2026-07-09",
        "generated_at": "2026-07-10T00:00:00+00:00",
        "universe_snapshot_id": "universe-fixture",
        "data_snapshot_id": "data-fixture",
        "config_hash": "config-fixture",
        "input_fingerprint": "input-fixture",
    }
    (processed / "quantverse_v2_run_manifest.json").write_text(
        json.dumps(run_metadata), encoding="utf-8"
    )
    pd.DataFrame(
        {
            "check": ["fixture_reference_math"],
            "passed": [True],
            **{key: [value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "quantverse_v2_reference_math_checks.csv", index=False)
    (processed / "quantverse_v2_reference_math_summary.json").write_text(
        json.dumps(
            {
                **run_metadata,
                "status": "passed",
                "check_count": 1,
                "failed_check_count": 0,
                "checks_path": (
                    "data/processed/quantverse_v2_reference_math_checks.csv"
                ),
            }
        ),
        encoding="utf-8",
    )

    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "run_status": "completed",
                "final_selected_model": "Equal Weight",
                "final_model_selection_method": (
                    "paired_block_bootstrap_gate_then_oos_sharpe"
                ),
                "final_model_selection_score": 1.0,
                "final_model_selection_decision": "not promoted",
                "promotion_decision": "not promoted",
                "weight_sum": 1.0,
                "final_selected_holdings": 2,
                "numerical_integrity_status": "passed",
                "numerical_integrity_failed_checks": 0,
                **run_metadata,
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_final_model_decision.json").write_text(
        json.dumps(
            {
                "final_selected_model": "Equal Weight",
                "final_model_selection_method": (
                    "paired_block_bootstrap_gate_then_oos_sharpe"
                ),
                "final_model_selection_score": 1.0,
                "final_decision": "not promoted",
                "final_decision_reason": "Fixture.",
                "random_portfolio_percentile": 0.70,
                "final_model_book_grounded_rank": 1,
                "final_model_gate_reasons": (
                    "benchmark self-comparison is not applicable"
                ),
                "publish_readiness_status": "research_publish_ready_with_limitations",
                **run_metadata,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "actual_status": ["benchmark_only"],
            "constraints_pass": [True],
            "cagr": [0.20],
            "annualized_return": [0.18],
            "volatility": [0.02],
            "sharpe": [1.2],
            "sortino": [1.4],
            "max_drawdown": [-0.01],
            "var_95": [-0.001],
            "cvar_95": [-0.0015],
            "configured_max_weight": [0.5],
            **{key: [value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_portfolio_league.csv", index=False)
    pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=260, freq="B"),
            "A": [0.001] * 260,
            "B": [0.002, -0.001] * 130,
        }
    ).to_csv(processed / "global_security_simple_returns_usd.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "weight": [0.5, 0.5],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "cagr": [0.20],
            "annualized_return": [0.18],
            "annualized_volatility": [0.02],
            "sharpe": [1.2],
            "sortino": [1.4],
            "max_drawdown": [-0.01],
            "var_95": [-0.001],
            "cvar_95": [-0.0015],
            "total_return": [0.05],
        }
    ).to_csv(processed / "global_portfolio_risk_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "avg_cagr": [0.10],
            "avg_annualized_return": [0.09],
            "avg_volatility": [0.03],
            "avg_sharpe": [1.0],
            "avg_sortino": [1.1],
            "avg_max_drawdown": [-0.01],
            "avg_cvar_95": [-0.001],
            "oos_annualized_return": [0.09],
            "oos_volatility": [0.03],
            "oos_sharpe": [1.0],
            "oos_sortino": [1.1],
            "oos_max_drawdown": [-0.01],
            "oos_cvar_95": [-0.001],
            "uncertainty_status": ["benchmark_self_comparison_not_applicable"],
            "uncertainty_method": ["paired_circular_block_bootstrap"],
            "paired_observations": [252],
            "sharpe_diff_ci_lower": [np.nan],
            "sharpe_diff_ci_upper": [np.nan],
            "probability_sharpe_improvement": [np.nan],
        }
    ).to_csv(processed / "global_walk_forward_model_comparison.csv", index=False)
    pd.DataFrame(
        [
            {
                "fold": fold,
                "check": check,
                "passed": True,
                "audit_status": (
                    "passed_with_current_universe_survivorship_limitation"
                ),
                "evidence_scope": "current_universe_not_point_in_time",
                **run_metadata,
            }
            for fold in [0, 1]
            for check in [
                "train_end_before_test_start",
                "scores_as_of_not_after_train_end",
                "selected_tickers_available_in_train",
                "scores_recomputed_inside_fold",
            ]
        ]
    ).to_csv(processed / "global_walk_forward_leakage_audit.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "risk_contribution_pct": [0.5, 0.5],
        }
    ).to_csv(processed / "global_risk_contribution_report.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "selection_flag": [True, True],
            "standard_composite_score_eligible": [True, True],
            **{key: [value, value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_stock_scores.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "current_listing_start_date": ["unavailable", "unavailable"],
            "provider_history_start_date": ["2024-01-01", "2024-01-01"],
            "first_valid_return_date": ["2024-01-02", "2024-01-02"],
            "observations_before_current_listing": [0, 0],
            "ticker_reuse_status": ["not_known", "not_known"],
            "identity_continuity_status": [
                "no_known_conflict_provider_only",
                "no_known_conflict_provider_only",
            ],
            "history_contamination_status": [
                "not_assessable_without_listing_date",
                "not_assessable_without_listing_date",
            ],
            "eligibility_status": ["eligible", "eligible"],
            "standard_scoring_eligible": [True, True],
            "forecast_eligible": [True, True],
            "walk_forward_eligible": [True, True],
            **{key: [value, value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_security_identity_audit.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "eligibility_status": ["eligible", "eligible"],
            "standard_scoring_eligible": [True, True],
            "forecast_eligible": [True, True],
            "walk_forward_eligible": [True, True],
            **{key: [value, value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_security_history_eligibility.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "observations": [260, 260],
            "12m_eligible": [True, True],
            "volatility_12m_eligible": [True, True],
            "standard_composite_score_eligible": [True, True],
            "eligibility_status": ["eligible", "eligible"],
            **{key: [value, value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_feature_history_eligibility.csv", index=False)
    pd.DataFrame(
        {
            "artifact": [
                "stocks_scored",
                "stocks_selection_flag_true",
                "semantic_selected_stock_count",
                "standard_scoring_eligible_count",
                "short_history_diagnostic_count",
                "forecast_input_count",
                "forecast_output_ticker_count",
                "portfolio_candidate_count",
                "final_model_holding_count",
                "walk_forward_latest_selected_count",
                "core_generated_artifact_run_ids",
            ],
            "count": [2, 2, 2, 2, 0, 2, 2, 2, 2, 2, 1],
            "status": ["passed"] * 11,
            "observed_relationship": ["fixture"] * 11,
            **{key: [value] * 11 for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_cross_artifact_count_reconciliation.csv", index=False)
    core_artifacts = [
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
    pd.DataFrame(
        [
            {
                "artifact": artifact,
                **run_metadata,
                "file_size": 1,
                "sha256": "fixture",
            }
            for artifact in core_artifacts
        ]
    ).to_csv(processed / "quantverse_v2_artifact_run_registry.csv", index=False)
    selected_view = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "name": ["Asset A", "Asset B"],
            "selection_rank": [1, 2],
            "composite_quant_score": [1.0, 0.9],
            "listing_country": ["United States", "United States"],
            "issuer_country": ["United States", "United States"],
            "economic_country": ["United States", "United States"],
            "listing_currency": ["USD", "USD"],
            "exchange": ["NYQ", "NYQ"],
            "sector": ["Technology", "Technology"],
            "industry": ["Software", "Hardware"],
            "metadata_source": ["fixture", "fixture"],
            "metadata_confidence": ["high", "high"],
            "metadata_as_of_date": ["2026-07-09", "2026-07-09"],
            "adr_or_foreign_issuer_flag": [False, False],
            "warning_flags": ["none", "none"],
            "selection_reason": ["fixture", "fixture"],
        }
    )
    selected_view.to_csv(
        processed / "global_selected_stocks_report_view.csv", index=False
    )
    pd.DataFrame(
        {
            "selected_stock_count": [2],
            "matched_metadata_count": [2],
            "unmatched_metadata_count": [0],
            "duplicate_ticker_count": [0],
            "listing_country_coverage_ratio": [1.0],
            "issuer_country_coverage_ratio": [1.0],
            "economic_country_coverage_ratio": [1.0],
            "sector_coverage_ratio": [1.0],
            "industry_coverage_ratio": [1.0],
            "semantic_view_status": ["passed"],
            "interpretation": ["fixture"],
            "invalidation_condition": ["fixture"],
        }
    ).to_csv(processed / "global_selected_stocks_report_view_quality.csv", index=False)
    for filename in [
        "global_model_selection_diagnostics.csv",
        "global_final_model_decision.csv",
        "global_robustness_sensitivity.csv",
        "global_top_holdings_explanation.csv",
    ]:
        pd.DataFrame({"value": [1]}).to_csv(processed / filename, index=False)
    pd.DataFrame(
        {
            "Date": ["2026-01-05", "2026-01-06"],
            "EURUSD=X": [1.10, 1.11],
        }
    ).to_csv(processed / "global_fx_prices.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "scenario": ["equity_shock"],
            "portfolio_impact": [-0.10],
            **{key: [value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_stress_test_results.csv", index=False)
    pd.DataFrame(
        {
            "check": ["cvar_not_above_var"],
            "passed": [True],
            **{key: [value] for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_risk_metric_sanity_checks.csv", index=False)
    pd.DataFrame(
        {
            "operation_id": ["QV2-MD-0001"],
            "path": ["src/project/example.py"],
            "line": [10],
            "function": ["example"],
            "operation": ["ffill"],
            "callsite_fingerprint": ["fixture-callsite"],
            "source_tree_hash": ["source-fixture"],
            "code": ["frame.ffill(limit=5)"],
            "classification": ["BOUNDED_FORWARD_FILL"],
            "risk_level": ["medium"],
            "status": ["reviewed"],
            "approved": [True],
            "reason": ["bounded fixture operation"],
            "required_control": ["finite limit"],
        }
    ).to_csv(
        processed / "quantverse_v2_missing_data_operation_audit.csv",
        index=False,
    )
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "eligible_final_model": [True],
            "selection_score": [1.0],
            "book_grounded_rank": [1],
            "random_sharpe_percentile": [0.70],
            "promotion_gate_failed_reasons": [
                "benchmark self-comparison is not applicable"
            ],
            "sharpe_improvement_vs_equal_weight": [0.0],
            "beats_equal_weight_sharpe": [False],
            "drawdown_not_materially_worse_than_equal_weight": [True],
            "cvar_not_materially_worse_than_equal_weight": [True],
            "turnover_within_limit": [True],
            "random_sharpe_gate_pass": [True],
            "turnover": [0.20],
            "walk_forward_annualized_return": [0.09],
            "walk_forward_volatility": [0.03],
            "walk_forward_sharpe": [1.0],
            "walk_forward_sortino": [1.1],
            "walk_forward_max_drawdown": [-0.01],
            "walk_forward_cvar_95": [-0.001],
            "uncertainty_status": ["benchmark_self_comparison_not_applicable"],
            "uncertainty_method": ["paired_circular_block_bootstrap"],
            "paired_oos_observations": [252],
            "sharpe_diff_ci_lower": [np.nan],
            "sharpe_diff_ci_upper": [np.nan],
            "probability_sharpe_improvement": [np.nan],
            "uncertainty_gate_pass": [True],
            "forecast_validation_gate_pass": [True],
            "extreme_metric_warning": ["none"],
            "random_benchmark_scope": ["walk_forward_oos_net"],
            "random_benchmark_provenance_status": ["verified_same_protocol"],
            "random_benchmark_protocol_hash": ["wf-random-fixture"],
            "robustness_gate_pass": [False],
            "leakage_gate_pass": [True],
            "leakage_evidence_status": [
                "verified_current_no_lookahead_with_survivorship_limitation"
            ],
        }
    ).to_csv(processed / "global_model_selection_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Policy Constrained"],
            "return_percentile": [0.6, 0.4],
            "volatility_percentile": [0.5, 0.7],
            "sharpe_percentile": [0.7, 0.3],
            "max_drawdown_percentile": [0.5, 0.6],
            "cvar_percentile": [0.5, 0.6],
        }
    ).to_csv(processed / "global_random_portfolio_percentile_report.csv", index=False)
    pd.DataFrame(
        {
            "horizon": ["12M"],
            "horizon_days": [252],
            "mean_mae": [0.12],
            "mean_rmse": [0.16],
            "mean_random_walk_mae": [0.14],
            "forecast_validation_status": ["validated_diagnostic"],
            "allocation_signal_status": ["diagnostic_only"],
        }
    ).to_csv(processed / "global_forecast_validation_by_horizon.csv", index=False)
    pd.DataFrame(
        {"portfolio_id": range(40), "sharpe": [idx / 40 for idx in range(40)]}
    ).to_csv(processed / "global_random_portfolio_distribution.csv", index=False)
    oos_dates = pd.date_range("2026-01-05", periods=4, freq="B")
    date_payload = "\n".join(oos_dates.strftime("%Y-%m-%d")).encode("utf-8")
    date_hash = f"dates-{hashlib.sha256(date_payload).hexdigest()[:24]}"
    pd.DataFrame(
        {
            "Date": oos_dates,
            "fold": [0, 0, 1, 1],
            "model_name": ["Equal Weight"] * 4,
            "return": [0.001, -0.002, 0.003, 0.001],
        }
    ).to_csv(processed / "global_walk_forward_returns.csv", index=False)
    random_return_rows = [
        {
            "Date": date,
            "fold": 0 if index < 2 else 1,
            "portfolio_id": portfolio_id,
            "return": 0.0001 * (portfolio_id + 1) + 0.00001 * index,
        }
        for portfolio_id in range(40)
        for index, date in enumerate(oos_dates)
    ]
    pd.DataFrame(random_return_rows).to_csv(
        processed / "global_walk_forward_random_returns.csv",
        index=False,
    )
    random_weight_rows = [
        {
            "fold": fold,
            "rebalance_date": oos_dates[fold * 2],
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "target_weight": 0.5,
            "pre_trade_weight": 0.5,
            "post_test_weight": 0.5,
            **run_metadata,
        }
        for fold in range(2)
        for portfolio_id in range(40)
        for ticker in ["A", "B"]
    ]
    random_weights = pd.DataFrame(random_weight_rows)
    random_weights.to_csv(
        processed / "global_walk_forward_random_weights.csv",
        index=False,
    )
    provenance = {
        "benchmark_scope": "walk_forward_oos_net",
        "provenance_status": "verified_same_protocol",
        "protocol_hash": "wf-random-fixture",
        "fold_schedule_hash": "fold-fixture",
        "selected_universe_by_fold_hash": "universe-fold-fixture",
        "model_oos_dates_hash": date_hash,
        "random_oos_dates_hash": date_hash,
        "oos_dates_match": True,
        "random_weights_hash": _stable_frame_hash(
            random_weights,
            [
                "fold",
                "portfolio_id",
                "ticker",
                "target_weight",
                "pre_trade_weight",
                "post_test_weight",
            ],
        ),
        **run_metadata,
    }
    (processed / "global_walk_forward_random_benchmark_provenance.json").write_text(
        json.dumps(provenance), encoding="utf-8"
    )
    pd.DataFrame(
        {
            "portfolio_id": range(40),
            "benchmark_scope": ["walk_forward_oos_net"] * 40,
            "benchmark_provenance_status": ["verified_same_protocol"] * 40,
            "protocol_hash": ["wf-random-fixture"] * 40,
            "annualized_return": [0.08 + idx / 1000 for idx in range(40)],
            "volatility": [0.20 + idx / 1000 for idx in range(40)],
            "sharpe": [idx / 40 for idx in range(40)],
            "max_drawdown": [-0.30 + idx / 1000 for idx in range(40)],
            "cvar_95": [-0.04 + idx / 10000 for idx in range(40)],
            **{key: [value] * 40 for key, value in run_metadata.items()},
        }
    ).to_csv(processed / "global_walk_forward_random_distribution.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "uncertainty_status": ["benchmark_self_comparison_not_applicable"],
            "uncertainty_method": ["paired_circular_block_bootstrap"],
            "paired_observations": [252],
            "bootstrap_samples": [1000],
            "block_length": [21],
            "confidence_level": [0.95],
            "sharpe_diff_ci_lower": [np.nan],
            "sharpe_diff_ci_upper": [np.nan],
            "probability_sharpe_improvement": [np.nan],
        }
    ).to_csv(processed / "global_walk_forward_uncertainty.csv", index=False)
    (processed / "global_parameter_sensitivity_summary.json").write_text(
        json.dumps(
            {
                **run_metadata,
                "robustness_status": "diagnostic_configuration_stability_only",
                "robustness_method": "current_sample_parameter_sensitivity",
                "promotion_eligible": False,
            }
        ),
        encoding="utf-8",
    )
    for filename in [
        "global_region_exposure.csv",
        "global_country_exposure.csv",
        "global_listing_country_exposure.csv",
        "global_issuer_country_exposure.csv",
        "global_economic_country_exposure.csv",
        "global_currency_exposure.csv",
        "global_exchange_exposure.csv",
        "global_sector_exposure.csv",
        "global_industry_exposure.csv",
        "global_sleeve_exposure.csv",
    ]:
        pd.DataFrame({"bucket": ["A", "B"], "weight": [0.5, 0.5]}).to_csv(
            processed / filename, index=False
        )
    pd.DataFrame(
        {
            "exposure_metadata_status": ["passed"],
            "sector_coverage_ratio": [1.0],
            "industry_coverage_ratio": [1.0],
            "issuer_country_coverage_ratio": [1.0],
            "economic_country_coverage_ratio": [1.0],
            "listing_country_coverage_ratio": [1.0],
            "metadata_confidence_distribution": ['{"medium": 1.0}'],
            "listing_country_vs_issuer_country_warning": [False],
            "interpretation": ["complete separated exposure metadata"],
            "promotion_blocker": [False],
        }
    ).to_csv(processed / "global_exposure_metadata_quality.csv", index=False)
    build_visual_analytics_outputs(processed)

    html = " ".join(
        [
            "Executive Summary",
            "<h2>Stock Scoring Methodology</h2>",
            selected_view.to_html(index=False),
            "<h2>Expected Return Forecasts</h2>",
            "Portfolio Model League",
            "Robust Model Selection",
            "Walk-Forward",
            "Exposure",
            '<h2 id="portfolio">Portfolio holdings</h2>',
            selected_view.to_html(index=False),
            (
                "Economic-country exposure is unavailable and is not inferred "
                "from listing venue, trading currency or issuer domicile."
            ),
            "<h2>Visual Portfolio Analytics</h2>",
            "Visual Portfolio Analytics",
            "Equity Curve and Drawdown",
            "Model Risk-Return Map",
            "Forecast Error Versus Random Walk",
            "Random Benchmark Distribution",
            "Exposure and Concentration",
            "Security Identity and History Eligibility",
            "Listing exposure",
            "Issuer exposure",
            "Economic exposure",
            "Limitations",
        ]
    )
    (output / "html" / "quantverse_v2_research_report.html").write_text(
        html, encoding="utf-8"
    )
    with pd.ExcelWriter(
        output / "excel" / "quantverse_v2_research_output.xlsx",
        engine="xlsxwriter",
    ) as writer:
        for sheet in [
            "EXECUTIVE_DASHBOARD",
            "PORTFOLIO",
            "HOLDINGS_DETAIL",
            "MODEL_COMPARISON",
            "MODEL_DECISIONS",
            "UNCERTAINTY",
            "RISK",
            "EXPOSURE",
            "FORECASTS",
            "ELIGIBILITY",
            "AUDIT_FINDINGS",
            "DECISION_REGISTER",
            "FORMULA_DICTIONARY",
            "DATA_DICTIONARY",
            "PORTFOLIO_DASHBOARD",
            "VISUAL_ANALYTICS_DASHBOARD",
            "START_HERE",
            "EXECUTIVE_SUMMARY",
            "SELECTED_STOCKS_RAW",
            "SELECTED_METADATA_QUALITY",
            "SECURITY_IDENTITY",
            "HISTORY_ELIGIBILITY",
            "FEATURE_ELIGIBILITY",
            "COUNT_RECONCILIATION",
            "STOCK_SCORES",
            "RETURN_FORECASTS",
            "MODEL_LEAGUE",
            "MODEL_SELECTION",
            "MODEL_SELECTION_DIAGNOSTICS",
            "FINAL_MODEL_DECISION",
            "FINAL_WEIGHTS",
            "RISK_METRICS",
            "RISK_CONTRIBUTIONS",
            "WALK_FORWARD",
            "RANDOM_PERCENTILES",
            "ROBUSTNESS",
            "EXPOSURE_REGION",
            "EXPOSURE_COUNTRY",
            "EXPOSURE_LISTING_COUNTRY",
            "EXPOSURE_ISSUER_COUNTRY",
            "EXPOSURE_ECON_COUNTRY",
            "EXPOSURE_CURRENCY",
            "EXPOSURE_EXCHANGE",
            "EXPOSURE_INDUSTRY",
            "EXPOSURE_METADATA",
            "TOP_HOLDINGS_EXPLANATION",
            "FORECAST_VALIDATION",
            "VISUAL_SUMMARY",
            "VISUAL_EQUITY_CURVE",
            "VISUAL_DRAWDOWN",
            "VISUAL_RISK_RETURN",
            "VISUAL_FORECAST_ERROR",
            "VISUAL_RANDOM_BENCH",
            "VISUAL_EXPOSURE",
            "VISUAL_TOP_HOLDINGS",
            "VISUAL_VALIDATION",
            "WARNINGS",
            "CLAIM_CONTROL",
        ]:
            pd.DataFrame({"value": [1]}).to_excel(writer, sheet_name=sheet, index=False)
        _write_selected_stocks_sheet(writer, selected_view)
    _write_pdf(
        output / "pdf" / "quantverse_v2_research_report.pdf",
        "\n".join(
            [
                "Executive Summary",
                "Stock Scoring Methodology",
                "ticker",
                "listing_country",
                "issuer_country",
                "economic_country",
                "listing_currency",
                "Expected Return Forecasts",
            ]
        ),
    )
    _write_pdf(
        output / "pdf" / "quantverse_v2_executive_research_report.pdf",
        "\n".join(
            [
                "Equal Weight",
                "not promoted",
                "Executive Summary",
                "2. Portfolio Holdings and Concentration",
                "Ticker",
                "Listing Country",
                "Issuer Country",
                "Economic Country",
                (
                    "Economic-country exposure is unavailable and is not inferred "
                    "from listing venue, trading currency or issuer domicile."
                ),
                "3. Out-of-Sample Path Evidence",
            ]
        ),
    )
    _write_pdf(
        output / "pdf" / "quantverse_v2_methodology_validation_appendix.pdf",
        "Equal Weight\nnot promoted\nMethodology and Validation",
    )
    _write_pdf(
        output / "thesis" / "quantverse_doctoral_dissertation_full.pdf",
        "QuantVerse dissertation",
    )
    _write_pdf(
        output / "thesis" / "quantverse_doctoral_defense_presentation_full.pdf",
        "QuantVerse defense",
    )
    _write_publication_manifest(
        tmp_path,
        output / "quantverse_v2_report_publication_manifest.json",
        run_metadata,
        [
            output / "pdf" / "quantverse_v2_research_report.pdf",
            output / "pdf" / "quantverse_v2_executive_research_report.pdf",
            output / "pdf" / "quantverse_v2_methodology_validation_appendix.pdf",
            output / "html" / "quantverse_v2_research_report.html",
        ],
        "quantverse_v2_pdf_html_research_package",
    )
    _write_publication_manifest(
        tmp_path,
        output / "quantverse_v2_excel_publication_manifest.json",
        run_metadata,
        [output / "excel" / "quantverse_v2_research_output.xlsx"],
        "quantverse_v2_analytical_workbook",
    )
    register_artifacts(
        processed,
        [
            *list(processed.iterdir()),
            universe_dir / "current_global_equity_universe.csv",
        ],
        run_metadata,
        root=tmp_path,
    )

    result = validate_artifacts(tmp_path)

    assert result["overall_status"] == "passed"
    assert result["failed_check_count"] == 0

    stale_provenance = dict(provenance)
    stale_provenance["random_oos_dates_hash"] = "dates-static-full-sample"
    (processed / "global_walk_forward_random_benchmark_provenance.json").write_text(
        json.dumps(stale_provenance), encoding="utf-8"
    )
    stale_result = validate_artifacts(tmp_path)
    assert any(
        check["check"] == "random_benchmark_is_same_protocol_walk_forward_oos_net"
        and not check["passed"]
        for check in stale_result["checks"]
    )

    (processed / "global_walk_forward_random_benchmark_provenance.json").write_text(
        json.dumps(provenance), encoding="utf-8"
    )
    decision_path = processed / "global_final_model_decision.json"
    original_decision = json.loads(decision_path.read_text(encoding="utf-8"))
    false_decision = dict(original_decision)
    false_decision["final_decision"] = "promoted"
    decision_path.write_text(json.dumps(false_decision), encoding="utf-8")
    decision_result = validate_artifacts(tmp_path)
    assert any(
        check["check"] == "final_decision_is_fail_closed_for_public_data_scope"
        and not check["passed"]
        for check in decision_result["checks"]
    )
    decision_path.write_text(json.dumps(original_decision), encoding="utf-8")

    false_robustness = pd.read_csv(processed / "global_model_selection_report.csv")
    false_robustness["robustness_gate_pass"] = True
    false_robustness.to_csv(
        processed / "global_model_selection_report.csv",
        index=False,
    )
    robustness_result = validate_artifacts(tmp_path)
    assert any(
        check["check"] == "robustness_promotion_gate_fails_closed"
        and not check["passed"]
        for check in robustness_result["checks"]
    )

    missing_data_audit = pd.read_csv(
        processed / "quantverse_v2_missing_data_operation_audit.csv"
    )
    missing_data_audit.loc[0, "approved"] = False
    missing_data_audit.to_csv(
        processed / "quantverse_v2_missing_data_operation_audit.csv",
        index=False,
    )
    missing_data_result = validate_artifacts(tmp_path)
    assert any(
        check["check"] == "missing_data_operations_are_explicitly_reviewed"
        and not check["passed"]
        for check in missing_data_result["checks"]
    )


def test_artifact_validator_fails_on_final_model_mismatch(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "run_status": "completed",
                "final_selected_model": "Risk Parity",
                "final_model_selection_method": "robust_public_data_evidence_gate",
                "final_model_selection_score": 1.0,
                "final_model_selection_decision": "not promoted",
                "promotion_decision": "not promoted",
                "weight_sum": 1.0,
                "final_selected_holdings": 2,
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_final_model_decision.json").write_text(
        json.dumps(
            {
                "final_selected_model": "Equal Weight",
                "final_model_selection_method": "robust_public_data_evidence_gate",
                "final_model_selection_score": 1.0,
                "final_decision": "not promoted",
                "final_decision_reason": "Fixture.",
                "publish_readiness_status": "research_publish_ready_with_limitations",
            }
        ),
        encoding="utf-8",
    )

    result = validate_artifacts(tmp_path)

    assert result["overall_status"] == "failed"
    assert any(
        check["check"] == "summary_matches_final_model_decision" and not check["passed"]
        for check in result["checks"]
    )


def test_artifact_validator_fails_on_summary_numerical_integrity_mismatch(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "run_status": "completed",
                "final_selected_model": "Equal Weight",
                "numerical_integrity_status": "failed",
                "numerical_integrity_failed_checks": 3,
            }
        ),
        encoding="utf-8",
    )

    result = validate_artifacts(tmp_path)

    assert any(
        check["check"] == "summary_numerical_integrity_matches_artifact_validation"
        and not check["passed"]
        for check in result["checks"]
    )


def test_artifact_validator_fails_on_current_report_stale_decision_phrase(tmp_path):
    processed = tmp_path / "data" / "processed"
    output = tmp_path / "output" / "html"
    processed.mkdir(parents=True)
    output.mkdir(parents=True)
    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps({"run_status": "completed", "final_selected_model": "HRP"}),
        encoding="utf-8",
    )
    (output / "quantverse_v2_research_report.html").write_text(
        "Final model set to Equal Weight; best metric candidate Min CVaR was not used.",
        encoding="utf-8",
    )

    result = validate_artifacts(tmp_path)

    assert any(
        check["check"] == "current_v2_reports_no_stale_decision_phrases"
        and not check["passed"]
        for check in result["checks"]
    )


def test_portfolio_input_audit_detects_short_history_weight_leakage(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        {
            "Model": ["Equal Weight"],
            "Ticker": ["SPCX"],
            "Weight": [1.0],
        }
    ).to_csv(processed / "global_master_candidate_weights.csv", index=False)
    pd.DataFrame(
        {
            "Sharpe": [1.0],
            "weight_SPCX": [1.0],
        }
    ).to_csv(processed / "global_master_random_portfolio_benchmark.csv", index=False)
    pd.DataFrame({"ticker": ["SPCX"]}).to_csv(
        processed / "global_master_selected_assets.csv", index=False
    )
    pd.DataFrame({"SPCX": [1.0]}).to_csv(
        processed / "global_correlation_matrix.csv", index=False
    )

    violations = _portfolio_input_violations(processed, {"SPCX"})

    assert violations == ["SPCX"]


def test_artifact_validator_cli_imports_from_outside_repository(tmp_path):
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "validate_quantverse_v2_artifacts.py"
    )

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        "Validate generated QuantVerse v2 release-candidate artifacts" in result.stdout
    )
