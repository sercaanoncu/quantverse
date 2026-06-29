# Validation

Standard local validation:

```bash
python -m black src scripts tests
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
git status
```

The full ETF pipeline is not required unless explicitly part of the sprint.

Generated outputs should be cleaned before commit:

```bash
git clean -fd -- data/processed
git clean -f -- data/universe/current_global_equity_universe.csv
```
