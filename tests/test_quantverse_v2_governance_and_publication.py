import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts.build_quantverse_v2_excel_output import EXCEL_ENGINE_KWARGS
from project.reporting.artifact_publication import (
    publish_staged_files,
    staged_publication,
    validate_publication_manifest,
)
from project.reporting.quantverse_v2_publication import (
    _stress_plot_frame,
    load_publication_evidence,
)
from project.research.global_model_selection import build_final_model_decision
from project.research.run_identity import register_artifacts

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "audit" / "evidence" / "QUANTVERSE_V2_EXECUTION_LEDGER.jsonl"
DECISIONS = ROOT / "docs" / "audit" / "QUANTVERSE_V2_DECISION_REGISTER.md"
CHANGES = ROOT / "docs" / "audit" / "QUANTVERSE_V2_CHANGE_LEDGER.md"
FORMULAS = ROOT / "docs" / "methodology" / "QUANTVERSE_V2_FORMULA_THEORY_REGISTRY.md"
SELECTIONS = ROOT / "docs" / "audit" / "QUANTVERSE_V2_SELECTION_REJECTION_REGISTER.md"
ADVERSARIAL_AUDIT = (
    ROOT / "docs" / "audit" / "QUANTVERSE_V2_ADVERSARIAL_VALIDATOR_META_AUDIT.md"
)
PYRIGHT_CONFIG = ROOT / "pyrightconfig.json"


def _publication_identity(run_id: str = "run-1") -> dict[str, str]:
    return {
        "run_id": run_id,
        "execution_id": run_id,
        "data_as_of_date": "2026-07-17",
        "generated_at": "2026-07-19T00:00:00+00:00",
        "universe_snapshot_id": "universe-1",
        "data_snapshot_id": "data-1",
        "config_hash": "config-1",
        "input_fingerprint": "input-1",
    }


