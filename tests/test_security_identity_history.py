import numpy as np
import pandas as pd

from project.data_pipeline.global_returns import normalize_returns_to_base
from project.data_pipeline.security_identity import (
    apply_security_history_boundaries,
    build_feature_history_eligibility,
    build_security_identity_audit,
    resolve_security_master_rows,
)
from project.research.global_portfolio_league import build_portfolio_league
from project.research.global_stock_scoring import build_global_stock_scores


def _override(continuity: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["NEW"],
            "current_security_name": ["New Issuer"],
            "issuer_name": ["New Issuer"],
            "current_listing_start_date": ["2026-01-05"],
            "ticker_reuse_status": ["known_reuse_prior_unrelated_security"],
            "identity_continuity_status": [continuity],
            "metadata_source": ["unit"],
            "evidence_confidence": ["high"],
        }
    )


def _universe(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": tickers,
            "name": tickers,
            "sleeve": ["global_equity_us"] * len(tickers),
            "region": ["North America"] * len(tickers),
            "country": ["United States"] * len(tickers),
            "exchange": ["NASDAQ"] * len(tickers),
            "currency": ["USD"] * len(tickers),
            "asset_type": ["equity"] * len(tickers),
            "investable": [True] * len(tickers),
            "include": [True] * len(tickers),
            "benchmark_only": [False] * len(tickers),
            "signal_only": [False] * len(tickers),
            "data_provider": ["unit"] * len(tickers),
            "source": ["unit"] * len(tickers),
            "source_method": ["api_market_cap_enriched"] * len(tickers),
            "market_cap_usd": np.arange(len(tickers), 0, -1) * 1_000_000,
        }
    )


def test_reused_ticker_history_is_truncated_at_current_security_boundary():
    dates = pd.to_datetime(["2021-01-04", "2025-12-31", "2026-01-05", "2026-01-06"])
    prices = pd.DataFrame({"NEW": [10.0, 12.0, 50.0, 51.0]}, index=dates)

    clean, report = apply_security_history_boundaries(
        prices,
        _override("verified_current_security_from_listing_date"),
    )

    assert clean.loc[dates[:2], "NEW"].isna().all()
    assert clean.loc[dates[2:], "NEW"].notna().all()
    assert int(report.loc[0, "observations_before_boundary"]) == 2
    assert bool(report.loc[0, "history_truncation_applied"]) is True


def test_verified_same_security_rename_continuity_is_not_truncated():
    dates = pd.to_datetime(["2025-12-31", "2026-01-05", "2026-01-06"])
    prices = pd.DataFrame({"NEW": [49.0, 50.0, 51.0]}, index=dates)

    clean, report = apply_security_history_boundaries(
        prices,
        _override("verified_same_security_continuity"),
    )

    pd.testing.assert_frame_equal(clean, prices)
    assert int(report.loc[0, "observations_before_boundary"]) == 1
    assert bool(report.loc[0, "history_truncation_applied"]) is False


def test_canonical_security_row_prioritizes_included_investable_record():
    universe = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "name": ["Excluded proxy", "Included security"],
            "sleeve": ["global_equity_nasdaq", "global_equity_us"],
            "currency": ["USD", "USD"],
            "asset_type": ["equity", "equity"],
            "investable": [True, True],
            "include": [False, True],
            "benchmark_only": [False, False],
            "signal_only": [False, False],
            "source_method": ["index_proxy", "api_market_cap_enriched"],
            "as_of_date": ["2026-01-01", "2026-01-02"],
        }
    )
    canonical = resolve_security_master_rows(universe)
    local = pd.DataFrame(
        {"AAA": [0.01, 0.02]},
        index=pd.date_range("2026-01-05", periods=2, freq="B"),
    )

    converted, report, _ = normalize_returns_to_base(local, universe)

    assert canonical.loc[0, "name"] == "Included security"
    assert report.loc[0, "fx_normalization_status"] == "native_base"
    pd.testing.assert_series_equal(converted["AAA"], local["AAA"], check_names=False)


def test_identity_audit_records_removed_contamination_and_short_history():
    dates = pd.to_datetime(["2025-12-31", "2026-01-05", "2026-01-06", "2026-01-07"])
    provider = pd.DataFrame({"NEW": [10.0, 50.0, 51.0, 52.0]}, index=dates)
    valid, truncation = apply_security_history_boundaries(
        provider,
        _override("verified_current_security_from_listing_date"),
    )
    returns = valid.pct_change(fill_method=None)
    audit = build_security_identity_audit(
        _universe(["NEW"]),
        provider,
        valid,
        returns,
        _override("verified_current_security_from_listing_date"),
        truncation,
    )
    row = audit.iloc[0]

    assert int(row["observations_before_current_listing"]) == 1
    assert row["history_contamination_status"] == "detected_and_removed"
    assert row["eligibility_status"] == "diagnostic_short_history"
    assert bool(row["standard_scoring_eligible"]) is False


def test_hrp_inputs_change_only_when_history_repair_changes_eligible_universe():
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    contaminated = pd.DataFrame(
        rng.normal(0.0004, 0.01, size=(300, 4)),
        index=dates,
        columns=["A", "B", "C", "NEW"],
    )
    corrected = contaminated.copy()
    corrected.loc[dates[:-40], "NEW"] = np.nan
    universe = _universe(list(contaminated.columns))

    contaminated_features = build_feature_history_eligibility(contaminated)
    corrected_features = build_feature_history_eligibility(corrected)
    contaminated_scores = build_global_stock_scores(
        contaminated,
        universe,
        max_selected=4,
        feature_history_eligibility=contaminated_features,
    )
    corrected_scores = build_global_stock_scores(
        corrected,
        universe,
        max_selected=4,
        feature_history_eligibility=corrected_features,
    )
    _, contaminated_weights, _ = build_portfolio_league(
        contaminated,
        contaminated_scores,
        metadata=universe,
        max_assets=4,
        max_weight=0.50,
    )
    _, corrected_weights, _ = build_portfolio_league(
        corrected,
        corrected_scores,
        metadata=universe,
        max_assets=4,
        max_weight=0.50,
    )
    contaminated_hrp = contaminated_weights.loc[
        contaminated_weights["model_name"].eq("HRP")
    ]
    corrected_hrp = corrected_weights.loc[corrected_weights["model_name"].eq("HRP")]

    assert "NEW" in set(contaminated_hrp["ticker"])
    assert "NEW" not in set(corrected_hrp["ticker"])
    assert (
        corrected_scores.loc[corrected_scores["ticker"].eq("NEW"), "eligibility_status"]
        .eq("diagnostic_short_history")
        .all()
    )


def test_no_boundary_change_produces_identical_hrp_weights():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2026-01-05", periods=260, freq="B")
    returns = pd.DataFrame(
        rng.normal(0.0003, 0.01, size=(260, 3)),
        index=dates,
        columns=["A", "B", "NEW"],
    )
    universe = _universe(list(returns.columns))
    scores = build_global_stock_scores(returns, universe, max_selected=3)
    _, first, _ = build_portfolio_league(
        returns, scores, metadata=universe, max_assets=3, max_weight=0.50
    )
    _, second, _ = build_portfolio_league(
        returns.copy(), scores.copy(), metadata=universe, max_assets=3, max_weight=0.50
    )
    first_hrp = first.loc[first["model_name"].eq("HRP")].set_index("ticker")["weight"]
    second_hrp = second.loc[second["model_name"].eq("HRP")].set_index("ticker")[
        "weight"
    ]

    pd.testing.assert_series_equal(first_hrp, second_hrp)
