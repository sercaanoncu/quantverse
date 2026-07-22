"""Inventory and classify active QuantVerse missing-data operations."""

from __future__ import annotations

import ast
import hashlib
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = (
    ROOT / "data" / "processed" / "quantverse_v2_missing_data_operation_audit.csv"
)
OUTPUT_MD = ROOT / "docs" / "audit" / "QUANTVERSE_V2_MISSING_DATA_OPERATION_AUDIT.md"
ZERO_FILL_ALLOWLIST = (
    ROOT
    / "docs"
    / "audit"
    / "evidence"
    / "QUANTVERSE_V2_ZERO_FILL_CALLSITE_ALLOWLIST.csv"
)
NUMERIC_FILL_ALLOWLIST = (
    ROOT
    / "docs"
    / "audit"
    / "evidence"
    / "QUANTVERSE_V2_NUMERIC_FILL_CALLSITE_ALLOWLIST.csv"
)
FORWARD_FILL_ALLOWLIST = (
    ROOT
    / "docs"
    / "audit"
    / "evidence"
    / "QUANTVERSE_V2_FORWARD_FILL_CALLSITE_ALLOWLIST.csv"
)

OPERATIONS = {
    "fillna",
    "dropna",
    "reindex",
    "merge",
    "join",
    "ffill",
    "bfill",
    "interpolate",
    "nan_to_num",
    "combine_first",
}


class ClassificationResult(TypedDict):
    classification: str
    risk_level: str
    status: str
    approved: bool
    reason: str
    required_control: str


@dataclass(frozen=True)
class MissingDataOperation:
    operation_id: str
    path: str
    line: int
    function: str
    operation: str
    callsite_fingerprint: str
    code: str
    classification: str
    risk_level: str
    status: str
    approved: bool
    reason: str
    required_control: str


class _OperationVisitor(ast.NodeVisitor):
    def __init__(self, path: str, source: str):
        self.path = path
        self.source = source
        self.lines = source.splitlines()
        self.function_stack: list[str] = []
        self.rows: list[MissingDataOperation] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in OPERATIONS:
            operation = node.func.attr
            if operation == "join" and isinstance(
                node.func.value,
                (ast.Constant, ast.JoinedStr),
            ):
                self.generic_visit(node)
                return
            code = (
                ast.get_source_segment(self.source, node)
                or self.lines[node.lineno - 1].strip()
            )
            operation = _normalized_operation(operation, code)
            function = self.function_stack[-1] if self.function_stack else "<module>"
            fingerprint = _callsite_fingerprint(node)
            classification = _classify(
                path=self.path,
                line=int(node.lineno),
                function=function,
                operation=operation,
                code=code,
                callsite_fingerprint=fingerprint,
                node=node,
            )
            self.rows.append(
                MissingDataOperation(
                    operation_id="",
                    path=self.path,
                    line=int(node.lineno),
                    function=function,
                    operation=operation,
                    callsite_fingerprint=fingerprint,
                    code=" ".join(code.split())[:240],
                    **classification,
                )
            )
        self.generic_visit(node)


def scan_repository(root: str | Path = ROOT) -> pd.DataFrame:
    """Return one classified row for every active missing-data operation."""
    root_path = Path(root).resolve()
    rows: list[MissingDataOperation] = []
    files = sorted((root_path / "src").rglob("*.py")) + sorted(
        (root_path / "scripts").rglob("*.py")
    )
    for path in files:
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(root_path).as_posix()
        tree = ast.parse(source, filename=relative)
        visitor = _OperationVisitor(relative, source)
        visitor.visit(tree)
        rows.extend(visitor.rows)
    source_tree_hash = _source_tree_hash(files, root_path)
    records = []
    for index, row in enumerate(
        sorted(rows, key=lambda item: (item.path, item.line, item.operation)),
        start=1,
    ):
        payload = asdict(row)
        payload["operation_id"] = f"QV2-MD-{index:04d}"
        payload["source_tree_hash"] = source_tree_hash
        records.append(payload)
    return pd.DataFrame(records)