def test_execution_ledger_is_valid_jsonl_with_required_audit_fields():
    required = {
        "action_id",
        "timestamp",
        "phase",
        "operation_type",
        "summary",
        "files_read",
        "files_changed",
        "inputs",
        "outputs",
        "run_id",
        "execution_id",
        "git_commit",
        "reason",
        "expected_result",
        "observed_result",
        "status",
        "error_summary",
        "follow_up_action",
    }
    rows = [
        json.loads(line)
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert rows
    assert len({row["action_id"] for row in rows}) == len(rows)
    assert all(required.issubset(row) for row in rows)
    serialized = json.dumps(rows)
    assert "C:\\\\Users\\\\" not in serialized
    assert "password" not in serialized.lower()
    assert "api_key" not in serialized.lower()


def test_material_decisions_have_the_complete_governance_contract():
    text = DECISIONS.read_text(encoding="utf-8")
    required_fields = [
        "Problem",
        "Evidence",
        "Why it matters",
        "Affected system",
        "Previous method",
        "Candidate methods",
        "Alternative 1",
        "Why rejected",
        "Alternative 2",
        "Chosen method",
        "Why chosen",
        "Mathematical basis",
        "Statistical basis",
        "Financial/economic basis",
        "Book support",
        "Academic support",
        "Assumptions",
        "Parameters",
        "Sensitivity",
        "Expected impact",
        "Observed impact",
        "Validation",
        "Invalidation conditions",
        "Residual limitation",
        "Status",
    ]
    sections = [
        "## " + section
        for section in text.split("\n## ")
        if section.startswith("QV2-DEC-")
    ]

    assert len(sections) >= 5
    for section in sections:
        for field in required_fields:
            assert f"| {field} |" in section


def test_threshold_classifications_use_only_declared_governance_classes():
    allowed = {
        "THEORY_DERIVED",
        "LITERATURE_SUPPORTED",
        "EMPIRICALLY_CALIBRATED",
        "POLICY_ASSUMPTION",
        "UNSUPPORTED",
    }
    text = FORMULAS.read_text(encoding="utf-8")
    threshold_rows = [
        line
        for line in text.splitlines()
        if line.startswith("| ") and "Config (`" in line
    ]

    assert threshold_rows
    for row in threshold_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert cells[2] in allowed


def test_change_and_selection_ledgers_link_material_decisions():
    changes = CHANGES.read_text(encoding="utf-8")
    selections = SELECTIONS.read_text(encoding="utf-8")

    for decision_id in ["QV2-DEC-001", "QV2-DEC-002", "QV2-DEC-003", "QV2-DEC-004"]:
        assert decision_id in changes
    for item in [
        "Equal Weight",
        "HRP",
        "Ledoit-Wolf",
        "Static full-sample random portfolios",
        "Zero-fill selected missing returns",
    ]:
        assert item in selections


def test_adversarial_validator_audit_covers_all_required_attack_classes():
    text = ADVERSARIAL_AUDIT.read_text(encoding="utf-8")

    assert all(f"ADV-{index:03d}" in text for index in range(1, 27))
    assert text.count("| rejected |") == 26
    for phrase in [
        "Wrong non-native FX direction",
        "Static full-sample random",
        "Missing robustness",
        "Future winner",
        "Stale run",
        "Mismatched config hash",
        "risk-free",
        "Selected asset return",
        "optimizer weights",
        "CVaR sign",
        "overlap",
        "mixes current and stale",
    ]:
        assert phrase.lower() in text.lower()


def test_pyright_gate_covers_critical_financial_modules_without_broad_ignore():
    config = json.loads(PYRIGHT_CONFIG.read_text(encoding="utf-8"))
    required = {
        "src/project/research/global_model_selection.py",
        "src/project/research/global_walk_forward.py",
        "src/project/research/global_portfolio_league.py",
        "src/project/research/global_portfolio_risk.py",
        "src/project/research/global_numerical_integrity.py",
        "src/project/data_pipeline/security_identity.py",
        "src/project/data_pipeline/global_returns.py",
        "src/project/data_pipeline/processor.py",
        "src/project/portfolio_contract.py",
        "src/project/reporting/artifact_publication.py",
        "src/project/reporting/quantverse_v2_publication.py",
        "scripts/audit_quantverse_v2_missing_data_operations.py",
    }

    assert required.issubset(config["include"])
    assert config["typeCheckingMode"] == "basic"
    assert config["pythonVersion"] == "3.10"
    assert "ignore" not in config
    assert not any(key.startswith("report") for key in config)


def test_stress_chart_uses_final_model_scenarios_not_run_metadata():
    stress = pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight", "HRP"],
            "scenario": ["equity_selloff", "rate_shock", "equity_selloff"],
            "portfolio_loss_estimate": [-0.15, -0.01, -0.12],
            "config_hash": ["config-current"] * 3,
            "input_fingerprint": ["input-current"] * 3,
        }
    )
    evidence = SimpleNamespace(stress=stress, final_model="Equal Weight")

    plot = _stress_plot_frame(evidence)

    assert set(plot["Scenario"]) == {"equity_selloff", "rate_shock"}
    assert plot["Portfolio_Impact"].tolist() == [-0.15, -0.01]
    assert not plot["Scenario"].str.contains("config|input", regex=True).any()


def test_stress_chart_rejects_undeclared_column_fallback():
    evidence = SimpleNamespace(
        stress=pd.DataFrame(
            {"config_hash": ["config-current"], "input_fingerprint": ["input-current"]}
        ),
        final_model="Equal Weight",
    )

    with pytest.raises(ValueError, match="requires current"):
        _stress_plot_frame(evidence)


def test_staging_context_removes_partial_files_after_builder_failure(tmp_path):
    with pytest.raises(RuntimeError, match="synthetic builder failure"):
        with staged_publication(tmp_path, "report") as stage:
            (stage / "partial.pdf").write_bytes(b"partial")
            raise RuntimeError("synthetic builder failure")

    assert not list((tmp_path / "output" / ".staging").glob("report-*"))


