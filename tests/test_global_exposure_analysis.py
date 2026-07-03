import pandas as pd

from project.research.global_exposure_analysis import build_exposure_analysis


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
    assert "explanation" in exposure["top_holdings"]
    assert "sector" in exposure


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
