from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_TO_SCAN = [
    ROOT / "README.md",
    ROOT / "docs" / "product" / "QUANTVERSE_V2_PRODUCT_CONTRACT.md",
    ROOT / "docs" / "audit" / "QUANTVERSE_V2_CORE_ENGINE_REALITY_CHECK.md",
    ROOT / "docs" / "showcase" / "README_GITHUB_SHOWCASE.md",
    ROOT / "docs" / "showcase" / "LINKEDIN_PROJECT_POST.md",
    ROOT / "docs" / "showcase" / "BANK_INTERVIEW_TALK_TRACK.md",
]


def test_public_docs_do_not_use_unsupported_marketing_claims():
    forbidden = [
        "guarantees future",
        "guaranteed alpha",
        "guaranteed outperformance",
        "is a live trading system",
        "official exact top-100 supported",
        "promoted global usd master portfolio",
    ]
    for path in DOCS_TO_SCAN:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"{path} contains unsupported phrase: {phrase}"


def test_readme_and_product_contract_include_claim_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    contract = (
        (ROOT / "docs" / "product" / "QUANTVERSE_V2_PRODUCT_CONTRACT.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "not investment advice" in readme
    assert "not investment advice" in contract
    assert "public-data" in readme
    assert "point-in-time" in readme
    assert "actual_status" in contract
