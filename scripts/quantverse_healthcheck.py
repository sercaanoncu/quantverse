"""Fast local readiness check for the QuantVerse repository.

This script intentionally does not download market data, run pytest, or execute
the full pipeline. It is a quick product-level sanity check for local setup.
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path

CRITICAL_PATHS = [
    "configs/base.yaml",
    "scripts/run_full_pipeline.py",
    "src",
    "tests",
    "README.md",
]

KEY_DOCS = [
    "docs/research/model_league_system.md",
    "docs/research/asset_class_momentum_forensic_audit.md",
    "docs/audit/EVIDENCE_MATRIX.md",
]

KEY_OUTPUTS = [
    "data/processed/model_league_summary.csv",
    "data/processed/model_promotion_gate.csv",
    "data/processed/champion_selection_summary.json",
]

TRACKED_JUNK_PATTERNS = [
    "Lib/*",
    "Scripts/*",
    "etc/*",
    "share/*",
    ".venv/*",
    "venv/*",
    "env/*",
    "data/cache/*",
    "data/raw/*",
    "data/processed/*.parquet",
    "data/processed/*.pkl",
    "data/processed/*.pickle",
    "output/*",
    "reports/*",
    ".pytest_cache/*",
    "__pycache__/*",
    ".ipynb_checkpoints/*",
    "src/*.egg-info/*",
    "*.pdf",
]


def _status(label: str, message: str) -> None:
    print(f"{label}: {message}")


def _path_exists(root: Path, relative_path: str) -> bool:
    return (root / relative_path).exists()


def _tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        _status("WARN", f"Could not inspect tracked files with git: {exc}")
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines()]


def _matches_junk(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        fnmatch.fnmatchcase(normalized, pattern) for pattern in TRACKED_JUNK_PATTERNS
    )


def main() -> int:
    root = Path.cwd()
    critical_missing = False

    if _path_exists(root, "pyproject.toml") and _path_exists(root, "src/project"):
        _status("PASS", "Current directory looks like a QuantVerse repository")
    else:
        _status(
            "WARN",
            "Current directory does not clearly look like the QuantVerse repo root",
        )

    for relative_path in CRITICAL_PATHS:
        if _path_exists(root, relative_path):
            _status("PASS", f"Critical path exists: {relative_path}")
        else:
            _status("FAIL", f"Missing critical path: {relative_path}")
            critical_missing = True

    for relative_path in KEY_DOCS:
        if _path_exists(root, relative_path):
            _status("PASS", f"Key documentation exists: {relative_path}")
        else:
            _status("WARN", f"Key documentation missing: {relative_path}")

    for relative_path in KEY_OUTPUTS:
        if _path_exists(root, relative_path):
            _status("PASS", f"Generated lightweight output exists: {relative_path}")
        else:
            _status("WARN", f"Output not generated yet: {relative_path}")

    junk = [path for path in _tracked_files(root) if _matches_junk(path)]
    if junk:
        _status("WARN", "Tracked generated/junk patterns found:")
        for path in junk[:20]:
            _status("WARN", f"  {path}")
        if len(junk) > 20:
            _status("WARN", f"  ... {len(junk) - 20} more")
    else:
        _status("PASS", "No obvious tracked junk/heavy artifact patterns found")

    if critical_missing:
        _status("FAIL", "Repository is missing critical source/config files")
        return 1

    _status("PASS", "Healthcheck completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
