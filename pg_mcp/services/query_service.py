from __future__ import annotations

import logging
from typing import Any, Literal

from pg_mcp.config import settings
from pg_mcp.db.executor import QueryExecutor
from pg_mcp.db.registry import PoolRegistry
from pg_mcp.db.schema_cache import SchemaCache
from pg_mcp.db.schema_introspect import introspect_schema
from pg_mcp.db.schema_retriever import SchemaRetriever
from pg_mcp.llm.client import OpenAIClient
from pg_mcp.sql.safety import validate_readonly_sql, SqlValidationError

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(
        self,
        pool_registry: PoolRegistry,
        schema_cache: SchemaCache,
        llm_client: OpenAIClient
    ) -> None:
        self.pool_registry = pool_registry
        self.schema_cache = schema_cache
        self.llm_client = llm_client

    async def query(
        self,
        natural_query: str,
        database_name: str | None = None,
        mode: Literal["execute", "sql_only"] = "execute",
        validate_meaning: bool | None = None
    ) -> dict[str, Any]:
        # 1. Select database
        db_name = database_name or settings.default_database
        if not db_name:
            available = [db.name for db in settings.databases]
            if not available:
                 raise ValueError("No databases configured in PG_MCP_DATABASES")
            raise ValueError(f"Database not specified. Available: {available}")

        # 2. Get/Refresh Schema
        pool = await self.pool_registry.get_pool(db_name)
        
        async def _introspect(name: str):
            async with pool.acquire() as conn:
                return await introspect_schema(conn=conn, database_name=name)

        schema = await self.schema_cache.ensure_loaded(db_name, _introspect)
        
        # 3. Retrieve relevant tables (RAG-lite)
        retriever = SchemaRetriever(schema)
        relevant_tables = retriever.retrieve_relevant_tables(natural_query)
        
        # 4. Generate SQL (Initial Attempt)
        gen_res = await self.llm_client.generate_sql(natural_query, relevant_tables)
        
        if gen_res.clarifying_questions:
            return {
                "status": "clarification_needed",
                "questions": gen_res.clarifying_questions,
                "assumptions": gen_res.assumptions
            }

        # 5. Safety Validation
        self._validate_sql(gen_res.sql)

        # 6. Response Base
        response = {
            "database": db_name,
            "sql": gen_res.sql,
            "explanation": gen_res.explanation,
            "assumptions": gen_res.assumptions,
            "mode": mode
        }

        if mode == "sql_only":
            return response

        # 7. Execution with 1-time Auto-fix
        executor = QueryExecutor(pool)
        try:
            exec_res = await executor.execute_query(gen_res.sql)
            response.update(exec_res)
        except Exception as e:
            logger.warning(f"SQL execution failed, attempting 1-time auto-fix. Error: {e}")
            
            # Phase 5C: Auto-fix attempt
            fixed_gen_res = await self.llm_client.generate_sql(
                natural_query, 
                relevant_tables, 
                error_context=str(e)
            )
            
            # Re-validate fixed SQL
            self._validate_sql(fixed_gen_res.sql)
            
            # Re-execute fixed SQL
            exec_res = await executor.execute_query(fixed_gen_res.sql)
            
            # Update response with fixed info
            response.update({
                "sql": fixed_gen_res.sql,
                "explanation": f"Fixed SQL after error. {fixed_gen_res.explanation}",
                "auto_fixed": True,
                "original_error": str(e)
            })
            response.update(exec_res)

        # 8. Meaning Validation (Optional)
        should_validate = validate_meaning if validate_meaning is not None else settings.meaning_validation_enabled
        if should_validate and mode == "execute" and "rows" in response:
            meaning_res = await self.llm_client.validate_meaning(
                natural_query, response["sql"], response["rows"]
            )
            response["meaning_validation"] = {
                "matches": meaning_res.matches_intent,
                "reason": meaning_res.reason
            }

        return response

    def _validate_sql(self, sql: str) -> None:
        validation = validate_readonly_sql(
            sql, 
            disallowed_functions=settings.disallowed_functions
        )
        if not validation.is_readonly:
            raise SqlValidationError(validation.blocked_reasons)
