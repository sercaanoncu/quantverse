"""Staged publication helpers for user-facing QuantVerse artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Mapping

PUBLICATION_RUN_IDENTITY_FIELDS = (
    "run_id",
    "execution_id",
    "data_as_of_date",
    "generated_at",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
)


@contextmanager
def staged_publication(root: str | Path, label: str) -> Iterator[Path]:
    """Yield a clean staging directory and remove it after use."""
    root_path = Path(root)
    staging_root = root_path / "output" / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    stage = staging_root / f"{label}-{uuid.uuid4().hex}"
    stage.mkdir(parents=True)
    try:
        yield stage
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def publish_staged_files(
    staged_to_final: Mapping[str | Path, str | Path],
    *,
    root: str | Path,
    manifest_path: str | Path,
    run_identity: Mapping[str, object],
    publication_type: str,
) -> dict[str, object]:
    """Publish a complete artifact set and write its manifest last.

    Existing targets are retained as temporary backups until every replacement
    and the completion manifest have succeeded. A handled publication failure
    therefore restores the prior coherent package instead of leaving a mixture
    of old and new artifacts.
    """
    root_path = Path(root).resolve()
    pairs = [(Path(source), Path(target)) for source, target in staged_to_final.items()]
    if not pairs:
        raise ValueError("At least one staged artifact is required.")
    targets = [target.resolve() for _, target in pairs]
    if len(targets) != len(set(targets)):
        raise ValueError("Publication targets must be unique.")
    missing = [str(source) for source, _ in pairs if not source.is_file()]
    if missing:
        raise FileNotFoundError(
            "Staged publication is incomplete: " + ", ".join(missing)
        )
    publication_label = str(publication_type).strip()
    if not publication_label:
        raise ValueError("Publication type must be non-empty.")
    missing_identity = [
        field
        for field in PUBLICATION_RUN_IDENTITY_FIELDS
        if not str(run_identity.get(field, "")).strip()
    ]
    if missing_identity:
        raise ValueError(
            "Publication run identity is incomplete: " + ", ".join(missing_identity)
        )
    relative_targets: list[Path] = []
    for target in targets:
        try:
            relative_targets.append(target.relative_to(root_path))
        except ValueError as exc:
            raise ValueError(
                f"Publication target must remain under root: {target.name}"
            ) from exc

    publication_id = uuid.uuid4().hex
    artifact_rows = [
        {
            "artifact": target.as_posix(),
            "size_bytes": int(source.stat().st_size),
            "sha256": _sha256(source),
        }
        for (source, _), target in zip(pairs, relative_targets, strict=True)
    ]

    manifest = {
        "publication_status": "complete",
        "publication_id": publication_id,
        "publication_type": publication_label,
        "published_at": datetime.now(timezone.utc).isoformat(),
        **{key: str(value) for key, value in run_identity.items()},
        "artifacts": artifact_rows,
    }
    destination = Path(manifest_path)
    if not destination.is_absolute():
        destination = root_path / destination
    destination = destination.resolve()
    try:
        destination.relative_to(root_path)
    except ValueError as exc:
        raise ValueError("Publication manifest must remain under root.") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = destination.with_suffix(destination.suffix + ".tmp")
    manifest_backup = destination.with_name(f".{destination.name}.{publication_id}.bak")
    target_backups: dict[Path, Path | None] = {}

    try:
        if destination.exists():
            os.replace(destination, manifest_backup)
        for source, target in pairs:
            target.parent.mkdir(parents=True, exist_ok=True)
            backup = target.with_name(f".{target.name}.{publication_id}.bak")
            if target.exists():
                os.replace(target, backup)
                target_backups[target] = backup
            else:
                target_backups[target] = None
            os.replace(source, target)

        temporary_manifest.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_manifest, destination)
    except Exception:
        temporary_manifest.unlink(missing_ok=True)
        if destination.exists():
            destination.unlink()
        if manifest_backup.exists():
            os.replace(manifest_backup, destination)
        for target, backup in reversed(list(target_backups.items())):
            target.unlink(missing_ok=True)
            if backup is not None and backup.exists():
                os.replace(backup, target)
        raise

    manifest_backup.unlink(missing_ok=True)
    for backup in target_backups.values():
        if backup is not None:
            backup.unlink(missing_ok=True)
    return manifest


def validate_publication_manifest(
    root: str | Path,
    manifest_path: str | Path,
    *,
    expected_run_id: str,
    expected_publication_type: str | None = None,
    expected_artifacts: Iterable[str | Path] | None = None,
    expected_run_identity: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    """Verify an exact, one-run publication package and every declared file."""
    root_path = Path(root).resolve()
    path = Path(manifest_path)
    if not path.is_absolute():
        path = root_path / path
    path = path.resolve()
    try:
        path.relative_to(root_path)
    except ValueError:
        return [
            {
                "check": "publication_manifest_path_within_root",
                "passed": False,
                "details": "manifest path resolves outside publication root",
            }
        ]
    if not path.exists():
        return [
            {
                "check": "publication_manifest_present",
                "passed": False,
                "details": f"missing={path.name}",
            }
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            {
                "check": "publication_manifest_readable",
                "passed": False,
                "details": f"{type(exc).__name__}: invalid publication manifest",
            }
        ]
    if not isinstance(payload, dict):
        return [
            {
                "check": "publication_manifest_object",
                "passed": False,
                "details": "publication manifest must be a JSON object",
            }
        ]
    artifacts = payload.get("artifacts", [])
    artifact_rows = (
        [row for row in artifacts if isinstance(row, dict)]
        if isinstance(artifacts, list)
        else []
    )
    declared_names = [str(row.get("artifact", "")).strip() for row in artifact_rows]
    declared_normalized = [
        _normalized_relative_artifact(root_path, name) for name in declared_names
    ]
    expected_normalized = (
        {
            normalized
            for item in expected_artifacts
            if (normalized := _normalized_relative_artifact(root_path, item))
            is not None
        }
        if expected_artifacts is not None
        else None
    )
    expected_identity = {
        field: str(value)
        for field, value in dict(expected_run_identity or {}).items()
        if field in PUBLICATION_RUN_IDENTITY_FIELDS
    }
    expected_identity["run_id"] = str(expected_run_id)
    missing_identity = [
        field
        for field in PUBLICATION_RUN_IDENTITY_FIELDS
        if not str(payload.get(field, "")).strip()
    ]
    mismatched_identity = [
        field
        for field, value in expected_identity.items()
        if str(payload.get(field, "")) != value
    ]
    publication_type = str(payload.get("publication_type", "")).strip()
    type_matches = bool(
        publication_type
        and (
            expected_publication_type is None
            or publication_type == str(expected_publication_type)
        )
    )
    rows_well_formed = bool(
        isinstance(artifacts, list)
        and len(artifact_rows) == len(artifacts)
        and artifact_rows
    )
    unique_members = bool(
        rows_well_formed
        and all(name is not None for name in declared_normalized)
        and len(declared_normalized) == len(set(declared_normalized))
    )
    membership_exact = bool(
        expected_normalized is None
        or (
            unique_members
            and set(declared_normalized) == expected_normalized
            and len(expected_normalized) == len(declared_normalized)
        )
    )
    checks = [
        {
            "check": "publication_manifest_complete",
            "passed": payload.get("publication_status") == "complete",
            "details": f"status={payload.get('publication_status', 'missing')}",
        },
        {
            "check": "publication_manifest_run_id_matches",
            "passed": str(payload.get("run_id")) == str(expected_run_id),
            "details": (
                f"manifest={payload.get('run_id', 'missing')}; "
                f"expected={expected_run_id}"
            ),
        },
        {
            "check": "publication_manifest_has_artifacts",
            "passed": bool(isinstance(artifacts, list) and artifacts),
            "details": (f"artifact_count={len(artifact_rows)}"),
        },
        {
            "check": "publication_manifest_type_matches",
            "passed": type_matches,
            "details": (
                f"manifest={publication_type or 'missing'}; "
                f"expected={expected_publication_type or 'non-empty'}"
            ),
        },
        {
            "check": "publication_manifest_identity_complete_and_matches",
            "passed": not missing_identity and not mismatched_identity,
            "details": (
                f"missing={missing_identity}; mismatched={mismatched_identity}"
            ),
        },
        {
            "check": "publication_manifest_artifacts_unique",
            "passed": unique_members,
            "details": (
                f"declared={declared_normalized}; rows_well_formed={rows_well_formed}"
            ),
        },
        {
            "check": "publication_manifest_artifact_membership_exact",
            "passed": membership_exact,
            "details": (
                f"declared={sorted(name for name in declared_normalized if name)}; "
                f"expected={sorted(expected_normalized) if expected_normalized is not None else 'not supplied'}"
            ),
        },
    ]
    for row in artifact_rows:
        declared = Path(str(row.get("artifact", "")))
        path_is_relative = bool(str(declared).strip() and not declared.is_absolute())
        artifact = (root_path / declared).resolve() if path_is_relative else declared
        try:
            artifact.relative_to(root_path)
            path_within_root = path_is_relative
        except ValueError:
            path_within_root = False
        exists = bool(path_within_root and artifact.is_file())
        actual_hash = _sha256(artifact) if exists else "missing"
        actual_size = int(artifact.stat().st_size) if exists else -1
        declared_size_raw = row.get("size_bytes")
        declared_size = (
            int(declared_size_raw)
            if isinstance(declared_size_raw, int)
            and not isinstance(declared_size_raw, bool)
            and declared_size_raw >= 0
            else -2
        )
        checks.append(
            {
                "check": f"publication_path_{artifact.name or 'invalid'}",
                "passed": path_within_root,
                "details": (
                    f"declared_relative={path_is_relative}; "
                    f"within_root={path_within_root}"
                ),
            }
        )
        checks.append(
            {
                "check": f"publication_hash_{artifact.name}",
                "passed": bool(exists and actual_hash == str(row.get("sha256"))),
                "details": (
                    f"exists={exists}; expected_sha256={row.get('sha256')}; "
                    f"actual_sha256={actual_hash}"
                ),
            }
        )
        checks.append(
            {
                "check": f"publication_size_{artifact.name}",
                "passed": bool(exists and actual_size == declared_size),
                "details": (
                    f"exists={exists}; expected_size={declared_size}; "
                    f"actual_size={actual_size}"
                ),
            }
        )
    return checks


def _normalized_relative_artifact(
    root: Path,
    artifact: str | Path,
) -> str | None:
    declared = Path(str(artifact))
    if not str(declared).strip():
        return None
    resolved = (
        declared.resolve() if declared.is_absolute() else (root / declared).resolve()
    )
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
