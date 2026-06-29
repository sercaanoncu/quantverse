# TESTING.md

## Standard Commands

```powershell
python -m black src scripts tests
python -m black --check src scripts tests
python -m ruff check src scripts tests
python -m pytest -q
python -m compileall src scripts
git status
```

## When To Run More

Run focused tests first for the changed module. Run the full pytest suite before
committing. The full ETF pipeline is required only when the task explicitly
changes that pipeline or its outputs.

## Financial Sanity Checks

- weights sum to 1
- long-only constraints are respected when configured
- benchmark and candidate use aligned dates
- transaction-cost assumptions are stated
- generated data outputs are excluded from commits
