from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class SqlValidationResult:
    is_readonly: bool
    blocked_reasons: tuple[str, ...]


class SqlValidationError(ValueError):
    def __init__(self, reasons: Sequence[str]) -> None:
        super().__init__("SQL validation failed")
        self.reasons = tuple(reasons)


def _normalize_identifier(name: str) -> str:
    return name.strip().strip('"').lower()


def validate_readonly_sql(
    sql: str,
    *,
    dialect: str = "postgres",
    allow_multi_statement: bool = False,
    disallowed_functions: Iterable[str] = (),
) -> SqlValidationResult:
    disallowed = {_normalize_identifier(f) for f in disallowed_functions}

    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as e:  # noqa: BLE001
        raise SqlValidationError([f"parse_error: {e}"]) from e

    reasons: list[str] = []

    if not allow_multi_statement and len(statements) != 1:
        reasons.append("multi_statement_not_allowed")

    # Safely get expression classes to support different sqlglot versions
    def _is_instance(node: exp.Expression, class_names: Iterable[str]) -> bool:
        classes = []
        for name in class_names:
            cls = getattr(exp, name, None)
            if cls is not None:
                classes.append(cls)
        return isinstance(node, tuple(classes)) if classes else False

    for stmt in statements:
        if isinstance(stmt, exp.Select):
            pass
        elif isinstance(stmt, exp.With):
            if not isinstance(stmt.this, exp.Select):
                reasons.append("with_must_wrap_select")
        elif isinstance(stmt, exp.Union):
            pass
        else:
            reasons.append(f"statement_not_allowed:{stmt.__class__.__name__}")

        for node in stmt.walk():
            if _is_instance(node, ["Command"]):
                reasons.append("command_not_allowed")

            if _is_instance(node, ["Insert", "Update", "Delete", "Merge"]):
                reasons.append("dml_not_allowed")

            if _is_instance(node, ["Create", "Alter", "Drop", "Truncate"]):
                reasons.append("ddl_not_allowed")

            if _is_instance(node, ["Copy"]):
                reasons.append("copy_not_allowed")

            if _is_instance(node, ["Call", "Do"]):
                reasons.append("call_do_not_allowed")

            if _is_instance(node, ["Set"]):
                reasons.append("set_not_allowed")

            if isinstance(node, exp.Func):
                raw_fname = node.sql(dialect=dialect).split("(")[0].strip()
                normalized_fname = _normalize_identifier(raw_fname)
                parts = normalized_fname.split(".")
                func_only = parts[-1]
                
                if normalized_fname in disallowed or func_only in disallowed:
                    reasons.append(f"disallowed_function:{normalized_fname}")

    is_ok = len(reasons) == 0
    return SqlValidationResult(is_readonly=is_ok, blocked_reasons=tuple(dict.fromkeys(reasons)))
