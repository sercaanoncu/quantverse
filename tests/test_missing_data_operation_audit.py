import ast
from pathlib import Path

from scripts.audit_quantverse_v2_missing_data_operations import scan_repository

ROOT = Path(__file__).resolve().parents[1]


def test_missing_data_audit_classifies_every_active_operation():
    frame = scan_repository(ROOT)

    assert not frame.empty
    assert frame["operation_id"].is_unique
    assert frame["classification"].notna().all()
    assert frame["required_control"].astype(str).str.len().gt(0).all()
    assert frame["approved"].astype(bool).all()


def test_active_source_has_no_backward_or_unbounded_forward_fill():
    frame = scan_repository(ROOT)

    assert (
        not frame["classification"]
        .isin(["PROHIBITED_BACKWARD_FILL", "UNBOUNDED_FORWARD_FILL"])
        .any()
    )


def test_missing_data_audit_document_states_return_zero_fill_boundary():
    text = (
        ROOT / "docs" / "audit" / "QUANTVERSE_V2_MISSING_DATA_OPERATION_AUDIT.md"
    ).read_text(encoding="utf-8")

    assert "Selected-return zero fill is prohibited" in text
    assert "Complete Inventory" in text
    assert "Unapproved operations: **0**" in text


def test_missing_data_audit_script_has_valid_python_syntax():
    path = ROOT / "scripts" / "audit_quantverse_v2_missing_data_operations.py"

    ast.parse(path.read_text(encoding="utf-8"))


def test_unreviewed_zero_fill_is_rejected_even_in_a_formerly_safe_module(tmp_path):
    source = tmp_path / "src" / "project" / "research" / "global_walk_forward.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def injected(selected_returns):\n" "    return selected_returns.fillna(0.0)\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)
    row = frame.iloc[0]

    assert row["classification"] == "REVIEW_REQUIRED_NUMERIC_ZERO_FILL"
    assert not bool(row["approved"])
    assert str(row["source_tree_hash"]).startswith("source-")


def test_future_or_fallback_imputation_apis_fail_closed(tmp_path):
    source = tmp_path / "src" / "adversarial_imputation.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import numpy as np\n"
        "def attack(frame, other):\n"
        "    frame.fillna(method='bfill')\n"
        "    frame.interpolate(method='time')\n"
        "    np.nan_to_num(frame)\n"
        "    frame.combine_first(other)\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)

    assert set(frame["operation"]) == {
        "bfill",
        "interpolate",
        "nan_to_num",
        "combine_first",
    }
    assert not frame["approved"].astype(bool).any()


def test_forward_fill_requires_a_non_null_positive_limit(tmp_path):
    source = tmp_path / "src" / "adversarial_forward_fill.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def attack(frame):\n"
        "    frame.ffill(limit=None)\n"
        "    frame.ffill(limit=0)\n"
        "    frame.ffill(limit=-1)\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)

    assert set(frame["classification"]) == {"UNBOUNDED_FORWARD_FILL"}
    assert not frame["approved"].astype(bool).any()


def test_dynamic_forward_fill_limit_requires_exact_reviewed_callsite(tmp_path):
    source = tmp_path / "src" / "adversarial_dynamic_forward_fill.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def attack(frame, user_limit, get_limit):\n"
        "    frame.ffill(limit=user_limit)\n"
        "    frame.ffill(limit=get_limit())\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)

    assert set(frame["classification"]) == {"UNBOUNDED_FORWARD_FILL"}
    assert not frame["approved"].astype(bool).any()


def test_reindex_zero_fill_requires_exact_structural_allowlist_entry(tmp_path):
    source = tmp_path / "src" / "adversarial_reindex.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def attack(frame, labels):\n"
        "    return frame.reindex(labels, fill_value=0.0)\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)
    row = frame.iloc[0]

    assert row["classification"] == "REVIEW_REQUIRED_NUMERIC_ZERO_FILL"
    assert not bool(row["approved"])


def test_unreviewed_numeric_expression_is_not_mislabelled_as_metadata(tmp_path):
    source = tmp_path / "src" / "numeric_imputation.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def attack(frame):\n" "    return frame.fillna(frame.mean())\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)
    row = frame.iloc[0]

    assert row["classification"] == "NUMERIC_IMPUTATION_REQUIRES_REVIEW"
    assert not bool(row["approved"])


def test_string_and_boolean_fill_values_are_explicit_non_numeric_metadata(tmp_path):
    source = tmp_path / "src" / "metadata_fill.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def clean(frame):\n"
        "    frame['label'] = frame['label'].fillna('unavailable')\n"
        "    frame['flag'] = frame['flag'].fillna(False)\n"
        "    return frame\n",
        encoding="utf-8",
    )

    frame = scan_repository(tmp_path)

    assert set(frame["classification"]) == {"EXPLICIT_LABEL_OR_BOOLEAN_FILL"}
    assert frame["approved"].astype(bool).all()


def test_reviewed_numeric_imputations_are_bound_to_exact_callsites():
    frame = scan_repository(ROOT)
    reviewed = frame.loc[frame["classification"].eq("REVIEWED_NUMERIC_IMPUTATION")]

    assert not reviewed.empty
    assert reviewed["approved"].astype(bool).all()
    assert {
        "build_global_stock_scores",
        "_market_cap_percentile",
        "score_assets_for_selection",
    }.issubset(set(reviewed["function"]))
