from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from project.research.global_visual_analytics import (
    VISUAL_ANALYTICS_FILES,
    _resolve_final_model,
    build_drawdown_curve,
    build_equity_curve,
    build_exposure_chart,
    build_forecast_error_chart,
    build_model_risk_return_chart,
    build_random_benchmark_chart,
    build_top_holdings_chart,
    build_visual_analytics_outputs,
    validate_visual_analytics_frames,
    validate_visual_analytics_outputs,
)


def test_equity_curve_starts_at_one_and_drawdown_non_positive():
    returns = pd.Series(
        [0.02, -0.01, 0.03, -0.02],
        index=pd.date_range("2024-01-01", periods=4, freq="B"),
    )

    equity = build_equity_curve(returns, final_model="HRP")
    drawdown = build_drawdown_curve(equity, final_model="HRP")

    assert equity["equity_curve"].iloc[0] == 1.0
    assert len(equity) == len(returns) + 1
    assert equity["is_baseline"].tolist() == [True, False, False, False, False]
    assert equity["equity_curve"].iloc[-1] == pytest.approx(
        float(np.prod(1.0 + returns.to_numpy(dtype=float)))
    )
    assert (drawdown["drawdown"] <= 0.0).all()


def test_model_risk_return_uses_risk_x_return_y():
    walk_forward = pd.DataFrame(
        {
            "model_name": ["Equal Weight", "HRP"],
            "avg_annualized_return": [0.10, 0.12],
            "avg_volatility": [0.20, 0.16],
            "avg_sharpe": [0.50, 0.75],
            "avg_sortino": [0.60, 0.90],
            "avg_max_drawdown": [-0.20, -0.12],
            "avg_cvar_95": [-0.03, -0.02],
        }
    )

    chart = build_model_risk_return_chart(
        pd.DataFrame(), walk_forward, final_model="HRP"
    )

    assert chart["x_axis"].eq("annualized_volatility").all()
    assert chart["y_axis"].eq("annualized_return").all()
    assert bool(chart.loc[chart["model_name"].eq("HRP"), "is_final_model"].iloc[0])


def test_forecast_error_chart_compares_model_and_random_walk():
    validation = pd.DataFrame(
        {
            "horizon": ["1M", "3M"],
            "horizon_days": [21, 63],
            "mean_mae": [0.08, 0.10],
            "mean_random_walk_mae": [0.09, 0.11],
            "forecast_validation_status": ["validated_diagnostic"] * 2,
            "allocation_signal_status": ["diagnostic_only"] * 2,
        }
    )

    chart = build_forecast_error_chart(validation)

    assert {"model_mae", "random_walk_mae"}.issubset(chart.columns)
    assert np.allclose(
        chart["model_minus_random_walk_mae"],
        chart["model_mae"] - chart["random_walk_mae"],
    )


def test_random_benchmark_chart_is_not_degenerate():
    random_distribution = pd.DataFrame(
        {
            "sharpe": np.linspace(-0.5, 1.5, 50),
            "portfolio_id": range(50),
            "sampling_method": ["iid_uniform_raw_scores_projected_to_capped_simplex"]
            * 50,
            "benchmark_scope": ["walk_forward_oos_net"] * 50,
        }
    )
    random_percentiles = pd.DataFrame(
        {"model_name": ["HRP"], "sharpe_percentile": [0.86]}
    )
    model_risk_return = pd.DataFrame({"model_name": ["HRP"], "sharpe": [0.8]})

    chart = build_random_benchmark_chart(
        random_distribution,
        random_percentiles,
        model_risk_return,
        final_model="HRP",
    )

    assert chart["portfolio_count"].sum() == 50
    assert not chart["is_degenerate"].any()
    assert set(chart["sampling_method"]) == {
        "iid_uniform_raw_scores_projected_to_capped_simplex"
    }
    assert set(chart["benchmark_scope"]) == {"walk_forward_oos_net"}


