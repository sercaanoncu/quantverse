from pathlib import Path

import pandas as pd

REQUIRED_CONTEXT_FILES = [
    "AGENTS.md",
    "PROJECT_CONTEXT.md",
    "PIPELINE_CONTEXT.md",
    "TESTING.md",
    "DEBUGGING.md",
    "CHANGELOG.md",
    "NOTES.md",
    "RAG_NOTES.md",
    ".codex/CONTEXT.md",
    ".codex/TASK_PROTOCOL.md",
    ".codex/OUTPUT_CONTRACT.md",
    ".codex/PROJECT_STATE.md",
    ".codex/DO_NOT_DO.md",
    ".codex/VALIDATION.md",
]


def test_repo_context_engineering_files_exist_and_carry_guardrails():
    for file_name in REQUIRED_CONTEXT_FILES:
        path = Path(file_name)
        assert path.exists(), file_name

    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    assert "Do not introduce look-ahead bias" in agents
    assert "Do not hardcode fake tickers" in agents
    assert (
        "generated outputs"
        in Path("PIPELINE_CONTEXT.md").read_text(encoding="utf-8").lower()
    )


def test_source_candidate_examples_are_header_only_templates():
    for path in Path("data/universe/sources").glob("*_candidates.example.csv"):
        frame = pd.read_csv(path)
        assert frame.empty, path.name
        assert {"ticker", "source_url", "as_of_date", "market_cap_usd"}.issubset(
            frame.columns
        )
