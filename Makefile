.PHONY: setup test lint typecheck format smoke pipeline report clean

PYTHON ?= python
CONFIG ?= configs/base.yaml

setup:
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src scripts tests

typecheck:
	$(PYTHON) -m pyright

format:
	$(PYTHON) -m black src scripts tests

smoke:
	$(PYTHON) -m compileall src scripts
	$(PYTHON) -m pytest -q tests/test_config_pipeline.py tests/test_data_pipeline.py tests/test_optimization.py tests/test_risk.py

pipeline:
	$(PYTHON) scripts/run_full_pipeline.py --config $(CONFIG) --skip-pdf

report:
	$(PYTHON) scripts/run_full_pipeline.py --config $(CONFIG)

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in map(pathlib.Path, ['.pytest_cache', 'src/quantverse.egg-info', 'src/project.egg-info'])]"
