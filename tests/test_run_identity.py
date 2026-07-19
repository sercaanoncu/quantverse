import pandas as pd

from project.research.run_identity import (
    build_run_manifest,
    config_snapshot_hash,
    data_snapshot_id,
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
