"""Run lightweight scientific sanity checks for global quant outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory containing generated global quant outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    issues = _collect_issues(output_dir)
    summary = _summary(issues)
    issues.to_csv(output_dir / "global_scientific_sanity_issues.csv", index=False)
    summary.to_csv(output_dir / "global_scientific_sanity_summary.csv", index=False)
    blocker_count = (
        int(issues["promotion_blocker"].fillna(False).astype(bool).sum())
        if not issues.empty and "promotion_blocker" in issues
        else 0
    )
    print(
        f"Scientific sanity issues: {len(issues)}; promotion blockers: {blocker_count}"
    )
    return 0


def _collect_issues(output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    classification_path = output_dir / "global_exact_proxy_classification_report.csv"
    blockers_path = output_dir / "global_market_cap_rank_blockers.csv"
    bl_path = output_dir / "global_black_litterman_prerequisite_report.csv"
    decision_path = output_dir / "global_master_decision_summary.json"

    if not classification_path.exists():
        rows.append(
            _issue(
                "market_cap_rank",
                "missing_exact_proxy_classification_report",
                str(classification_path),
                "",
                "Exact/proxy sleeve status is not auditable.",
                True,
                "Run scripts/validate_real_global_universe.py.",
            )
        )
    else:
        classification = pd.read_csv(classification_path)
        unsupported = classification.loc[
            ~classification["classification"]
            .astype(str)
            .eq("exact_market_cap_rank_supported")
        ]
        for _, row in unsupported.iterrows():
            rows.append(
                _issue(
                    "exact_proxy",
                    "unsupported_exact_top100_claim",
                    str(classification_path),
                    "classification",
                    str(row.get("reason", "Exact status is unsupported.")),
                    True,
                    str(
                        row.get(
                            "turkish_explanation",
                            "Keep sleeve as proxy/manual until evidence is complete.",
                        )
                    ),
                    sleeve=row.get("sleeve", ""),
                )
            )

    if blockers_path.exists():
        blockers = pd.read_csv(blockers_path)
        for _, row in blockers.iterrows():
            rows.append(
                _issue(
                    "market_cap_rank",
                    str(row.get("issue", "market_cap_rank_blocker")),
                    str(blockers_path),
                    str(row.get("column", "")),
                    str(row.get("what_wrong", "")),
                    _to_bool(row.get("promotion_blocker", True)),
                    str(row.get("next_fix", "")),
                    ticker=row.get("ticker", ""),
                    sleeve=row.get("sleeve", ""),
                )
            )

    if bl_path.exists():
        bl = pd.read_csv(bl_path)
        invalid = bl.loc[~bl["black_litterman_prior_valid"].fillna(False).astype(bool)]
        if not invalid.empty:
            rows.append(
                _issue(
                    "black_litterman",
                    "black_litterman_priors_blocked",
                    str(bl_path),
                    "black_litterman_prior_valid",
                    "Black-Litterman cannot run as allocation evidence without valid market-cap priors for every required asset.",
                    True,
                    "Provide valid sourced market-cap/rank evidence or keep Black-Litterman blocked by data.",
                )
            )

    if decision_path.exists():
        try:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            decision = {}
        if str(decision.get("promotion_decision", "")).lower() == "promoted":
            if rows:
                rows.append(
                    _issue(
                        "promotion_gate",
                        "promotion_with_open_scientific_blockers",
                        str(decision_path),
                        "promotion_decision",
                        "A promoted decision exists while scientific blockers remain.",
                        True,
                        "Downgrade to not promoted until evidence gates pass.",
                    )
                )

    return pd.DataFrame(rows, columns=_issue_columns())


def _summary(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(
            [
                {
                    "check_group": "global_scientific_sanity",
                    "issues": 0,
                    "promotion_blockers": 0,
                    "status": "passed",
                }
            ]
        )
    return (
        issues.groupby("category", dropna=False)
        .agg(
            issues=("issue", "count"),
            promotion_blockers=(
                "promotion_blocker",
                lambda s: int(s.astype(bool).sum()),
            ),
        )
        .reset_index()
        .rename(columns={"category": "check_group"})
        .assign(status="issues_found")
    )


def _issue(
    category: str,
    issue: str,
    evidence_file: str,
    evidence_column: str,
    what_wrong: str,
    promotion_blocker: bool,
    next_fix: str,
    *,
    ticker: object = "",
    sleeve: object = "",
) -> dict[str, object]:
    return {
        "category": category,
        "ticker": ticker,
        "sleeve": sleeve,
        "issue": issue,
        "evidence_file": evidence_file,
        "evidence_column": evidence_column,
        "what_wrong": what_wrong,
        "why_important": "Unsupported exact/proxy, source, rank, or market-cap claims can make portfolio evidence non-auditable.",
        "promotion_blocker": bool(promotion_blocker),
        "next_fix": next_fix,
    }


def _issue_columns() -> list[str]:
    return [
        "category",
        "ticker",
        "sleeve",
        "issue",
        "evidence_file",
        "evidence_column",
        "what_wrong",
        "why_important",
        "promotion_blocker",
        "next_fix",
    ]


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    sys.exit(main())
