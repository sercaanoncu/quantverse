import pandas as pd
import pytest

from project.research.global_exposure_analysis import build_exposure_analysis


def test_exposure_fails_closed_when_requested_final_model_is_missing():
    weights = pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "ticker": ["A"],
            "weight": [1.0],
        }
    )
    universe = pd.DataFrame({"ticker": ["A"], "name": ["Asset A"]})

    with pytest.raises(ValueError, match="missing from the weight artifact"):
        build_exposure_analysis(weights, universe, final_model="HRP")


def test_exposure_rejects_non_numeric_or_non_unit_weights():
    universe = pd.DataFrame({"ticker": ["A", "B"], "name": ["A", "B"]})
    malformed = pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "weight": [0.5, "missing"],
        }
    )
    non_unit = malformed.assign(weight=[0.4, 0.4])

    with pytest.raises(ValueError, match="finite numeric"):
        build_exposure_analysis(malformed, universe, final_model="Equal Weight")
    with pytest.raises(ValueError, match="sum to 1.0"):
        build_exposure_analysis(non_unit, universe, final_model="Equal Weight")


def test_exposure_sums_to_one_and_top_holdings_explanation_exists():
    weights = pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "weight": [0.6, 0.4],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "name": ["Asset A", "Asset B"],
            "sleeve": ["global_equity_us", "defensive_bonds_cash"],
            "region": ["North America", "North America"],
            "country": ["United States", "United States"],
            "currency": ["USD", "USD"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="Equal Weight")

    assert exposure["region"]["weight"].sum() == 1.0
    assert exposure["sleeve"]["weight"].sum() == 1.0
    assert exposure["listing_country"]["weight"].sum() == 1.0
    assert "explanation" in exposure["top_holdings"]
    assert "sector" in exposure
    assert "industry" in exposure
    assert "metadata_quality" in exposure


def test_exposure_warning_triggers_for_concentration_and_missing_sector_gracefully():
    weights = pd.DataFrame(
        {
            "model_name": ["GMV", "GMV"],
            "ticker": ["A", "B"],
            "weight": [0.8, 0.2],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "name": ["Asset A", "Asset B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "region": ["North America", "North America"],
            "country": ["United States", "United States"],
            "currency": ["USD", "USD"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="GMV")

    assert "sector" in exposure
    assert exposure["warnings"]["warning_type"].str.contains("concentration").any()


def test_exposure_metadata_incomplete_when_sector_and_issuer_country_missing():
    weights = pd.DataFrame(
        {
            "model_name": ["HRP", "HRP"],
            "ticker": ["A", "B"],
            "weight": [0.7, 0.3],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "name": ["Asset A", "Asset B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "region": ["North America", "North America"],
            "country": ["United States", "United States"],
            "currency": ["USD", "USD"],
            "sector": ["missing", "missing"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="HRP")
    quality = exposure["metadata_quality"].iloc[0]

    assert quality["exposure_metadata_status"] == "diagnostic_metadata_incomplete"
    assert quality["sector_coverage_ratio"] == 0.0
    assert quality["issuer_country_coverage_ratio"] == 0.0
    assert bool(quality["listing_country_vs_issuer_country_warning"])
    assert exposure["warnings"]["warning_type"].eq("exposure_metadata_incomplete").any()


def test_listing_country_and_issuer_country_are_separate_exposures():
    weights = pd.DataFrame(
        {
            "model_name": ["HRP"],
            "ticker": ["UBS"],
            "weight": [1.0],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["UBS"],
            "name": ["UBS Group AG"],
            "sleeve": ["global_equity_us"],
            "region": ["North America"],
            "country": ["United States"],
            "listing_country": ["United States"],
            "issuer_country": ["Switzerland"],
            "economic_country": ["missing"],
            "currency": ["USD"],
            "sector": ["Financial Services"],
            "industry": ["Banks - Diversified"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="HRP")
    listing = exposure["listing_country"].set_index("bucket")["weight"]
    issuer = exposure["issuer_country"].set_index("bucket")["weight"]
    top = exposure["top_holdings"].iloc[0]

    assert listing["United States"] == 1.0
    assert issuer["Switzerland"] == 1.0
    assert bool(top["adr_or_foreign_issuer_flag"])
    assert exposure["metadata_quality"].iloc[0]["exposure_metadata_status"] == (
        "passed_with_metadata_warning"
    )


def test_partial_metadata_warns_instead_of_plain_pass():
    weights = pd.DataFrame(
        {
            "model_name": ["HRP", "HRP"],
            "ticker": ["A", "B"],
            "weight": [0.6, 0.4],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "name": ["Asset A", "Asset B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "region": ["North America", "North America"],
            "country": ["United States", "United States"],
            "issuer_country": ["United States", "missing"],
            "currency": ["USD", "USD"],
            "sector": ["Technology", "missing"],
            "industry": ["Software", "missing"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="HRP")
    quality = exposure["metadata_quality"].iloc[0]

    assert quality["exposure_metadata_status"] == "passed_with_metadata_warning"
    assert quality["sector_coverage_ratio"] == 0.6
    assert quality["issuer_country_coverage_ratio"] == 0.6
    assert bool(quality["promotion_blocker"])


def test_adr_like_ticker_does_not_become_us_issuer_by_default():
    weights = pd.DataFrame(
        {
            "model_name": ["HRP"],
            "ticker": ["UBS"],
            "weight": [1.0],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["UBS"],
            "name": ["UBS Group AG"],
            "sleeve": ["global_equity_us"],
            "region": ["North America"],
            "country": ["United States"],
            "currency": ["USD"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="HRP")
    issuer = exposure["issuer_country"].set_index("bucket")["weight"]
    top = exposure["top_holdings"].iloc[0]

    assert issuer["missing"] == 1.0
    assert bool(top["adr_or_foreign_issuer_flag"])
    assert "foreign_issuer_review_required" in top["metadata_missing_reason"]


def test_all_exposure_types_sum_to_one_when_metadata_is_available():
    weights = pd.DataFrame(
        {
            "model_name": ["HRP", "HRP"],
            "ticker": ["A", "B"],
            "weight": [0.55, 0.45],
        }
    )
    universe = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "name": ["Asset A", "Asset B"],
            "sleeve": ["global_equity_us", "global_equity_europe"],
            "region": ["North America", "Europe"],
            "listing_country": ["United States", "Germany"],
            "issuer_country": ["United States", "Germany"],
            "economic_country": ["United States", "Germany"],
            "currency": ["USD", "EUR"],
            "listing_currency": ["USD", "EUR"],
            "exchange": ["NYQ", "GER"],
            "sector": ["Technology", "Industrials"],
            "industry": ["Software", "Machinery"],
        }
    )

    exposure = build_exposure_analysis(weights, universe, final_model="HRP")

    for key in [
        "listing_country",
        "issuer_country",
        "economic_country",
        "currency",
        "exchange",
        "sector",
        "industry",
        "sleeve",
    ]:
        assert round(float(exposure[key]["weight"].sum()), 12) == 1.0
