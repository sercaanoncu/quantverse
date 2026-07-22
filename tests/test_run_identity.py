import pandas as pd

from project.research.run_identity import (
    build_run_manifest,
    config_snapshot_hash,
    data_snapshot_id,
    universe_snapshot_id,
)


def test_run_identity_separates_execution_from_stable_inputs():
    universe = pd.DataFrame(
        {
            "ticker": ["BBB", "AAA"],
            "sleeve": ["equity", "equity"],
            "include": [True, True],
        }
    )
    returns = pd.DataFrame(
        {"BBB": [0.02, -0.01], "AAA": [0.01, 0.03]},
        index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
    )
    config = {"base_currency": "USD", "selection": {"max_holdings": 25}}

    first = build_run_manifest(
        universe,
        data_as_of_date="2026-01-05",
        generated_at="2026-01-06T00:00:00+00:00",
        data_snapshot=returns,
        config=config,
    )
    second = build_run_manifest(
        universe.iloc[::-1],
        data_as_of_date="2026-01-05",
        generated_at="2026-01-06T00:01:00+00:00",
        data_snapshot=returns[["AAA", "BBB"]],
        config=config,
    )

    assert first["run_id"] != second["run_id"]
    assert first["execution_id"] == first["run_id"]
    assert second["execution_id"] == second["run_id"]
    assert first["universe_snapshot_id"] == second["universe_snapshot_id"]
    assert first["data_snapshot_id"] == second["data_snapshot_id"]
    assert first["config_hash"] == second["config_hash"]
    assert first["input_fingerprint"] == second["input_fingerprint"]


def test_input_hashes_change_when_evidence_or_configuration_changes():
    returns = pd.DataFrame({"AAA": [0.01, 0.02]})
    changed = pd.DataFrame({"AAA": [0.01, 0.021]})

    assert data_snapshot_id(returns) != data_snapshot_id(changed)
    assert config_snapshot_hash({"max_holdings": 25}) != config_snapshot_hash(
        {"max_holdings": 24}
    )


def test_universe_hash_changes_with_economically_material_metadata():
    universe = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "market_cap_usd": [1_000_000.0],
            "market_cap_rank": [1],
            "sector": ["Technology"],
            "industry": ["Software"],
            "economic_country": ["United States"],
            "data_provider": ["provider-a"],
        }
    )

    changed_cap = universe.assign(market_cap_usd=2_000_000.0)
    changed_rank = universe.assign(market_cap_rank=2)

    assert universe_snapshot_id(universe) != universe_snapshot_id(changed_cap)
    assert universe_snapshot_id(universe) != universe_snapshot_id(changed_rank)


def test_composite_config_hash_covers_downstream_analytic_settings():
    universe = pd.DataFrame({"ticker": ["A"], "include": [True]})
    returns = pd.DataFrame({"A": [0.01]}, index=["2026-01-02"])
    base_components = {
        "returns_matrix": {"base_currency": "USD"},
        "analysis": {"transaction_cost_bps": 10.0, "walk_forward_train_days": 252},
        "master_portfolio": {"max_weight": 0.10, "min_holdings": 10},
        "source_universe": {"require_source_url": True},
        "current_universe": {"deduplicate_on": "ticker"},
    }

    first = build_run_manifest(
        universe,
        data_as_of_date="2026-01-02",
        generated_at="2026-01-03T00:00:00+00:00",
        data_snapshot=returns,
        config_components=base_components,
    )
    changed = build_run_manifest(
        universe,
        data_as_of_date="2026-01-02",
        generated_at="2026-01-03T00:00:00+00:00",
        data_snapshot=returns,
        config_components={
            **base_components,
            "master_portfolio": {
                "max_weight": 0.08,
                "min_holdings": 10,
            },
        },
    )

    assert first["config_scope"] == (
        "composite:analysis,current_universe,master_portfolio,"
        "returns_matrix,source_universe"
    )
    assert first["config_hash"] != changed["config_hash"]
    assert first["input_fingerprint"] != changed["input_fingerprint"]
    assert first["run_id"] != changed["run_id"]
