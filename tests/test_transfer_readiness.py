import json
import re
from pathlib import Path


def test_transfer_manifest_lists_required_do_not_copy_entries():
    manifest = json.loads(
        Path("docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )

    required = {
        ".git/",
        "Lib/",
        "Scripts/",
        "etc/",
        "share/",
        ".venv/",
        "venv/",
        "env/",
        "data/cache/",
        "data/raw/",
        "data/processed/*.parquet",
        "data/processed/*.pkl",
        "data/processed/*.pickle",
        "output/",
        "reports/",
        ".pytest_cache/",
        "__pycache__/",
        ".ipynb_checkpoints/",
    }

    assert required.issubset(set(manifest["must_not_copy"]))
    assert manifest["git_policy"]["commit"] is False
    assert manifest["git_policy"]["push"] is False


def test_transfer_manifest_has_dry_run_and_post_transfer_validation_commands():
    manifest = json.loads(
        Path("docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )

    assert "-DryRun" in manifest["copy_commands"]["dry_run"]
    assert "python -m pytest -q" in manifest["post_transfer_validation_commands"]
    assert (
        "python scripts/run_full_pipeline.py --config configs/base.yaml"
        in manifest["post_transfer_validation_commands"]
    )


def test_migration_helper_is_local_only_and_avoids_git_commands():
    script = Path("tools/migration/copy_quality_sprint_to_clean_repo.ps1").read_text(
        encoding="utf-8"
    )

    assert "$SourceRoot" in script
    assert "$DestRoot" in script
    assert "$DryRun" in script
    assert "run_full_pipeline.py" in script
    assert not re.search(r"(?im)^\s*git\s+", script)


def test_lightweight_csv_json_outputs_do_not_expose_local_absolute_paths():
    files = list(Path("data/processed").glob("*.csv")) + list(
        Path("data/processed").glob("*.json")
    )
    slash = "\\"
    banned_patterns = [
        f"C:{slash}{'Users'}{slash}",
        f"{slash}{'One' + 'Drive'}{slash}",
        f"{slash}{'Desk' + 'top'}{slash}",
        f"{slash}{'Pro' + 'je'}{slash}",
        "/" + "Users" + "/",
    ]
    offenders = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern in text for pattern in banned_patterns):
            offenders.append(str(path))

    assert offenders == []
