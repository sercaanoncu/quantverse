from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.run_global_robustness_analysis as robustness_cli
from project.research.global_portfolio_core import (
    CanonicalPortfolioPolicy,
    normalize_issuer_name,
    project_group_constrained_weights,
    sample_constraint_feasible_weights,
    select_canonical_securities,
    validate_portfolio_constraints,
)
from project.research.global_portfolio_risk import evaluate_return_series


def _metadata_and_scores() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    score_rows = []
    for index in range(36):
        ticker = f"T{index:02d}"
        rows.append(
            {
                "ticker": ticker,
                "issuer_name": f"Issuer {index}",
                "issuer_key": f"issuer-{index}",
                "issuer_key_source": "normalized_issuer_name_fallback",
                "sector": f"Sector {index % 8}",
                "industry": f"Industry {index % 12}",
                "issuer_country": f"Country {index % 4}",
                "observations": 700,
                "missing_rate": 0.0,
                "median_dollar_volume": np.nan,
                "constraint_metadata_complete": True,
            }
        )
        score_rows.append(
            {
                "ticker": ticker,
                "observations": 700,
                "data_coverage_score": 1.0,
                "composite_quant_score": float(100 - index),
                "standard_composite_score_eligible": True,
            }
        )
    rows.append(
        {
            **rows[0],
            "ticker": "T00B",
            "observations": 650,
        }
    )
    score_rows.append(
        {
            **score_rows[0],
            "ticker": "T00B",
            "observations": 650,
            "composite_quant_score": 101.0,
        }
    )
    return pd.DataFrame(rows), pd.DataFrame(score_rows)


def test_requested_five_percent_cap_is_explicitly_model_degenerate():
    policy = CanonicalPortfolioPolicy()
    assert policy.requested_cap_is_model_degenerate is True
    assert policy.target_holdings * policy.requested_max_issuer_weight == 1.0


def test_canonical_selection_has_twenty_unique_issuers_and_group_caps():
    metadata, scores = _metadata_and_scores()
    policy = CanonicalPortfolioPolicy()
    selected, audit = select_canonical_securities(scores, metadata, policy)
    assert len(selected) == 20
    assert selected["issuer_key"].nunique() == 20
    assert "T00" in selected["ticker"].tolist()
    duplicate = audit.loc[audit["ticker"].eq("T00B")].iloc[0]
    assert duplicate["selection_reason"].startswith("duplicate_economic_issuer")
    assert selected["sector"].value_counts().max() <= 5
    assert selected["industry"].value_counts().max() <= 3
    assert selected["issuer_country"].value_counts().max() <= 12


def test_group_projection_keeps_all_holdings_and_passes_constraints():
    metadata, scores = _metadata_and_scores()
    policy = CanonicalPortfolioPolicy()
    selected, _ = select_canonical_securities(scores, metadata, policy)
    raw = pd.Series(
        np.arange(1, 21, dtype=float),
        index=selected["ticker"],
    )
    weights = project_group_constrained_weights(raw, selected, policy)
    result = validate_portfolio_constraints(weights, selected, policy)
    assert result["all_constraints_pass"] is True
    assert result["holdings_count"] == 20
    assert np.isclose(weights.sum(), 1.0)


def test_constraint_feasible_random_portfolios_are_reproducible_and_non_degenerate():
    metadata, scores = _metadata_and_scores()
    policy = CanonicalPortfolioPolicy()
    selected, _ = select_canonical_securities(scores, metadata, policy)
    rng_one = np.random.default_rng(42)
    rng_two = np.random.default_rng(42)
    samples_one = pd.DataFrame(
        [
            sample_constraint_feasible_weights(selected, policy, rng_one)
            for _ in range(5)
        ]
    )
    samples_two = pd.DataFrame(
        [
            sample_constraint_feasible_weights(selected, policy, rng_two)
            for _ in range(5)
        ]
    )
    pd.testing.assert_frame_equal(samples_one, samples_two)
    assert float(samples_one.var(axis=0).sum()) > 0.0
    assert np.allclose(samples_one.sum(axis=1), 1.0)


def test_time_aligned_daily_risk_free_hurdle_changes_primary_sharpe():
    dates = pd.date_range("2024-01-02", periods=252, freq="B")
    returns = pd.Series(
        np.tile([0.0010, 0.0], 126),
        index=dates,
    )
    daily_hurdle = pd.Series(np.full(252, 0.0002), index=dates)
    zero_rf = evaluate_return_series(returns)
    market_rf = evaluate_return_series(returns, risk_free_daily=daily_hurdle)
    assert market_rf["sharpe"] < zero_rf["sharpe"]


def test_normalized_issuer_name_collapses_share_class_suffixes():
    assert normalize_issuer_name("Example Corp Class A") == normalize_issuer_name(
        "Example Corp Class B"
    )


def test_robustness_uses_persisted_market_rf_when_scalar_is_disabled(
    tmp_path,
    monkeypatch,
):
    dates = pd.date_range("2025-01-02", periods=3, freq="B")
    evidence = pd.DataFrame({"Date": dates, "annual_rate": [0.04, 0.041, 0.042]})
    monkeypatch.setattr(robustness_cli, "PROCESSED", tmp_path)
    evidence.to_csv(tmp_path / "global_risk_free_series.csv", index=False)
    observed = robustness_cli._diagnostic_annual_risk_free(
        {"risk_free_rate_annual": None}, dates
    )
    assert observed == pytest.approx(0.041)
