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

    for stmt in statements:
        if isinstance(stmt, exp.Select):
            pass
        elif isinstance(stmt, exp.With):
            # sqlglot sometimes represents WITH as exp.With wrapping the final statement
            if not isinstance(stmt.this, exp.Select):
                reasons.append("with_must_wrap_select")
        elif isinstance(stmt, exp.Union):
            # UNION of SELECTs is still readonly
            pass
        else:
            reasons.append(f"statement_not_allowed:{stmt.__class__.__name__}")

        for node in stmt.walk():
            if isinstance(node, exp.Command):
                reasons.append("command_not_allowed")

            if isinstance(node, exp.Insert) or isinstance(node, exp.Update) or isinstance(node, exp.Delete) or isinstance(node, exp.Merge):
                reasons.append("dml_not_allowed")

            if isinstance(node, exp.Create) or isinstance(node, exp.Alter) or isinstance(node, exp.Drop) or isinstance(node, exp.Truncate):
                reasons.append("ddl_not_allowed")

            if isinstance(node, exp.Copy):
                reasons.append("copy_not_allowed")

            if isinstance(node, exp.Call) or isinstance(node, exp.Do):
                reasons.append("call_do_not_allowed")

            if isinstance(node, exp.Set):
                reasons.append("set_not_allowed")

            if isinstance(node, exp.Func):
                # Normalize function name including schema if present
                # node.this might be an exp.Identifier or exp.Column/Table
                # node.sql() is the most reliable way to get the full name as written
                raw_fname = node.sql(dialect=dialect).split("(")[0].strip()
                normalized_fname = _normalize_identifier(raw_fname)
                
                # Check both the full name and just the function name part
                parts = normalized_fname.split(".")
                func_only = parts[-1]
                
                if normalized_fname in disallowed or func_only in disallowed:
                    reasons.append(f"disallowed_function:{normalized_fname}")

    is_ok = len(reasons) == 0
    return SqlValidationResult(is_readonly=is_ok, blocked_reasons=tuple(dict.fromkeys(reasons)))
