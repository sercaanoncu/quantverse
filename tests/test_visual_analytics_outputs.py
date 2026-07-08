from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_visual_analytics import (
    VISUAL_ANALYTICS_FILES,
    build_drawdown_curve,
    build_equity_curve,
    build_exposure_chart,
    build_forecast_error_chart,
    build_model_risk_return_chart,
    build_random_benchmark_chart,
    build_top_holdings_chart,
    build_visual_analytics_outputs,
    validate_visual_analytics_frames,
)


def test_equity_curve_starts_at_one_and_drawdown_non_positive():
    returns = pd.Series(
        [0.02, -0.01, 0.03, -0.02],
        index=pd.date_range("2024-01-01", periods=4, freq="B"),
    )

    equity = build_equity_curve(returns, final_model="HRP")
    drawdown = build_drawdown_curve(equity, final_model="HRP")

    assert equity["equity_curve"].iloc[0] == 1.0
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
        {"sharpe": np.linspace(-0.5, 1.5, 50), "portfolio_id": range(50)}
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


def test_exposure_chart_sums_to_one(tmp_path):
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    for filename in [
        "global_region_exposure.csv",
        "global_country_exposure.csv",
        "global_currency_exposure.csv",
        "global_sector_exposure.csv",
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
    exposure_summary = (
        outputs["summary"].loc[outputs["summary"]["chart_name"].eq("exposure")].iloc[0]
    )
    assert exposure_summary["validation_status"] == "passed_with_metadata_warning"


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
        "global_currency_exposure.csv",
        "global_sector_exposure.csv",
        "global_sleeve_exposure.csv",
    ]:
        pd.DataFrame({"bucket": ["A", "B"], "weight": [0.6, 0.4]}).to_csv(
            processed / filename, index=False
        )
    (processed / "global_final_model_decision.json").write_text(
        '{"final_selected_model": "HRP"}',
        encoding="utf-8",
    )
    (processed / "quantverse_v2_demo_summary.json").write_text(
        '{"final_selected_model": "HRP"}',
        encoding="utf-8",
    )
    return processed
