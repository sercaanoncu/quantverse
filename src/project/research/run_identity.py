"""Shared run identity and cross-artifact registry for QuantVerse v2."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

RUN_MANIFEST_NAME = "quantverse_v2_run_manifest.json"
RUN_REGISTRY_NAME = "quantverse_v2_artifact_run_registry.csv"
RUN_FIELDS = [
    "run_id",
    "execution_id",
    "data_as_of_date",
    "generated_at",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
]


def build_run_manifest(
    universe: pd.DataFrame,
    *,
    data_as_of_date: str,
    generated_at: str | None = None,
    data_snapshot: pd.DataFrame | pd.Series | None = None,
    config: Mapping[str, object] | None = None,
) -> dict[str, str]:
    """Create execution and stable-input identities for one evidence build."""
    generated = generated_at or datetime.now(timezone.utc).isoformat()
    universe_id = universe_snapshot_id(universe)
    data_id = data_snapshot_id(data_snapshot)
    config_id = config_snapshot_hash(config)
    input_seed = f"{universe_id}|{data_as_of_date}|{data_id}|{config_id}".encode(
        "utf-8"
    )
    input_fingerprint = f"input-{hashlib.sha256(input_seed).hexdigest()[:20]}"
    execution_seed = f"{input_fingerprint}|{generated}".encode("utf-8")
    execution_id = (
        f"qv2-{data_as_of_date}-{hashlib.sha256(execution_seed).hexdigest()[:16]}"
    )
    return {
        "run_id": execution_id,
        "execution_id": execution_id,
        "data_as_of_date": str(data_as_of_date),
        "generated_at": generated,
        "universe_snapshot_id": universe_id,
        "data_snapshot_id": data_id,
        "config_hash": config_id,
        "input_fingerprint": input_fingerprint,
    }


def universe_snapshot_id(universe: pd.DataFrame) -> str:
    """Return a stable digest for the current universe rows."""
    if universe.empty:
        return "universe-empty"
    columns = [
        column
        for column in [
            "ticker",
            "name",
            "sleeve",
            "exchange",
            "currency",
            "asset_type",
            "investable",
            "benchmark_only",
            "signal_only",
            "include",
            "as_of_date",
            "source_method",
        ]
        if column in universe
    ]
    if not columns:
        payload = str(len(universe)).encode("utf-8")
        return f"universe-{hashlib.sha256(payload).hexdigest()[:16]}"
    normalized = universe[columns].fillna("").astype(str).sort_values(columns)
    payload = normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return f"universe-{hashlib.sha256(payload).hexdigest()[:16]}"


def data_snapshot_id(data: pd.DataFrame | pd.Series | None) -> str:
    """Return a stable digest of the dated numerical evidence matrix."""
    if data is None:
        return "data-unavailable"
    frame = data.to_frame() if isinstance(data, pd.Series) else data.copy()
    if frame.empty:
        return "data-empty"
    frame.columns = frame.columns.map(str)
    frame = frame.reindex(sorted(frame.columns), axis=1).sort_index()
    frame.index = frame.index.map(str)
    payload = frame.to_csv(
        index=True,
        lineterminator="\n",
        na_rep="<NA>",
        float_format="%.17g",
    ).encode("utf-8")
    return f"data-{hashlib.sha256(payload).hexdigest()[:20]}"


def config_snapshot_hash(config: Mapping[str, object] | None) -> str:
    """Return a stable digest of the parsed configuration used by a run."""
    if config is None:
        return "config-unavailable"
    payload = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return f"config-{hashlib.sha256(payload).hexdigest()[:20]}"


def write_run_manifest(
    output_dir: str | Path,
    manifest: dict[str, str],
    *,
    reset_registry: bool = True,
) -> Path:
    """Write the run manifest and optionally reset the artifact registry."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / RUN_MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if reset_registry:
        registry = output / RUN_REGISTRY_NAME
        if registry.exists():
            registry.unlink()
    return path


def read_run_manifest(output_dir: str | Path) -> dict[str, str]:
    """Read the current run manifest."""
    path = Path(output_dir) / RUN_MANIFEST_NAME
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {field: str(payload.get(field, "unavailable")) for field in RUN_FIELDS}


def register_artifacts(
    output_dir: str | Path,
    artifact_paths: Iterable[str | Path],
    manifest: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Register generated artifacts against the active run identity."""
    output = Path(output_dir)
    metadata = manifest or read_run_manifest(output)
    if not metadata or not metadata.get("run_id"):
        raise ValueError("QuantVerse v2 run manifest is missing.")
    registry_path = output / RUN_REGISTRY_NAME
    existing = (
        pd.read_csv(registry_path)
        if registry_path.exists()
        else pd.DataFrame(
            columns=[
                "artifact",
                *RUN_FIELDS,
                "file_size",
                "sha256",
            ]
        )
    )
    rows = []
    for raw_path in artifact_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            continue
        try:
            artifact = path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            artifact = str(path)
        rows.append(
            {
                "artifact": artifact,
                **{field: metadata.get(field, "unavailable") for field in RUN_FIELDS},
                "file_size": int(path.stat().st_size),
                "sha256": _file_hash(path),
            }
        )
    updates = pd.DataFrame(rows)
    if updates.empty:
        return existing
    combined = pd.concat([existing, updates], ignore_index=True)
    combined = combined.drop_duplicates("artifact", keep="last").sort_values("artifact")
    combined.to_csv(registry_path, index=False)
    return combined


def registry_run_ids(
    output_dir: str | Path,
    artifacts: Iterable[str],
) -> dict[str, str]:
    """Return registered run IDs for requested artifact paths."""
    path = Path(output_dir) / RUN_REGISTRY_NAME
    if not path.exists():
        return {}
    frame = pd.read_csv(path, dtype=str).fillna("")
    wanted = set(artifacts)
    subset = frame.loc[frame["artifact"].astype(str).isin(wanted)]
    return dict(zip(subset["artifact"], subset["run_id"], strict=False))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
