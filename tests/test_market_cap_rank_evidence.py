import json
import subprocess
import sys

import pandas as pd

from project.data_pipeline.market_cap_rank_evidence import (
    EVIDENCE_STATUS_VALUES,
    black_litterman_priors_available,
    validate_market_cap_rank_evidence,
    write_market_cap_rank_outputs,
)


def _row(**overrides):
    base = {
        "ticker": "AAA",
        "name": "Alpha",
        "sleeve": "global_equity_nasdaq",
        "region": "North America",
        "country": "United States",
        "exchange": "NASDAQ",
        "currency": "USD",
        "asset_type": "equity",
        "market_cap_usd": 1000.0,
        "market_cap_rank": 1,
        "rank_universe": "NASDAQ sourced candidates",
        "rank_method": "source_rank",
        "source_name": "Unit Source",
        "source_url": "https://example.com/source",
        "source_provider": "unit",
        "as_of_date": "2026-01-31",
        "retrieved_at": "2026-02-01",
        "source_method": "exact_market_cap_rank",
        "exact_proxy_status": "exact_market_cap_rank",
        "notes": "unit",
    }
    base.update(overrides)
    return base


def _validate(rows):
    return validate_market_cap_rank_evidence(pd.DataFrame(rows), today="2026-02-01")


def test_exact_market_cap_rank_is_accepted_only_with_required_fields():
    report, classification, blockers, bl_report = _validate([_row()])

    assert report["evidence_status"].tolist() == ["exact_market_cap_rank"]
    assert classification["classification"].tolist() == [
        "exact_market_cap_rank_supported"
    ]
    assert blockers.empty
    assert bl_report["black_litterman_prior_valid"].tolist() == [True]
    assert set(report["evidence_status"]).issubset(EVIDENCE_STATUS_VALUES)


def test_missing_source_url_provider_date_market_cap_or_rank_blocks_exact():
    rows = [
        _row(ticker="NO_URL", source_url="", market_cap_rank=1),
        _row(ticker="NO_PROVIDER", source_provider="", market_cap_rank=2),
        _row(ticker="NO_DATE", as_of_date="", market_cap_rank=3),
        _row(ticker="NO_CAP", market_cap_usd="", market_cap_rank=4),
        _row(ticker="NO_RANK", market_cap_rank=""),
    ]

    report, classification, blockers, bl_report = _validate(rows)

    assert "exact_market_cap_rank_supported" not in set(
        classification["classification"]
    )
    assert set(report["evidence_status"]) == {
        "invalid_source",
        "missing_market_cap_rank",
    }
    assert set(blockers["ticker"]) == {
        "NO_URL",
        "NO_PROVIDER",
        "NO_DATE",
        "NO_CAP",
        "NO_RANK",
    }
    assert not bl_report["black_litterman_prior_valid"].any()


def test_duplicate_ranks_are_flagged_within_sleeve_asof_and_rank_universe():
    rows = [_row(ticker="AAA"), _row(ticker="BBB", market_cap_usd=900.0)]

    report, _, blockers, _ = _validate(rows)

    assert set(report["evidence_status"]) == {"duplicate_rank"}
    assert "duplicate_rank" in set(blockers["issue"])


def test_index_proxy_cannot_be_upgraded_to_exact():
    row = _row(
        source_method="index_proxy",
        exact_proxy_status="exact_market_cap_rank",
        notes="Nasdaq-100 index proxy constituent",
    )

    report, classification, blockers, _ = _validate([row])

    assert report["evidence_status"].iloc[0] == "index_proxy"
    assert classification["classification"].iloc[0] == "index_proxy_only"
    assert "index_proxy" in set(blockers["issue"])


def test_manual_review_rows_remain_proxy_research_only():
    row = _row(
        source_method="manual_review_required",
        exact_proxy_status="manual_review_required",
        notes="manual_review_required",
    )

    report, classification, blockers, _ = _validate([row])

    assert report["evidence_status"].iloc[0] == "manual_review_required"
    assert classification["classification"].iloc[0] == "manual_review_required"
    assert "manual_review_required" in set(blockers["issue"])


def test_black_litterman_prerequisite_requires_valid_market_cap_priors():
    valid = pd.DataFrame([_row(ticker="AAA"), _row(ticker="BBB", market_cap_rank=2)])
    invalid = pd.DataFrame([_row(ticker="AAA"), _row(ticker="BBB", source_url="")])

    assert black_litterman_priors_available(valid, ["AAA", "BBB"])
    assert not black_litterman_priors_available(invalid, ["AAA", "BBB"])


def test_validator_writes_required_generated_outputs(tmp_path):
    outputs = write_market_cap_rank_outputs(pd.DataFrame([_row()]), tmp_path)

    assert (tmp_path / "global_market_cap_rank_evidence_report.csv").exists()
    assert (tmp_path / "global_exact_proxy_classification_report.csv").exists()
    assert (tmp_path / "global_market_cap_rank_blockers.csv").exists()
    assert (tmp_path / "global_black_litterman_prerequisite_report.csv").exists()
    assert outputs["classification_report"]["classification"].iloc[0] == (
        "exact_market_cap_rank_supported"
    )


def test_scientific_audit_flags_unsupported_exact_claims(tmp_path):
    write_market_cap_rank_outputs(
        pd.DataFrame(
            [
                _row(
                    market_cap_usd="",
                    market_cap_rank="",
                    source_method="index_proxy",
                    exact_proxy_status="index_proxy",
                )
            ]
        ),
        tmp_path,
    )
    (tmp_path / "global_master_decision_summary.json").write_text(
        json.dumps({"promotion_decision": "not promoted"}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_global_scientific_sanity.py",
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    issues = pd.read_csv(tmp_path / "global_scientific_sanity_issues.csv")

    assert result.returncode == 0
    assert "unsupported_exact_top100_claim" in set(issues["issue"])
    assert issues["promotion_blocker"].astype(bool).any()