def test_exposure_chart_sums_to_one(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
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
        pd.DataFrame({"bucket": ["A", "B"], "weight": [0.4, 0.6]}).to_csv(
            processed / filename, index=False
        )

    chart = build_exposure_chart(processed)
    sums = chart.groupby("exposure_type")["weight"].sum()

    assert np.allclose(sums.to_numpy(dtype=float), 1.0)


def test_top_holdings_weights_are_non_negative():
    weights = pd.DataFrame(
        {
            "model_name": ["HRP", "HRP", "Equal Weight"],
            "ticker": ["A", "B", "A"],
            "weight": [0.7, 0.3, 1.0],
        }
    )

    chart = build_top_holdings_chart(weights, final_model="HRP")

    assert (chart["weight"] >= 0.0).all()
    assert chart["weight"].sum() == 1.0


def test_visual_analytics_outputs_have_required_schema(tmp_path):
    processed = _write_visual_fixture(tmp_path)

    outputs = build_visual_analytics_outputs(processed)
    validation = validate_visual_analytics_frames(outputs)

    assert validation["passed"].astype(bool).all()
    for key, filename in VISUAL_ANALYTICS_FILES.items():
        assert key in outputs
        assert (processed / filename).exists()
    assert set(outputs["model_risk_return"]["x_axis"]) == {"annualized_volatility"}
    assert set(outputs["model_risk_return"]["y_axis"]) == {"annualized_return"}
    assert set(outputs["equity_curve"]["evidence_scope"]) == {"walk_forward_oos_net"}
    assert int(outputs["equity_curve"]["source_observations"].iloc[0]) == 6
    assert len(outputs["equity_curve"]) == 7
    exposure_summary = (
        outputs["summary"].loc[outputs["summary"]["chart_name"].eq("exposure")].iloc[0]
    )
    assert exposure_summary["validation_status"] == "passed_with_metadata_warning"


def test_visual_validation_rejects_partial_non_finite_chart_values(tmp_path):
    processed = _write_visual_fixture(tmp_path)
    outputs = build_visual_analytics_outputs(processed)
    outputs["drawdown_curve"].loc[1, "drawdown"] = np.nan
    outputs["model_risk_return"].loc[0, "risk_x"] = np.nan
    outputs["forecast_error"].loc[0, "model_mae"] = np.nan
    outputs["random_benchmark"]["is_degenerate"] = outputs["random_benchmark"][
        "is_degenerate"
    ].astype(object)
    outputs["random_benchmark"].loc[0, "is_degenerate"] = np.nan
    outputs["exposure"].loc[0, "weight"] = np.nan

    validation = validate_visual_analytics_frames(outputs).set_index("check")

    assert not bool(validation.loc["drawdown_non_positive", "passed"])
    assert not bool(validation.loc["risk_return_axes_correct", "passed"])
    assert not bool(validation.loc["forecast_compares_random_walk", "passed"])
    assert not bool(validation.loc["random_benchmark_not_degenerate", "passed"])
    assert not bool(validation.loc["exposure_sums_to_one", "passed"])


def test_visual_final_model_does_not_fallback_to_demo_summary():
    with pytest.raises(ValueError, match="demo-summary fallback is not accepted"):
        _resolve_final_model({}, {"final_selected_model": "HRP"})


def test_visual_validator_rejects_full_sample_curve_labelled_as_oos(tmp_path):
    processed = _write_visual_fixture(tmp_path)
    build_visual_analytics_outputs(processed)
    full_sample = pd.Series(
        [0.001] * 80,
        index=pd.date_range("2024-01-01", periods=80, freq="B"),
    )
    wrong_equity = build_equity_curve(full_sample, final_model="HRP")
    wrong_drawdown = build_drawdown_curve(wrong_equity, final_model="HRP")
    wrong_equity.to_csv(
        processed / VISUAL_ANALYTICS_FILES["equity_curve"],
        index=False,
    )
    wrong_drawdown.to_csv(
        processed / VISUAL_ANALYTICS_FILES["drawdown_curve"],
        index=False,
    )

    result = validate_visual_analytics_outputs(processed)

    assert result["overall_status"] == "failed"
    assert any(
        row["check"] == "published_equity_curve_reconciles_stitched_oos_source"
        and not row["passed"]
        for row in result["checks"]
    )


def test_visual_analytics_does_not_fabricate_final_model(tmp_path):
    processed = _write_visual_fixture(tmp_path)
    (processed / "global_final_model_decision.json").unlink()
    (processed / "quantverse_v2_demo_summary.json").unlink()

    with pytest.raises(ValueError, match="explicit, available final-model"):
        build_visual_analytics_outputs(processed)


def _write_visual_fixture(root: Path) -> Path:
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=80, freq="B"),
            "A": [0.001] * 80,
            "B": [0.002, -0.001] * 40,
        }
    ).to_csv(processed / "global_security_simple_returns_usd.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["HRP", "HRP", "Equal Weight", "Equal Weight"],
            "ticker": ["A", "B", "A", "B"],
            "weight": [0.6, 0.4, 0.5, 0.5],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    oos_dates = pd.date_range("2024-04-01", periods=6, freq="B")
    pd.DataFrame(
        [
            {
                "Date": date,
                "fold": 0 if index < 3 else 1,
                "model_name": model,
                "return": value,
            }
            for model, values in [
                ("HRP", [0.01, -0.02, 0.015, 0.005, -0.003, 0.012]),
                ("Equal Weight", [0.008, -0.018, 0.012, 0.004, -0.002, 0.010]),
            ]
            for index, (date, value) in enumerate(zip(oos_dates, values, strict=True))
        ]
    ).to_csv(processed / "global_walk_forward_returns.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["HRP", "Equal Weight"],
            "annualized_return": [0.12, 0.10],
            "annualized_volatility": [0.16, 0.20],
            "sharpe": [0.75, 0.50],
            "sortino": [0.90, 0.60],
            "max_drawdown": [-0.12, -0.20],
            "cvar_95": [-0.02, -0.03],
        }
    ).to_csv(processed / "global_portfolio_risk_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["HRP", "Equal Weight"],
            "avg_annualized_return": [0.11, 0.09],
            "avg_volatility": [0.15, 0.18],
            "avg_sharpe": [0.73, 0.50],
            "avg_sortino": [0.86, 0.55],
            "avg_max_drawdown": [-0.10, -0.18],
            "avg_cvar_95": [-0.02, -0.03],
        }
    ).to_csv(processed / "global_walk_forward_model_comparison.csv", index=False)
    pd.DataFrame(
        {"portfolio_id": range(40), "sharpe": np.linspace(-0.4, 1.2, 40)}
    ).to_csv(processed / "global_random_portfolio_distribution.csv", index=False)
    pd.DataFrame({"model_name": ["HRP"], "sharpe_percentile": [0.86]}).to_csv(
        processed / "global_random_portfolio_percentile_report.csv", index=False
    )
    pd.DataFrame(
        {
            "horizon": ["1M"],
            "horizon_days": [21],
            "mean_mae": [0.08],
            "mean_random_walk_mae": [0.09],
            "forecast_validation_status": ["validated_diagnostic"],
            "allocation_signal_status": ["diagnostic_only"],
        }
    ).to_csv(processed / "global_forecast_validation_by_horizon.csv", index=False)
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
        pd.DataFrame({"bucket": ["A", "B"], "weight": [0.6, 0.4]}).to_csv(
            processed / filename, index=False
        )
    pd.DataFrame(
        {
            "exposure_metadata_status": ["passed_with_metadata_warning"],
            "sector_coverage_ratio": [1.0],
            "industry_coverage_ratio": [1.0],
            "issuer_country_coverage_ratio": [1.0],
            "economic_country_coverage_ratio": [0.0],
            "listing_country_coverage_ratio": [1.0],
            "metadata_confidence_distribution": ['{"medium": 1.0}'],
            "listing_country_vs_issuer_country_warning": [False],
            "interpretation": ["economic exposure unavailable"],
            "promotion_blocker": [True],
        }
    ).to_csv(processed / "global_exposure_metadata_quality.csv", index=False)
    (processed / "global_final_model_decision.json").write_text(
        '{"final_selected_model": "HRP"}',
        encoding="utf-8",
    )
    (processed / "quantverse_v2_demo_summary.json").write_text(
        '{"final_selected_model": "HRP"}',
        encoding="utf-8",
    )
    return processed
