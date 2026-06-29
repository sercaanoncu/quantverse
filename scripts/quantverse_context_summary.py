"""Print a lightweight QuantVerse context summary."""

from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    print(f"branch: {_git(['branch', '--show-current'])}")
    print(f"latest_commit: {_git(['log', '--oneline', '-1'])}")
    print(f"expected_pytest: {_expected_pytest_count()}")
    print(f"codex_context_pack: {_exists('.codex/CONTEXT.md')}")
    print(f"source_candidate_csvs: {_source_candidate_count()}")
    print(
        f"current_global_equity_universe: {_exists('data/universe/current_global_equity_universe.csv')}"
    )
    print(
        f"global_returns_matrix: {_exists('data/processed/global_security_returns.csv')}"
    )
    print(f"untracked_generated_outputs: {_untracked_processed_count()}")
    return 0


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _expected_pytest_count() -> str:
    for path in [Path("README.md"), Path("docs/testing_strategy.md")]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if " passed" in line and line.strip().split()[0].isdigit():
                return line.strip()
    return "unknown"


def _exists(path: str) -> str:
    return "yes" if Path(path).exists() else "no"


def _source_candidate_count() -> int:
    source_dir = Path("data/universe/sources")
    return len(list(source_dir.glob("*_candidates.csv"))) if source_dir.exists() else 0


def _untracked_processed_count() -> int:
    result = subprocess.run(
        ["git", "status", "--short", "--", "data/processed"],
        check=False,
        capture_output=True,
        text=True,
    )
    return len([line for line in result.stdout.splitlines() if line.startswith("??")])


if __name__ == "__main__":
    raise SystemExit(main())
