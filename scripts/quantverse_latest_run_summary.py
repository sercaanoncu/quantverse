"""Print a fast summary of the latest local QuantVerse outputs.

This utility reads already-generated files under data/processed. It does not
download market data, call external APIs, plot figures, or run the pipeline.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

PROCESSED = Path("data/processed")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        print(f"WARN: Missing optional file: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        print(f"WARN: Missing optional file: {path}")
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _fmt_percent(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "n/a"


def _first(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str] | None:
    return next((row for row in rows if row.get(key) == value), None)


def main() -> int:
    root = Path.cwd()
    if not (root / "pyproject.toml").exists() or not (root / "src").exists():
        print("FAIL: Run this script from the QuantVerse repository root.")
        return 1

    run_metadata = _load_json(PROCESSED / "run_metadata.json")
    champion = _load_json(PROCESSED / "champion_selection_summary.json")
    league = _load_csv(PROCESSED / "model_league_summary.csv")
    promotion = _load_csv(PROCESSED / "model_promotion_gate.csv")
    challengers = _load_csv(PROCESSED / "challenger_backtest_summary.csv")
    diagnostic = _load_csv(PROCESSED / "equal_weight_diagnostic.csv")

    print("QuantVerse Latest Run Summary")
    print("=" * 32)
    print("Project status: local research output summary")

    if run_metadata:
        print(f"Config: {run_metadata.get('config_path', 'n/a')}")
        date_range = run_metadata.get("date_range") or ["n/a", "n/a"]
        print(f"Data period: {date_range[0]} to {date_range[-1]}")
        print(f"Data as of: {run_metadata.get('data_as_of', 'n/a')}")
        print(
            f"Investable assets: {run_metadata.get('returns_shape', ['n/a', 'n/a'])[1]}"
        )

    if league:
        broad = _first(league, "League", "Broad Default Champion")
        defensive = _first(league, "League", "Defensive / Drawdown Champion")
        if broad:
            print(f"Broad champion: {broad.get('Strategy', 'n/a')}")
        if defensive:
            print(f"Defensive candidate: {defensive.get('Strategy', 'n/a')}")

    if champion:
        print(f"Highest CAGR model: {champion.get('best_cagr_model', 'n/a')}")
        print(f"Highest CAGR: {_fmt_percent(champion.get('best_cagr'))}")
        print(f"Equal Weight CAGR: {_fmt_percent(champion.get('equal_weight_cagr'))}")
        print(
            "Replace Equal Weight broad champion: "
            f"{champion.get('replace_equal_weight_champion', 'n/a')}"
        )

    asset_row = _first(promotion, "Strategy", "Asset-Class Momentum Rotation")
    if asset_row:
        print(
            "Asset-Class Momentum status: "
            f"{asset_row.get('Promotion_Decision', 'n/a')}"
        )

    if challengers:
        print(f"Challenger rows: {len(challengers)}")
    if diagnostic:
        print(f"Equal Weight diagnostic rows: {len(diagnostic)}")

    print(
        "Caution: QuantVerse is research decision support, not investment advice "
        "or a live trading system."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