def write_audit_outputs(frame: pd.DataFrame) -> None:
    """Write the machine-readable inventory and tracked audit narrative."""
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_CSV, index=False)
    counts = (
        frame.groupby(["operation", "classification", "status"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["operation", "classification"])
    )
    unapproved = frame.loc[~frame["approved"].astype(bool)]
    lines = [
        "# QuantVerse v2 Missing-Data Operation Audit",
        "",
        "This audit inventories every active pandas missing-data/alignment operation "
        "under `src/` and `scripts/`. It distinguishes missing asset weights from "
        "missing asset returns. A structural zero for an absent portfolio weight is "
        "not permission to convert a missing selected return into zero.",
        "",
        "## Executive Result",
        "",
        f"- Operations inventoried: **{len(frame)}**",
        f"- Unapproved operations: **{len(unapproved)}**",
        (
            f"- Source-tree hash: **{frame['source_tree_hash'].iloc[0]}**"
            if not frame.empty and "source_tree_hash" in frame
            else "- Source-tree hash: **missing**"
        ),
        "- Unbounded backward fill is prohibited because it can carry future "
        "information into the past.",
        "- Forward fill must be explicitly bounded.",
        "- Selected-return zero fill is prohibited.",
        "- Complete-case removal is sample-altering and must remain visible in "
        "coverage and observation counts.",
        "",
        "## Classification Summary",
        "",
        _markdown_table(
            counts,
            ["operation", "classification", "status", "count"],
        ),
        "",
        "## Scientific Policy",
        "",
        "| Operation class | Permitted use | Required evidence |",
        "|---|---|---|",
        "| `STRUCTURAL_ZERO_ALIGNMENT` | Missing asset weight, score fallback, count or display bucket | The underlying selected return is not replaced; weight/score semantics are explicit |",
        "| `REVIEWED_NUMERIC_IMPUTATION` | Exact methodology-backed numerical fallback | AST fingerprint, call-site line and written rationale must match the numeric allowlist |",
        "| `COMPLETE_CASE_SAMPLE_REDUCTION` | Remove invalid or unavailable rows | Observation count, date range and coverage remain disclosed |",
        "| `INDEX_ALIGNMENT` | Align labeled series/dataframes | Missingness remains missing unless an explicit structural fill follows |",
        "| `RELATIONAL_ALIGNMENT` | Merge/join evidence by declared keys | Cardinality and unmatched rows are validated |",
        "| `BOUNDED_FORWARD_FILL` | Short calendar/provider gaps or diagnostic signal alignment | Explicit finite limit and no future information |",
        "| `PROHIBITED_BACKWARD_FILL` | None in research inputs | Must be removed or isolated as non-research display logic |",
        "| `REVIEW_REQUIRED_NUMERIC_ZERO_FILL` | None until reviewed | Explicit proof that values are not selected returns |",
        "",
        "## Complete Inventory",
        "",
        _markdown_table(
            frame,
            [
                "operation_id",
                "path",
                "line",
                "function",
                "operation",
                "callsite_fingerprint",
                "source_tree_hash",
                "classification",
                "risk_level",
                "status",
                "reason",
                "required_control",
            ],
        ),
        "",
        "## Invalidation Conditions",
        "",
        "- Any backward-fill call in active source invalidates the no-look-ahead contract.",
        "- Any forward-fill call without an explicit finite `limit` requires rejection.",
        "- Any selected return converted to zero without an explicit market-closure "
        "or cash model invalidates portfolio, covariance, risk and OOS evidence.",
        "- Any complete-case operation whose resulting dates/observations are not "
        "reported invalidates comparisons across models.",
        "",
        "Generated by `scripts/audit_quantverse_v2_missing_data_operations.py`.",
    ]
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _classify(
    *,
    path: str,
    line: int,
    function: str,
    operation: str,
    code: str,
    callsite_fingerprint: str,
    node: ast.Call,
) -> ClassificationResult:
    compact = " ".join(code.split()).lower()
    if operation == "bfill":
        return _classification(
            "PROHIBITED_BACKWARD_FILL",
            "critical",
            False,
            "Backward fill can copy a future observation into an earlier date.",
            "Remove from research inputs or prove it is isolated display-only logic.",
        )
    if operation == "ffill":
        bounded = _has_explicit_bounded_forward_fill_limit(
            node,
            path=path,
            line=line,
            function=function,
            fingerprint=callsite_fingerprint,
        )
        return _classification(
            "BOUNDED_FORWARD_FILL" if bounded else "UNBOUNDED_FORWARD_FILL",
            "medium" if bounded else "high",
            bounded,
            (
                "Forward fill is restricted to an explicit finite gap."
                if bounded
                else "An unbounded stale value can survive an arbitrary data outage."
            ),
            "Retain an explicit finite limit and let unresolved values remain missing.",
        )
    if operation == "interpolate":
        return _classification(
            "PROHIBITED_FUTURE_AWARE_INTERPOLATION",
            "critical",
            False,
            "Interpolation can use a future endpoint to manufacture an earlier value.",
            "Remove from research inputs; use bounded past-only carry or leave missing.",
        )
    if operation == "nan_to_num":
        return _classification(
            "REVIEW_REQUIRED_NUMERIC_ZERO_FILL",
            "critical",
            False,
            "nan_to_num replaces missing numerical evidence, with zero as its default.",
            "Replace with explicit rejection or an exact reviewed structural policy.",
        )
    if operation == "combine_first":
        return _classification(
            "REVIEW_REQUIRED_FALLBACK_IMPUTATION",
            "high",
            False,
            "combine_first can silently substitute a secondary data source.",
            "Document source priority, temporal validity, units, and exact reviewed call site.",
        )
    if operation == "fillna":
        fill_kind = _fill_value_kind(node)
        if fill_kind == "zero":
            approved = _zero_fill_callsite_is_approved(
                path=path,
                line=line,
                function=function,
                fingerprint=callsite_fingerprint,
            )
            return _classification(
                (
                    "STRUCTURAL_ZERO_ALIGNMENT"
                    if approved
                    else "REVIEW_REQUIRED_NUMERIC_ZERO_FILL"
                ),
                "medium" if approved else "critical",
                approved,
                (
                    "Zero represents an absent structural weight/score/count or a "
                    "validation/display sentinel at an exact reviewed call site, "
                    "not a selected asset return."
                    if approved
                    else "The numeric zero-fill call site is not in the reviewed allowlist."
                ),
                (
                    "Keep the selected-return path under complete-weight checks."
                    if approved
                    else "Replace with explicit rejection or document a reviewed non-return meaning."
                ),
            )
        if fill_kind in {"numeric", "numeric_expression", "unknown"}:
            approved = _numeric_fill_callsite_is_approved(
                path=path,
                line=line,
                function=function,
                fingerprint=callsite_fingerprint,
            )
            return _classification(
                (
                    "REVIEWED_NUMERIC_IMPUTATION"
                    if approved
                    else "NUMERIC_IMPUTATION_REQUIRES_REVIEW"
                ),
                "high" if approved else "critical",
                approved,
                (
                    "The exact numerical imputation has a reviewed financial or "
                    "statistical meaning and is bound to this AST call site."
                    if approved
                    else "A numerical value or expression replaces missing evidence "
                    "without an exact reviewed call-site approval."
                ),
                (
                    "Retain the exact allowlist rationale and regression coverage."
                    if approved
                    else "Reject, remove, or add an exact methodology-backed allowlist entry."
                ),
            )
        if fill_kind == "missing_sentinel":
            return _classification(
                "EXPLICIT_MISSING_SENTINEL",
                "low",
                True,
                "The operation preserves missingness using an explicit missing sentinel.",
                "Do not replace the sentinel with a numerical estimate implicitly.",
            )
        return _classification(
            "EXPLICIT_LABEL_OR_BOOLEAN_FILL",
            "low",
            True,
            "The fill supplies an explicit metadata label, Boolean state or non-return default.",
            "Do not reuse the operation on return observations.",
        )
    if operation == "dropna":
        return _classification(
            "COMPLETE_CASE_SAMPLE_REDUCTION",
            "medium",
            True,
            "Invalid or unavailable rows are removed rather than fabricated.",
            "Persist observation counts, common dates and coverage after removal.",
        )
    if operation == "reindex":
        has_zero = _reindex_uses_zero_fill(node)
        approved = bool(
            has_zero
            and _zero_fill_callsite_is_approved(
                path=path,
                line=line,
                function=function,
                fingerprint=callsite_fingerprint,
            )
        )
        return _classification(
            (
                "STRUCTURAL_ZERO_ALIGNMENT"
                if approved
                else (
                    "REVIEW_REQUIRED_NUMERIC_ZERO_FILL"
                    if has_zero
                    else "INDEX_ALIGNMENT"
                )
            ),
            "medium" if approved else ("critical" if has_zero else "low"),
            approved if has_zero else True,
            (
                "Absent holdings are structural zero positions at an exact reviewed call site."
                if approved
                else (
                    "A zero-valued reindex fill is not bound to the reviewed call-site allowlist."
                    if has_zero
                    else "Labels are aligned without asserting that missing observations are zero."
                )
            ),
            (
                "Retain exact allowlist evidence and test the structural-weight meaning."
                if approved
                else (
                    "Reject or add an exact methodology-backed structural-zero approval."
                    if has_zero
                    else "Validate selected tickers, common dates and post-alignment missingness."
                )
            ),
        )
    return _classification(
        "RELATIONAL_ALIGNMENT",
        "medium",
        True,
        "Evidence tables are aligned by declared keys.",
        "Validate key uniqueness, cardinality, unmatched rows and run identity.",
    )


def _normalized_operation(operation: str, code: str) -> str:
    compact = " ".join(code.split()).lower()
    if operation != "fillna":
        return operation
    if any(
        token in compact
        for token in (
            "method='bfill'",
            'method="bfill"',
            "method='backfill'",
            'method="backfill"',
        )
    ):
        return "bfill"
    if any(
        token in compact
        for token in (
            "method='ffill'",
            'method="ffill"',
            "method='pad'",
            'method="pad"',
        )
    ):
        return "ffill"
    return operation


def _classification(
    classification: str,
    risk_level: str,
    approved: bool,
    reason: str,
    required_control: str,
) -> ClassificationResult:
    return {
        "classification": classification,
        "risk_level": risk_level,
        "status": "reviewed" if approved else "rejected_until_fixed",
        "approved": approved,
        "reason": reason,
        "required_control": required_control,
    }


def _has_explicit_bounded_forward_fill_limit(
    node: ast.Call,
    *,
    path: str,
    line: int,
    function: str,
    fingerprint: str,
) -> bool:
    limit = next(
        (keyword.value for keyword in node.keywords if keyword.arg == "limit"),
        None,
    )
    if limit is None:
        return False
    literal = _numeric_literal(limit)
    if literal is not None:
        return bool(math.isfinite(literal) and literal > 0)
    if isinstance(limit, ast.Constant):
        return False
    return _forward_fill_callsite_is_approved(
        path=path,
        line=line,
        function=function,
        fingerprint=fingerprint,
    )


def _reindex_uses_zero_fill(node: ast.Call) -> bool:
    value = next(
        (keyword.value for keyword in node.keywords if keyword.arg == "fill_value"),
        None,
    )
    literal = _numeric_literal(value)
    return literal == 0.0 if literal is not None else False


def _numeric_literal(node: ast.AST | None) -> float | None:
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None
    if isinstance(node, ast.UnaryOp) and isinstance(
        node.operand,
        ast.Constant,
    ):
        value = node.operand.value
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        if isinstance(node.op, ast.USub):
            return -float(value)
        if isinstance(node.op, ast.UAdd):
            return float(value)
    return None


def _fill_value_kind(node: ast.Call) -> str:
    value: ast.AST | None = node.args[0] if node.args else None
    for keyword in node.keywords:
        if keyword.arg == "value":
            value = keyword.value
            break
    if value is None:
        return "unknown"
    if isinstance(value, ast.Constant):
        if value.value is None:
            return "missing_sentinel"
        if isinstance(value.value, bool):
            return "label_or_boolean"
        if isinstance(value.value, str):
            return "label_or_boolean"
        if isinstance(value.value, (int, float, complex)):
            return "zero" if value.value == 0 else "numeric"
        return "unknown"
    if isinstance(value, ast.UnaryOp) and isinstance(
        value.operand,
        ast.Constant,
    ):
        operand = value.operand.value
        if isinstance(operand, (int, float, complex)) and not isinstance(
            operand,
            bool,
        ):
            signed = -operand if isinstance(value.op, ast.USub) else operand
            return "zero" if signed == 0 else "numeric"
    if isinstance(value, ast.Attribute) and value.attr in {"NA", "NaT", "nan"}:
        return "missing_sentinel"
    if _looks_like_text_expression(value):
        return "label_or_boolean"
    if isinstance(value, ast.Dict):
        kinds = {
            _fill_value_kind(
                ast.Call(
                    func=ast.Name(id="fillna"),
                    args=[item],
                    keywords=[],
                )
            )
            for item in value.values
            if item is not None
        }
        if kinds.issubset({"label_or_boolean", "missing_sentinel"}):
            return "label_or_boolean"
        if kinds == {"zero"}:
            return "zero"
        return "numeric_expression"
    return "numeric_expression"


def _looks_like_text_expression(node: ast.AST) -> bool:
    text_tokens = {
        "label",
        "name",
        "ticker",
        "symbol",
        "status",
        "reason",
        "warning",
        "source",
        "unavailable",
        "missing_value",
    }
    if isinstance(node, ast.Name):
        name = node.id.lower()
        return name in text_tokens or any(token in name for token in text_tokens)
    if isinstance(node, ast.Subscript):
        slice_node = node.slice
        return bool(
            isinstance(slice_node, ast.Constant)
            and isinstance(slice_node.value, str)
            and any(token in slice_node.value.lower() for token in text_tokens)
        )
    return False


def _callsite_fingerprint(node: ast.Call) -> str:
    payload = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


def _source_tree_hash(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"source-{digest.hexdigest()[:24]}"


def _zero_fill_callsite_is_approved(
    *,
    path: str,
    line: int,
    function: str,
    fingerprint: str,
) -> bool:
    if not ZERO_FILL_ALLOWLIST.exists():
        return False
    frame = pd.read_csv(ZERO_FILL_ALLOWLIST, dtype=str).fillna("")
    required = {"path", "line", "function", "callsite_fingerprint", "approved_meaning"}
    if not required.issubset(frame.columns):
        return False
    matches = (
        frame["path"].eq(path)
        & frame["line"].eq(str(int(line)))
        & frame["function"].eq(function)
        & frame["callsite_fingerprint"].eq(fingerprint)
        & frame["approved_meaning"].str.strip().ne("")
    )
    return bool(matches.any())


def _numeric_fill_callsite_is_approved(
    *,
    path: str,
    line: int,
    function: str,
    fingerprint: str,
) -> bool:
    if not NUMERIC_FILL_ALLOWLIST.exists():
        return False
    frame = pd.read_csv(NUMERIC_FILL_ALLOWLIST, dtype=str).fillna("")
    required = {"path", "line", "function", "callsite_fingerprint", "approved_meaning"}
    if not required.issubset(frame.columns):
        return False
    matches = (
        frame["path"].eq(path)
        & frame["line"].eq(str(int(line)))
        & frame["function"].eq(function)
        & frame["callsite_fingerprint"].eq(fingerprint)
        & frame["approved_meaning"].str.strip().ne("")
    )
    return bool(matches.any())


def _forward_fill_callsite_is_approved(
    *,
    path: str,
    line: int,
    function: str,
    fingerprint: str,
) -> bool:
    if not FORWARD_FILL_ALLOWLIST.exists():
        return False
    frame = pd.read_csv(FORWARD_FILL_ALLOWLIST, dtype=str).fillna("")
    required = {
        "path",
        "line",
        "function",
        "callsite_fingerprint",
        "approved_meaning",
    }
    if not required.issubset(frame.columns):
        return False
    matches = (
        frame["path"].eq(path)
        & frame["line"].eq(str(int(line)))
        & frame["function"].eq(function)
        & frame["callsite_fingerprint"].eq(fingerprint)
        & frame["approved_meaning"].str.strip().ne("")
    )
    return bool(matches.any())


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    selected = frame[[column for column in columns if column in frame]].copy()
    selected = selected.fillna("").astype(str)
    header = "| " + " | ".join(selected.columns) + " |"
    divider = "|" + "|".join(["---"] * len(selected.columns)) + "|"
    rows = [
        "| "
        + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in row)
        + " |"
        for row in selected.itertuples(index=False, name=None)
    ]
    return "\n".join([header, divider, *rows])


def main() -> int:
    frame = scan_repository(ROOT)
    write_audit_outputs(frame)
    unapproved = int((~frame["approved"].astype(bool)).sum())
    print(f"missing_data_operations={len(frame)}")
    print(f"missing_data_unapproved={unapproved}")
    print(f"missing_data_audit_csv={OUTPUT_CSV}")
    print(f"missing_data_audit_doc={OUTPUT_MD}")
    return 0 if unapproved == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
