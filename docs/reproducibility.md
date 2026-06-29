# QuantVerse Reproducibility Guide

Date: 2026-06-25

## Tested Environment

- Python: 3.12
- Operating system: Windows
- Main configuration: `configs/base.yaml`
- Production command: `python scripts/run_full_pipeline.py --config configs/base.yaml`
- Working-folder note: this repository is the clean GitHub clone. Git branch
  and commit state should be checked in this folder before release work.

## Installation

Production pipeline:

```powershell
python -m pip install -e .
```

Development and validation tools:

```powershell
python -m pip install -e ".[dev]"
```

Notebook dependencies, if needed:

```powershell
python -m pip install -e ".[dev,notebook]"
```

## Validation Commands

```powershell
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
python scripts/run_full_pipeline.py --config configs/base.yaml
```

Latest validated pytest result:

```text
83 passed
```

This file should be updated whenever deterministic tests are added or removed.

## Generated Artifact Policy

`data/processed`, `reports`, `output/pdf` and `output/html` contain reproducible
research artifacts. Lightweight CSV/JSON/PNG files may be copied into the clean
repo for review when the transfer manifest says so. Heavy Parquet, pickle, PDF,
HTML, cache and figure outputs are not required source files for the clean repo.

During transfer:

- Copy: `data/processed/*.csv`, `data/processed/*.json`,
  `data/processed/*.png`
- Do not copy: `data/processed/*.parquet`, `data/processed/*.pkl`,
  `data/processed/*.pickle`, `output/`, `reports/`, `data/cache/`, `data/raw/`

Detailed transfer procedure:

- `docs/audit/QUALITY_SPRINT_TRANSFER_MANIFEST.md`
- `tools/migration/copy_quality_sprint_to_clean_repo.ps1`

## Data Source Note

The pipeline uses public `yfinance` data. Running the same command on another
date can change the final data date, risk-free quote and market prices.
Institutional use would require Bloomberg, Refinitiv, ICE, FactSet or another
controlled vendor plus independent reconciliation.

## Portability Note

Output metadata must not contain host-specific absolute paths. `run_metadata.json`
should record repository-relative paths such as `configs/base.yaml`.

## Research Output Note

Research outputs are split into benchmark, alpha challenger, risk engine,
validation engine and governance artifacts. The most important review files are:

- `data/processed/research_alpha_leaderboard.csv`
- `data/processed/model_league_summary.csv`
- `data/processed/model_promotion_gate.csv`
- `data/processed/model_overfit_diagnostics.csv`
- `data/processed/covariance_model_comparison.csv`

## Platform Notes

- Tested on Windows PowerShell.
- Makefile targets can be used where GNU Make is available.
- PDF generation uses `reportlab`; PDF QA can use `pdfplumber` and Poppler.
- Git commit and branch validation must be done in this clean repository before
  release work.
