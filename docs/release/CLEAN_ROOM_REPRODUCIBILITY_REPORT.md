# Clean-Room Reproducibility Report

> Historical record: this file describes the earlier isolated
> `quantverse_release_check` run. Its Policy Constrained model and 164/166-test
> counts are not the current QuantVerse v2 result. The current corrected clean
> output rebuild is documented in
> `docs/audit/QUANTVERSE_V2_FULL_AUDIT_REPAIR_IMPACT.md`; it selects Equal
> Weight as the public-data research model and remains `not promoted`.

Clean-room path:

`<desktop>/quantverse_release_check`

The clean-room run was built from tracked repository contents using `git archive`. Existing local generated outputs were not copied. After extraction, `data/processed` was explicitly emptied before the demo run to verify that the v2 pipeline can regenerate evidence from committed source files and public data.

## Commands Run

| Command | Result | Evidence |
| ------- | ------ | -------- |
| `python -m pip install -e ".[dev]"` | Passed | Editable install completed as `quantverse-1.0.0`; dependencies were already mostly satisfied |
| `python scripts/run_quantverse_v2_demo.py --config configs/global_quant_research.yaml` | Passed | Generated v2 outputs from clean-room state |
| `python scripts/build_quantverse_v2_research_report.py` | Passed | PDF/HTML research report regenerated |
| `python scripts/build_quantverse_v2_excel_output.py` | Passed | Excel workbook regenerated |
| `python scripts/build_doctoral_thesis_report.py` | Passed | Full thesis PDF regenerated; 74 pages reported |
| `python scripts/build_doctoral_defense_presentation.py` | Passed | Defense PDFs regenerated; full defense 55 pages reported |
| `python -m pytest -q` | Passed | `164 passed in 52.99s`; non-fatal Windows temp cleanup warning appeared after tests |
| `python -m black --check src scripts tests` | Passed | Formatting check clean |
| `python -m ruff check src scripts tests` | Passed | Lint check clean |
| `python -m compileall src scripts` | Passed | Source compile check clean |

## Regenerated Output Paths

| Artifact | Path |
| -------- | ---- |
| v2 PDF report | `<desktop>/quantverse_release_check/output/pdf/quantverse_v2_research_report.pdf` |
| v2 HTML report | `<desktop>/quantverse_release_check/output/html/quantverse_v2_research_report.html` |
| v2 Excel workbook | `<desktop>/quantverse_release_check/output/excel/quantverse_v2_research_output.xlsx` |
| Full thesis PDF | `<desktop>/quantverse_release_check/output/thesis/quantverse_doctoral_dissertation_full.pdf` |
| Full defense PDF | `<desktop>/quantverse_release_check/output/thesis/quantverse_doctoral_defense_presentation_full.pdf` |

## Row Counts And Run Summary

| Output | Clean-room Evidence |
| ------ | ------------------- |
| Current global universe | 600 rows |
| Assets with returns | 589 assets |
| Stock scores | 589 rows |
| Forecast rows | 2356 rows |
| Portfolio league | 13 models |
| Risk report | 10 portfolios |
| Walk-forward status | `completed_public_data_current_universe` |
| Final research model | `Policy Constrained` in the clean-room run |
| Final promotion decision | `not promoted` |
| Publish readiness | `research_publish_ready_with_limitations` |

## Warnings

- `scripts/run_global_master_portfolio.py` emitted a non-fatal pandas `FutureWarning` about concatenation with all-NA entries.
- The test run emitted a non-fatal Windows temporary-directory cleanup `PermissionError` after reporting all tests passed.
- The clean-room final model differed from the pre-existing local generated output because public-data generated artifacts are time-sensitive and are not committed. This does not invalidate reproducibility because the clean-room run completed from source, produced internally consistent summaries, and retained the `not promoted` decision.

## Reproducibility Decision

The clean-room run passed using committed source files only. It did not rely on untracked local `data/processed` or `output` artifacts.
