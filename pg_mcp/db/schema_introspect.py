from __future__ import annotations

from typing import Iterable

import asyncpg

from pg_mcp.models.schema import ColumnSchema, ConstraintSchema, DatabaseSchema, TableSchema


async def introspect_schema(
    *,
    conn: asyncpg.Connection,
    database_name: str,
    exclude_schemas: Iterable[str] = ("pg_catalog", "information_schema"),
) -> DatabaseSchema:
    exclude = tuple(exclude_schemas)

    rows = await conn.fetch(
        """
        SELECT
            c.table_schema,
            c.table_name,
            t.table_type,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema <> ALL($1::text[])
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
        """,
        list(exclude),
    )

    table_map: dict[tuple[str, str], TableSchema] = {}

    def _kind(table_type: str) -> str:
        # information_schema.tables.table_type: BASE TABLE | VIEW | FOREIGN TABLE
        if table_type.upper() == "VIEW":
            return "view"
        return "table"

    for r in rows:
        key = (r["table_schema"], r["table_name"])
        tbl = table_map.get(key)
        if tbl is None:
            tbl = TableSchema(schema_name=r["table_schema"], name=r["table_name"], kind=_kind(r["table_type"]))
            table_map[key] = tbl
        tbl.columns.append(
            ColumnSchema(
                name=r["column_name"],
                data_type=r["data_type"],
                is_nullable=(r["is_nullable"].upper() == "YES"),
                default=r["column_default"],
            )
        )

    constraints = await conn.fetch(
        """
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_name = tc.constraint_name
         AND kcu.table_schema = tc.table_schema
         AND kcu.table_name = tc.table_name
        LEFT JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema <> ALL($1::text[])
          AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
        ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position
        """,
        list(exclude),
    )

    constraint_map: dict[tuple[str, str, str], ConstraintSchema] = {}

    for r in constraints:
        tkey = (r["table_schema"], r["table_name"])
        tbl = table_map.get(tkey)
        if tbl is None:
            continue

        ckey = (r["table_schema"], r["table_name"], r["constraint_name"])
        cs = constraint_map.get(ckey)
        if cs is None:
            foreign_table = None
            if r["foreign_table_name"]:
                foreign_table = f"{r['foreign_table_schema']}.{r['foreign_table_name']}"

            cs = ConstraintSchema(
                name=r["constraint_name"],
                constraint_type=r["constraint_type"],
                columns=[],
                foreign_table=foreign_table,
                foreign_columns=[],
            )
            constraint_map[ckey] = cs
            tbl.constraints.append(cs)

        if r["column_name"] and r["column_name"] not in cs.columns:
            cs.columns.append(r["column_name"])
        if r["foreign_column_name"] and r["foreign_column_name"] not in cs.foreign_columns:
            cs.foreign_columns.append(r["foreign_column_name"])

    return DatabaseSchema(database=database_name, tables=list(table_map.values()), loaded_at_epoch_s=__import__("time").time())
