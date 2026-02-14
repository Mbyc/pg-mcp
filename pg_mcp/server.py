from __future__ import annotations

import logging
from typing import Literal

import asyncpg
from fastmcp import FastMCP
from pg_mcp.config import settings
from pg_mcp.db.registry import PoolRegistry
from pg_mcp.db.schema_cache import SchemaCache
from pg_mcp.llm.client import OpenAIClient
from pg_mcp.services.query_service import QueryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pg-mcp")

# Create FastMCP instance
mcp = FastMCP("pg-mcp")

# Component Factory for Registry
async def pool_factory(db_name: str) -> asyncpg.Pool:
    db_config = next((db for db in settings.databases if db.name == db_name), None)
    if not db_config:
        # Check if we can fall back to env-based single DB if no list provided
        # But per PRD/Design, we expect a configured list or specific envs
        raise ValueError(f"Database configuration for '{db_name}' not found in PGMCP_DATABASES")
    
    logger.info(f"Initializing connection pool for database: {db_name}")
    return await asyncpg.create_pool(
        dsn=db_config.dsn,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
        timeout=10.0
    )

# Singleton components
pool_registry = PoolRegistry(
    pool_factory=pool_factory,
    idle_timeout_s=settings.pool_idle_timeout_s
)

schema_cache = SchemaCache(refresh_interval_s=settings.schema_refresh_interval_s)
llm_client = OpenAIClient()

query_service = QueryService(
    pool_registry=pool_registry,
    schema_cache=schema_cache,
    llm_client=llm_client
)

@mcp.tool()
async def query(
    natural_query: str,
    database: str | None = None,
    mode: Literal["execute", "sql_only"] = "execute",
    validate_meaning: bool | None = None
) -> dict:
    """
    Query PostgreSQL databases using natural language.
    
    Args:
        natural_query: The natural language description of your query.
        database: Optional target database name.
        mode: 'execute' (default) to run the query, or 'sql_only' to just generate the SQL.
        validate_meaning: Optional flag to enable/disable LLM-based result validation.
    """
    try:
        logger.info(f"Received query: {natural_query} (db={database}, mode={mode})")
        return await query_service.query(
            natural_query=natural_query,
            database_name=database,
            mode=mode,
            validate_meaning=validate_meaning
        )
    except Exception as e:
        logger.exception(f"Error executing query: {str(e)}")
        return {
            "status": "error",
            "error_type": e.__class__.__name__,
            "message": str(e)
        }

def main():
    """Main entry point for the MCP server."""
    logger.info("Starting pg-mcp server via FastMCP...")
    mcp.run()

if __name__ == "__main__":
    main()
