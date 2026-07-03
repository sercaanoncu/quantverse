# GitHub Push Checklist

Do not push until every local command below passes and generated artifacts remain excluded from Git.

## Final Commands

```powershell
python scripts/run_quantverse_v2_demo.py --config configs/global_quant_research.yaml
python scripts/validate_quantverse_v2_artifacts.py
python scripts/build_quantverse_v2_research_report.py
python scripts/build_quantverse_v2_excel_output.py
python scripts/build_doctoral_thesis_report.py
python scripts/build_doctoral_defense_presentation.py
python -m pytest -q
python -m black src scripts tests
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m compileall src scripts
git status --short --branch
```

## Git Status Expectations

- No staged or tracked `data/processed/*` generated outputs.
- No staged or tracked `output/*` generated reports.
- No staged or tracked `data/universe/current_global_equity_universe.csv`.
- Source/docs/tests changes only.
- Generated local artifacts may exist in the working tree, but should be ignored.

## Push Command

```powershell
git push origin integrate-fx-marketcap-gates
```

## Suggested PR Title

`Release QuantVerse v2 public-data research engine`

## Suggested PR Description

```markdown
## Summary
- Adds QuantVerse v2 public-data global equity research outputs, robust model selection, walk-forward evidence, random portfolio benchmarking, forecast diagnostics, exposure/risk reporting, and publication guardrails.
- Adds release-candidate artifact validation and reproducibility documentation.
- Keeps generated data/report artifacts out of Git.

## Validation
- python scripts/run_quantverse_v2_demo.py --config configs/global_quant_research.yaml
- python scripts/validate_quantverse_v2_artifacts.py
- python scripts/build_quantverse_v2_research_report.py
- python scripts/build_quantverse_v2_excel_output.py
- python scripts/build_doctoral_thesis_report.py
- python scripts/build_doctoral_defense_presentation.py
- python -m pytest -q
- python -m black --check src scripts tests
- python -m ruff check src scripts tests
- python -m compileall src scripts

## Limitations
- Public-data research only; not investment advice.
- No official exact top-100 market-cap claim.
- No institutional point-in-time backtest claim.
- Global master portfolio remains not promoted.
```

## Suggested GitHub Repository Description

`Public-data quantitative equity research and risk analytics engine with model leagues, walk-forward validation, random portfolio benchmarks, and explicit claim controls.`

## Suggested Pinned Project Text

`QuantVerse v2: a transparent public-data quant research project that compares portfolio models, validates risk and robustness, and keeps investment-claim limitations visible.`

## Final Release Gate

Only push after the final validation run passes and the last `git status --short --branch` shows no generated artifact files staged or tracked.