def test_publication_rejects_incomplete_stage_without_touching_current_file(tmp_path):
    current = tmp_path / "output" / "report.pdf"
    current.parent.mkdir(parents=True)
    current.write_bytes(b"current")
    manifest = tmp_path / "output" / "report_manifest.json"

    with pytest.raises(FileNotFoundError, match="incomplete"):
        publish_staged_files(
            {tmp_path / "missing.pdf": current},
            root=tmp_path,
            manifest_path=manifest,
            run_identity={"run_id": "run-1"},
            publication_type="research_report",
        )

    assert current.read_bytes() == b"current"
    assert not manifest.exists()


def test_publication_rolls_back_all_targets_when_a_replacement_fails(
    tmp_path, monkeypatch
):
    first = tmp_path / "output" / "first.pdf"
    second = tmp_path / "output" / "second.html"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"old-first")
    second.write_text("old-second", encoding="utf-8")
    staged_first = tmp_path / "staged-first.pdf"
    staged_second = tmp_path / "staged-second.html"
    staged_first.write_bytes(b"new-first")
    staged_second.write_text("new-second", encoding="utf-8")
    manifest = tmp_path / "output" / "manifest.json"

    import project.reporting.artifact_publication as publication

    original_replace = publication.os.replace

    def fail_second_artifact(source, target):
        if Path(source) == staged_second and Path(target) == second:
            raise OSError("synthetic replacement failure")
        return original_replace(source, target)

    monkeypatch.setattr(publication.os, "replace", fail_second_artifact)

    with pytest.raises(OSError, match="synthetic replacement failure"):
        publish_staged_files(
            {staged_first: first, staged_second: second},
            root=tmp_path,
            manifest_path=manifest,
            run_identity=_publication_identity(),
            publication_type="research_report",
        )

    assert first.read_bytes() == b"old-first"
    assert second.read_text(encoding="utf-8") == "old-second"
    assert not manifest.exists()


def test_publication_rejects_incomplete_run_identity(tmp_path):
    staged = tmp_path / "staged.pdf"
    staged.write_bytes(b"new")
    final = tmp_path / "output" / "report.pdf"

    with pytest.raises(ValueError, match="run identity is incomplete"):
        publish_staged_files(
            {staged: final},
            root=tmp_path,
            manifest_path=tmp_path / "output" / "manifest.json",
            run_identity={"run_id": "run-1"},
            publication_type="research_report",
        )

    assert staged.exists()
    assert not final.exists()


def test_successful_publication_is_hash_bound_and_rejects_stale_run(tmp_path):
    staged = tmp_path / "staged.xlsx"
    staged.write_bytes(b"workbook")
    final = tmp_path / "output" / "research.xlsx"
    manifest = tmp_path / "output" / "excel_publication_manifest.json"

    payload = publish_staged_files(
        {staged: final},
        root=tmp_path,
        manifest_path=manifest,
        run_identity=_publication_identity(),
        publication_type="analytical_workbook",
    )
    valid = validate_publication_manifest(
        tmp_path,
        manifest,
        expected_run_id="run-1",
        expected_publication_type="analytical_workbook",
        expected_artifacts=["output/research.xlsx"],
        expected_run_identity=_publication_identity(),
    )
    stale = validate_publication_manifest(
        tmp_path,
        manifest,
        expected_run_id="run-2",
        expected_publication_type="analytical_workbook",
        expected_artifacts=["output/research.xlsx"],
        expected_run_identity=_publication_identity("run-2"),
    )

    assert payload["publication_status"] == "complete"
    assert payload["artifacts"][0]["artifact"] == "output/research.xlsx"
    assert final.read_bytes() == b"workbook"
    assert all(check["passed"] for check in valid)
    assert not next(
        check
        for check in stale
        if check["check"] == "publication_manifest_run_id_matches"
    )["passed"]

    copied_root = tmp_path.parent / f"{tmp_path.name}-copied"
    shutil.copytree(tmp_path / "output", copied_root / "output")
    copied_checks = validate_publication_manifest(
        copied_root,
        "output/excel_publication_manifest.json",
        expected_run_id="run-1",
        expected_publication_type="analytical_workbook",
        expected_artifacts=["output/research.xlsx"],
        expected_run_identity=_publication_identity(),
    )
    assert all(check["passed"] for check in copied_checks)


