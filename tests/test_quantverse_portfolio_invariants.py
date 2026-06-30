import pandas as pd

from scripts.audit_quantverse_portfolio_logic import (
    _bool,
    _weight_issues,
    _weight_rows,
)
from scripts.build_global_quant_capability_gap_matrix import (
    ALLOWED_STATUS,
    build_matrix,
)


def test_weight_audit_accepts_complete_long_only_portfolio():
    weights = pd.DataFrame(
        {
            "Model": ["Equal Weight", "Equal Weight", "Equal Weight"],
            "Ticker": ["AAA", "BBB", "CCC"],
            "Weight": [0.2, 0.3, 0.5],
        }
    )

    rows = _weight_rows(weights, "Model", "Ticker", "Weight", "unit.csv")

    assert rows[0]["weight_sum"] == 1.0
    assert rows[0]["negative_weights"] == 0
    assert _weight_issues(rows) == []


def test_weight_audit_flags_bad_sum_and_negative_weights():
    weights = pd.DataFrame(
        {
            "Model": ["Bad", "Bad"],
            "Ticker": ["AAA", "BBB"],
            "Weight": [1.2, -0.1],
        }
    )

    rows = _weight_rows(weights, "Model", "Ticker", "Weight", "unit.csv")
    issues = {issue["issue"] for issue in _weight_issues(rows)}

    assert "weight_sum_not_one" in issues
    assert "negative_weight_without_shorting" in issues


def test_boolean_flag_parser_is_case_insensitive_and_conservative():
    frame = pd.DataFrame({"include": ["TRUE", "yes", "0", "", None]})

    assert _bool(frame, "include").tolist() == [True, True, False, False, False]
    assert _bool(frame, "missing").tolist() == [False, False, False, False, False]


def test_capability_gap_matrix_covers_all_84_questions_with_allowed_statuses():
    matrix = build_matrix()

    assert len(matrix) == 84
    assert set(matrix["item"]) == set(range(1, 85))
    assert set(matrix["status"]).issubset(ALLOWED_STATUS)
    assert matrix["question"].str.len().gt(0).all()
