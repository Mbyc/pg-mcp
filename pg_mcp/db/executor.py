from __future__ import annotations

import logging
import time
from typing import Any

import asyncpg
from pg_mcp.config import settings

logger = logging.getLogger(__name__)

class QueryExecutor:
    """Safely executes PostgreSQL queries and formats results."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def execute_query(
        self, 
        sql: str, 
        max_rows: int = settings.max_rows,
        statement_timeout_ms: int = settings.statement_timeout_ms
    ) -> dict[str, Any]:
        """
        Executes a query with strict resource limits.
        Uses EXPLAIN for initial validation.
        Wrap SQL in a subquery to safely apply LIMIT.
        """
        start_time = time.monotonic()
        
        # Safely wrap the query to apply our own LIMIT for result preview
        # Using a subquery is the most reliable way to enforce a row limit on any valid SELECT
        wrapped_sql = f"SELECT * FROM ({sql.rstrip(';')}) AS __mcp_query_preview__ LIMIT {max_rows + 1}"

        async with self.pool.acquire() as conn:
            # 1. Validation using EXPLAIN
            try:
                await conn.execute(f"EXPLAIN {sql}")
            except asyncpg.PostgresError as e:
                logger.error(f"SQL validation via EXPLAIN failed: {e}")
                raise

            # 2. Set session-level timeout
            await conn.execute(f"SET LOCAL statement_timeout = {statement_timeout_ms}")
            
            # 3. Execute and fetch limited rows
            rows = await conn.fetch(wrapped_sql)
            
            execution_time_ms = int((time.monotonic() - start_time) * 1000)
            
            truncated = len(rows) > max_rows
            final_rows = [dict(r) for r in rows[:max_rows]]
            
            return {
                "rows": final_rows,
                "row_count": len(final_rows),
                "truncated": truncated,
                "execution_time_ms": execution_time_ms
            }