def test_publication_validator_rejects_inexact_or_mutated_package(tmp_path):
    staged_first = tmp_path / "staged.pdf"
    staged_second = tmp_path / "staged.html"
    staged_first.write_bytes(b"pdf")
    staged_second.write_text("html", encoding="utf-8")
    first = tmp_path / "output" / "report.pdf"
    second = tmp_path / "output" / "report.html"
    manifest = tmp_path / "output" / "manifest.json"
    identity = _publication_identity()

    publish_staged_files(
        {staged_first: first, staged_second: second},
        root=tmp_path,
        manifest_path=manifest,
        run_identity=identity,
        publication_type="research_report",
    )
    original = json.loads(manifest.read_text(encoding="utf-8"))

    cases = [
        (
            lambda payload: payload.update(publication_type="wrong_type"),
            "publication_manifest_type_matches",
        ),
        (
            lambda payload: payload.update(artifacts=payload["artifacts"][:1]),
            "publication_manifest_artifact_membership_exact",
        ),
        (
            lambda payload: payload.update(
                artifacts=[payload["artifacts"][0], payload["artifacts"][0]]
            ),
            "publication_manifest_artifacts_unique",
        ),
        (
            lambda payload: payload["artifacts"][0].update(size_bytes=999),
            "publication_size_report.pdf",
        ),
    ]
    for mutate, failed_check in cases:
        payload = json.loads(json.dumps(original))
        mutate(payload)
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        checks = validate_publication_manifest(
            tmp_path,
            manifest,
            expected_run_id="run-1",
            expected_publication_type="research_report",
            expected_artifacts=["output/report.pdf", "output/report.html"],
            expected_run_identity=identity,
        )
        assert not next(check for check in checks if check["check"] == failed_check)[
            "passed"
        ]


def test_publication_rejects_target_or_manifest_outside_root(tmp_path):
    staged = tmp_path / "staged.pdf"
    staged.write_bytes(b"new")
    outside = tmp_path.parent / "outside.pdf"

    with pytest.raises(ValueError, match="target must remain under root"):
        publish_staged_files(
            {staged: outside},
            root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            run_identity=_publication_identity(),
            publication_type="research_report",
        )


