# QuantVerse Quality Sprint Transfer Manifest

Date: 2026-06-25

This manifest is for moving safe local-only work from the old non-Git QuantVerse
working folder into the clean GitHub clone. Do not treat the old folder's `.git`
metadata as authoritative. Do not copy virtual environments, caches, heavy
generated data, reports, PDF handoff files or output directories.

## 1. Files Changed By This Sprint

- `src/project/research/challenger.py`
- `src/project/research/__init__.py`
- `src/project/pipeline.py`
- `src/project/reporting/pdf_report.py`
- `tests/test_challenger_research.py`
- `tests/test_transfer_readiness.py`
- `README.md`
- `docs/reproducibility.md`
- `docs/testing_strategy.md`
- `docs/interview_defense_questions.md`
- `docs/audit/FINAL_SCORECARD.md`
- `docs/audit/QUANTVERSE_AUDIT.md`
- `docs/audit/EVIDENCE_MATRIX.md`
- `docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.md`
- `docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.json`
- `tools/migration/copy_quality_sprint_to_clean_repo.ps1`

## 2. Files Added By This Sprint

- `docs/research/research_grounded_quantverse_architecture.md`
- `docs/research/literature_to_quantverse_implementation_matrix.md`
- `docs/research/model_league_system.md`
- `docs/research/risk_covariance_upgrade_plan.md`
- `docs/research/ml_ai_quantverse_strategy.md`
- `docs/research/validation_hardening_plan.md`
- `tests/test_research_architecture_outputs.py`

## 3. Files That Must Be Copied To The Clean Repo

Copy these categories from the old working folder to the clean clone:

- `src/`
- `src/project/research/`
- `tests/`
- `docs/`
- `docs/research/`
- `configs/`
- `config/` if present
- project CLI script: `scripts/run_full_pipeline.py`
- `README.md`
- `pyproject.toml`
- `Makefile`
- `.pre-commit-config.yaml`
- `.gitignore`
- lightweight generated review artefacts:
  - `data/processed/*.csv`
  - `data/processed/*.json`
  - `data/processed/*.png`

Important Windows note: the old folder contains a polluted `Scripts/`
environment directory. The helper script does not copy the whole `Scripts/`
tree. It copies only the project script `scripts/run_full_pipeline.py`.

## 4. Files And Folders That Must NOT Be Copied

- `.git/`
- `Lib/`
- `Scripts/`
- `etc/`
- `share/`
- `.venv/`
- `venv/`
- `env/`
- `data/cache/`
- `data/raw/`
- `data/processed/*.parquet`
- `data/processed/*.pkl`
- `data/processed/*.pickle`
- `output/`
- `reports/`
- `.pytest_cache/`
- `__pycache__/`
- `.ipynb_checkpoints/`
- `.ruff_cache/`
- `tmp/`
- PDF handoff files

## 5. Exact Windows PowerShell Transfer Commands

Set these variables after replacing the placeholders:

```powershell
$SourceRoot = "OLD_QUANTVERSE_WORKING_FOLDER"
$DestRoot = "CLEAN_GITHUB_CLONE_FOLDER"
```

Run a dry run first:

```powershell
powershell -ExecutionPolicy Bypass -File "$SourceRoot\tools\migration\copy_quality_sprint_to_clean_repo.ps1" `
  -SourceRoot $SourceRoot `
  -DestRoot $DestRoot `
  -DryRun
```

If the dry run output is correct, run the real copy:

```powershell
powershell -ExecutionPolicy Bypass -File "$SourceRoot\tools\migration\copy_quality_sprint_to_clean_repo.ps1" `
  -SourceRoot $SourceRoot `
  -DestRoot $DestRoot
```

Manual fallback commands if the helper script is unavailable:

```powershell
robocopy "$SourceRoot\src" "$DestRoot\src" /E /XD .git .venv venv env __pycache__ .pytest_cache .ipynb_checkpoints .ruff_cache tmp output reports /XF *.pyc *.pyo *.parquet *.pkl *.pickle
robocopy "$SourceRoot\tests" "$DestRoot\tests" /E /XD __pycache__ .pytest_cache .ipynb_checkpoints /XF *.pyc *.pyo
robocopy "$SourceRoot\docs" "$DestRoot\docs" /E /XD __pycache__ .pytest_cache .ipynb_checkpoints /XF *.pyc *.pyo
robocopy "$SourceRoot\configs" "$DestRoot\configs" /E /XD __pycache__ .pytest_cache .ipynb_checkpoints /XF *.pyc *.pyo
if (Test-Path "$SourceRoot\config") { robocopy "$SourceRoot\config" "$DestRoot\config" /E /XD __pycache__ .pytest_cache .ipynb_checkpoints /XF *.pyc *.pyo }
New-Item -ItemType Directory -Force "$DestRoot\scripts" | Out-Null
Copy-Item "$SourceRoot\scripts\run_full_pipeline.py" "$DestRoot\scripts\run_full_pipeline.py" -Force
Copy-Item "$SourceRoot\README.md" "$DestRoot\README.md" -Force
Copy-Item "$SourceRoot\pyproject.toml" "$DestRoot\pyproject.toml" -Force
Copy-Item "$SourceRoot\Makefile" "$DestRoot\Makefile" -Force
Copy-Item "$SourceRoot\.pre-commit-config.yaml" "$DestRoot\.pre-commit-config.yaml" -Force
Copy-Item "$SourceRoot\.gitignore" "$DestRoot\.gitignore" -Force
New-Item -ItemType Directory -Force "$DestRoot\data\processed" | Out-Null
Copy-Item "$SourceRoot\data\processed\*.csv" "$DestRoot\data\processed\" -Force
Copy-Item "$SourceRoot\data\processed\*.json" "$DestRoot\data\processed\" -Force
Copy-Item "$SourceRoot\data\processed\*.png" "$DestRoot\data\processed\" -Force
```

## 6. Exact Post-Transfer Validation Commands

Run these inside the clean GitHub clone:

```powershell
python -m pip install -e ".[dev]"
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
python scripts/run_full_pipeline.py --config configs/base.yaml
```

## 7. Expected Successful Outputs

- `python -m black --check src scripts tests`: exit code 0; files would be left
  unchanged.
- `python -m ruff check src scripts tests`: exit code 0; `All checks passed!`.
- `python -m pytest -q`: exit code 0; latest local validation result is
  `71 passed`.
- `python -m compileall src scripts`: exit code 0.
- `python scripts/run_full_pipeline.py --config configs/base.yaml`: exit code 0;
  refreshed `data/processed/`, `reports/`, `output/html/` and `output/pdf/`
  artefacts.

## 8. Review Notes

- The old folder is a staging folder, not the clean Git repository.
- No commit, branch, push, upload or external account action is part of this
  sprint.
- Lightweight data files are review artefacts. Heavy Parquet/pickle outputs are
  intentionally regenerated locally instead of copied.
- The helper copies `docs/research/` and `src/project/research/` through the
  broader `docs/` and `src/` categories.
