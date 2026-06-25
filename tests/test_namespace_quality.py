import importlib
from pathlib import Path


def test_public_quantverse_top_level_imports():
    import quantverse

    assert hasattr(quantverse, "PipelineConfig")
    assert hasattr(quantverse, "run_full_pipeline")


def test_public_quantverse_pipeline_module_imports():
    pipeline = importlib.import_module("quantverse.pipeline")

    assert hasattr(pipeline, "PipelineConfig")
    assert hasattr(pipeline, "run_full_pipeline")


def test_public_quantverse_nested_risk_module_imports():
    validation = importlib.import_module("quantverse.risk.validation")

    assert hasattr(validation, "var_exception_tests")


def test_public_quantverse_reporting_module_imports():
    pdf_report = importlib.import_module("quantverse.reporting.pdf_report")

    assert hasattr(pdf_report, "InvestmentPDFReport")
    assert hasattr(pdf_report, "generate_pdf_report")


def test_legacy_project_namespace_still_imports():
    legacy = importlib.import_module("project.pipeline")

    assert hasattr(legacy, "PipelineConfig")
    assert hasattr(legacy, "run_full_pipeline")


def test_committed_text_sources_do_not_contain_local_absolute_paths():
    roots = [
        Path("src"),
        Path("scripts"),
        Path("tests"),
        Path("docs"),
        Path("configs"),
    ]
    files = [Path("README.md"), Path("pyproject.toml"), Path("Makefile")]
    for root in roots:
        files.extend(path for path in root.rglob("*") if path.is_file())

    slash = "\\"
    banned = [
        f"C:{slash}Users{slash}",
        f"{slash}OneDrive{slash}",
        f"{slash}Desktop{slash}",
        f"{slash}Proje{slash}",
        "/" + "Users" + "/",
    ]
    offenders = []
    for path in files:
        if any(part.endswith(".egg-info") for part in path.parts):
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in {
            ".cfg",
            ".ini",
            ".md",
            ".py",
            ".toml",
            ".txt",
            ".yaml",
            ".yml",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern in text for pattern in banned):
            offenders.append(str(path))

    assert offenders == []