def test_publication_validator_rejects_absolute_and_traversal_artifact_paths(tmp_path):
    manifest = tmp_path / "output" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    outside = tmp_path.parent / "outside-publication.txt"
    outside.write_text("outside", encoding="utf-8")
    for declared in [str(outside.resolve()), "../outside-publication.txt"]:
        manifest.write_text(
            json.dumps(
                {
                    "publication_status": "complete",
                    "run_id": "run-1",
                    "artifacts": [
                        {
                            "artifact": declared,
                            "sha256": "not-used",
                            "size_bytes": 7,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        checks = validate_publication_manifest(
            tmp_path,
            manifest,
            expected_run_id="run-1",
        )

        assert not next(
            check for check in checks if check["check"].startswith("publication_path_")
        )["passed"]


def _write_publication_evidence(
    root: Path,
    *,
    mismatched_artifact: str | None = None,
    include_final_weights: bool = True,
) -> None:
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    manifest = {
        "run_id": "run-1",
        "execution_id": "run-1",
        "data_as_of_date": "2026-07-17",
        "generated_at": "2026-07-19T00:00:00+00:00",
        "universe_snapshot_id": "universe-1",
        "data_snapshot_id": "data-1",
        "config_hash": "config-1",
        "input_fingerprint": "input-1",
    }
    (processed / "quantverse_v2_run_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (processed / "global_final_model_decision.json").write_text(
        json.dumps(
            {
                **manifest,
                "final_selected_model": "Equal Weight",
                "final_decision": "not promoted",
                "final_decision_reason": "Synthetic test decision.",
            }
        ),
        encoding="utf-8",
    )
    (processed / "quantverse_v2_reference_math_summary.json").write_text(
        json.dumps(
            {
                **manifest,
                "status": "passed",
                "check_count": 40,
                "failed_check_count": 0,
                "checks_path": "data/processed/quantverse_v2_reference_math_checks.csv",
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_walk_forward_random_benchmark_provenance.json").write_text(
        json.dumps(
            {
                **manifest,
                "fold_count": 1,
                "transaction_cost_bps": 10.0,
                "max_weight": 1.0,
                "risk_free_policy": "zero",
                "random_weights_hash": "synthetic-random-weights-hash",
            }
        ),
        encoding="utf-8",
    )
    files = [
        "quantverse_v2_reference_math_checks.csv",
        "quantverse_v2_visual_validation.csv",
        "global_portfolio_league.csv",
        "global_model_selection_report.csv",
        "global_portfolio_league_weights.csv",
        "global_top_holdings_explanation.csv",
        "global_portfolio_risk_report.csv",
        "global_walk_forward_model_comparison.csv",
        "global_walk_forward_leakage_audit.csv",
        "global_walk_forward_uncertainty.csv",
        "global_stress_test_results.csv",
        "quantverse_v2_visual_exposure.csv",
        "quantverse_v2_visual_equity_curve.csv",
        "quantverse_v2_visual_drawdown_curve.csv",
        "quantverse_v2_visual_model_risk_return.csv",
        "quantverse_v2_visual_random_benchmark.csv",
        "quantverse_v2_visual_forecast_error.csv",
        "global_risk_metric_sanity_checks.csv",
        "global_security_identity_audit.csv",
        "global_security_history_eligibility.csv",
    ]
    for filename in files:
        run_id = "run-2" if filename == mismatched_artifact else "run-1"
        row_identity = {
            field: [run_id if field == "run_id" else value]
            for field, value in manifest.items()
        }
        payload: dict[str, list[object]] = {
            **row_identity,
            "value": [1.0],
        }
        if filename in {
            "quantverse_v2_reference_math_checks.csv",
            "quantverse_v2_visual_validation.csv",
            "global_risk_metric_sanity_checks.csv",
        }:
            payload.update({"check": ["synthetic_check"], "passed": [True]})
        if filename == "global_portfolio_league.csv":
            payload.update(
                {
                    "model_name": ["Equal Weight"],
                    "configured_max_weight": [1.0],
                }
            )
        if filename == "global_model_selection_report.csv":
            payload.update(
                {
                    "model_name": ["Equal Weight"],
                    "eligible_final_model": [True],
                    "selection_score": [1.0],
                    "book_grounded_rank": [1],
                    "random_sharpe_percentile": [0.70],
                    "promotion_gate_failed_reasons": [
                        "benchmark self-comparison is not applicable"
                    ],
                    "rejection_reason": ["benchmark self-comparison is not applicable"],
                    "sharpe_improvement_vs_equal_weight": [0.0],
                    "beats_equal_weight_sharpe": [False],
                    "drawdown_not_materially_worse_than_equal_weight": [True],
                    "cvar_not_materially_worse_than_equal_weight": [True],
                    "turnover_within_limit": [True],
                    "random_sharpe_gate_pass": [True],
                    "uncertainty_gate_pass": [True],
                    "robustness_gate_pass": [False],
                    "forecast_validation_gate_pass": [True],
                    "extreme_metric_warning": ["none"],
                    "walk_forward_sharpe": [1.0],
                    "walk_forward_annualized_return": [0.10],
                    "walk_forward_max_drawdown": [-0.05],
                    "walk_forward_cvar_95": [-0.02],
                    "turnover": [0.20],
                    "leakage_gate_pass": [True],
                    "leakage_evidence_status": [
                        "verified_current_no_lookahead_with_" "survivorship_limitation"
                    ],
                }
            )
        if filename == "global_walk_forward_leakage_audit.csv":
            rows = []
            for check in [
                "train_end_before_test_start",
                "scores_as_of_not_after_train_end",
                "selected_tickers_available_in_train",
                "scores_recomputed_inside_fold",
            ]:
                rows.append(
                    {
                        **{
                            field: (run_id if field == "run_id" else value)
                            for field, value in manifest.items()
                        },
                        "fold": 1,
                        "check": check,
                        "passed": True,
                        "audit_status": (
                            "passed_with_current_universe_survivorship_limitation"
                        ),
                        "evidence_scope": "current_universe_not_point_in_time",
                    }
                )
            pd.DataFrame(rows).to_csv(processed / filename, index=False)
            continue
        if filename == "global_portfolio_league_weights.csv":
            payload.update(
                {
                    "model_name": [
                        "Equal Weight" if include_final_weights else "Other Model"
                    ],
                    "ticker": ["A"],
                    "weight": [1.0],
                }
            )
        if filename == "global_top_holdings_explanation.csv":
            payload.update(
                {
                    "model_name": ["Equal Weight"],
                    "ticker": ["A"],
                    "weight": [1.0],
                }
            )
        pd.DataFrame(payload).to_csv(processed / filename, index=False)
    selection = pd.read_csv(processed / "global_model_selection_report.csv")
    decision = build_final_model_decision(selection)
    decision.update(manifest)
    (processed / "global_final_model_decision.json").write_text(
        json.dumps(decision),
        encoding="utf-8",
    )
    _refresh_publication_registry(root)


def _refresh_publication_registry(
    root: Path,
    paths: list[Path] | None = None,
) -> None:
    processed = root / "data" / "processed"
    manifest = json.loads(
        (processed / "quantverse_v2_run_manifest.json").read_text(encoding="utf-8")
    )
    artifacts = paths or [
        path
        for path in processed.iterdir()
        if path.name != "quantverse_v2_run_manifest.json"
    ]
    register_artifacts(
        processed,
        artifacts,
        manifest,
        root=root,
    )


def test_publication_evidence_loader_rejects_mixed_runs(tmp_path):
    _write_publication_evidence(
        tmp_path,
        mismatched_artifact="global_stress_test_results.csv",
    )

    with pytest.raises(ValueError, match="mixes runs"):
        load_publication_evidence(tmp_path)


def test_publication_evidence_loader_rejects_failed_reference_math(tmp_path):
    _write_publication_evidence(tmp_path)
    path = tmp_path / "data" / "processed" / "quantverse_v2_reference_math_summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update({"status": "failed", "failed_check_count": 1})
    path.write_text(json.dumps(payload), encoding="utf-8")
    _refresh_publication_registry(tmp_path, [path])

    with pytest.raises(ValueError, match="reference_math:not_passed"):
        load_publication_evidence(tmp_path)


def test_publication_evidence_loader_requires_declared_final_weights(tmp_path):
    _write_publication_evidence(tmp_path, include_final_weights=False)

    with pytest.raises(ValueError, match="Final model weights are missing"):
        load_publication_evidence(tmp_path)


def test_publication_evidence_loader_rejects_non_run_id_identity_mismatch(tmp_path):
    _write_publication_evidence(tmp_path)
    path = tmp_path / "data" / "processed" / "global_portfolio_risk_report.csv"
    frame = pd.read_csv(path)
    frame["config_hash"] = "config-stale"
    frame.to_csv(path, index=False)
    _refresh_publication_registry(tmp_path, [path])

    with pytest.raises(ValueError, match="config_hash"):
        load_publication_evidence(tmp_path)


@pytest.mark.parametrize(
    "filename",
    [
        "global_risk_metric_sanity_checks.csv",
        "quantverse_v2_visual_validation.csv",
    ],
)
def test_publication_evidence_loader_rejects_failed_scientific_gate(
    tmp_path,
    filename,
):
    _write_publication_evidence(tmp_path)
    path = tmp_path / "data" / "processed" / filename
    frame = pd.read_csv(path)
    frame["passed"] = False
    frame.to_csv(path, index=False)
    _refresh_publication_registry(tmp_path, [path])

    with pytest.raises(ValueError, match="scientific gate failed"):
        load_publication_evidence(tmp_path)


def test_publication_evidence_loader_rejects_configured_weight_cap_breach(tmp_path):
    _write_publication_evidence(tmp_path)
    league_path = tmp_path / "data" / "processed" / "global_portfolio_league.csv"
    league = pd.read_csv(league_path)
    league["configured_max_weight"] = 0.90
    league.to_csv(league_path, index=False)
    _refresh_publication_registry(tmp_path, [league_path])

    with pytest.raises(ValueError, match="max_cap_breach"):
        load_publication_evidence(tmp_path)


def test_publication_snapshot_reads_duplicate_csv_path_once(tmp_path, monkeypatch):
    _write_publication_evidence(tmp_path)
    target = (
        tmp_path / "data" / "processed" / "global_portfolio_league_weights.csv"
    ).resolve()
    original = pd.read_csv
    reads: list[Path] = []

    def tracked_read_csv(path, *args, **kwargs):
        resolved = Path(path).resolve()
        if resolved == target:
            reads.append(resolved)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", tracked_read_csv)

    load_publication_evidence(
        tmp_path,
        additional_csv_paths=[target, target],
    )

    assert reads == [target]


def test_publication_evidence_loader_rejects_stale_passed_source_hash(tmp_path):
    _write_publication_evidence(tmp_path)
    path = tmp_path / "data" / "processed" / "quantverse_v2_visual_validation.csv"
    frame = pd.read_csv(path)
    frame["value"] = 999.0
    frame.to_csv(path, index=False)

    with pytest.raises(ValueError, match="registered source hash"):
        load_publication_evidence(tmp_path)


def test_publication_evidence_loader_rejects_unregistered_additional_csv(tmp_path):
    _write_publication_evidence(tmp_path)
    extra = tmp_path / "data" / "processed" / "unregistered_excel_source.csv"
    pd.DataFrame({"value": [1.0]}).to_csv(extra, index=False)

    with pytest.raises(ValueError, match="registered source hash"):
        load_publication_evidence(
            tmp_path,
            additional_csv_paths=[extra],
        )


def test_publication_evidence_loader_rejects_decision_not_derived_from_selection(
    tmp_path,
):
    _write_publication_evidence(tmp_path)
    path = tmp_path / "data" / "processed" / "global_final_model_decision.json"
    decision = json.loads(path.read_text(encoding="utf-8"))
    decision["final_decision"] = "promoted"
    path.write_text(json.dumps(decision), encoding="utf-8")
    _refresh_publication_registry(tmp_path, [path])

    with pytest.raises(ValueError, match="decision_mismatch"):
        load_publication_evidence(tmp_path)


def test_published_turnover_formula_matches_gross_l1_contract():
    source = (
        ROOT / "src" / "project" / "reporting" / "quantverse_v2_publication.py"
    ).read_text(encoding="utf-8")

    assert '"sum_i |w_i,t - w_i,t-1|"' in source
    assert '"0.5 * sum_i |w_i,t - w_i,t-1|"' not in source


def test_excel_writer_treats_formula_and_url_like_evidence_as_plain_text(tmp_path):
    path = tmp_path / "plain-text-evidence.xlsx"
    with pd.ExcelWriter(
        path,
        engine="xlsxwriter",
        engine_kwargs=EXCEL_ENGINE_KWARGS,
    ) as writer:
        pd.DataFrame(
            {
                "evidence": [
                    "=1+1",
                    "https://example.invalid/research-evidence",
                ]
            }
        ).to_excel(writer, index=False)

    with zipfile.ZipFile(path) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        shared_strings = workbook.read("xl/sharedStrings.xml").decode("utf-8")

    assert "<f>" not in sheet_xml
    assert "<hyperlink" not in sheet_xml
    assert "=1+1" in shared_strings
    assert "https://example.invalid/research-evidence" in shared_strings


def test_html_publication_constrains_mobile_grid_and_table_overflow():
    source = (
        ROOT / "src" / "project" / "reporting" / "quantverse_v2_publication.py"
    ).read_text(encoding="utf-8")

    assert "main {{ width:min(1180px,100%); min-width:0; max-width:100%;" in source
    assert (
        ".table-wrap {{ width:100%; min-width:0; max-width:100%; overflow-x:auto;"
        in source
    )
    assert ".layout {{ grid-template-columns:minmax(0,1fr); }}" in source
    assert "@media (max-width:520px)" in source
