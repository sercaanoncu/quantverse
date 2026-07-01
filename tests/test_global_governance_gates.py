import json

import pandas as pd

from scripts.audit_global_scientific_sanity import run_audit


def test_governance_docs_keep_current_universe_from_historical_overclaim():
    required = [
        "docs/audit/point_in_time_universe_framework.md",
        "docs/audit/delisting_corporate_action_audit_framework.md",
        "docs/audit/global_walk_forward_readiness.md",
    ]
    for path in required:
        text = open(path, encoding="utf-8").read().lower()
        assert "current" in text
        assert "promot" in text
        assert "not" in text or "no " in text


def test_audit_flags_missing_pit_delisting_and_walk_forward_evidence(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    universe = tmp_path / "current_global_equity_universe.csv"
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "sleeve": "global_equity_us",
                "notes": "current research input only",
            }
        ]
    ).to_csv(universe, index=False)
    (processed / "global_master_decision_summary.json").write_text(
        json.dumps({"promotion_decision": "not promoted"}),
        encoding="utf-8",
    )

    _, issues, _ = run_audit(processed, universe)
    issue_names = set(issues["issue"])

    assert "point_in_time_membership_evidence_missing" in issue_names
    assert "delisting_and_corporate_action_evidence_missing" in issue_names
    assert "global_walk_forward_evidence_missing" in issue_names
    assert issues["blocks_promotion"].astype(bool).any()


def test_sourced_equity_population_report_forbids_exact_top100_overclaim():
    text = open(
        "docs/audit/sourced_equity_population_report.md",
        encoding="utf-8",
    ).read()

    assert "not an official exchange" in text
    assert "Exact top-100 market-cap claim is not supported" in text
    assert "Yahoo Finance via yfinance" in text
