from __future__ import annotations

import logging
import sys
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
        raise ValueError(f"Database configuration for '{db_name}' not found in PGMCP_DATABASES")
    
    # Debug: log the target DSN (masked password)
    masked_dsn = db_config.dsn
    if "@" in masked_dsn:
        prefix, suffix = masked_dsn.split("@", 1)
        if ":" in prefix:
            base, _ = prefix.rsplit(":", 1)
            masked_dsn = f"{base}:****@{suffix}"
    
    logger.info(f"Initializing connection pool for {db_name} targeting {masked_dsn}")
    
    # Increase timeout to 30s to handle slow local starts or high load
    return await asyncpg.create_pool(
        dsn=db_config.dsn,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
        timeout=30.0,
        ssl=False
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
async def health() -> dict:
    import hashlib

    try:
        db_names = [db.name for db in settings.databases]
    except Exception:
        db_names = []

    db_dsn_endpoints: list[dict[str, str | int]] = []
    for db in settings.databases:
        dsn = db.dsn
        safe_dsn = dsn
        if "@" in safe_dsn:
            prefix, suffix = safe_dsn.split("@", 1)
            if ":" in prefix:
                base, _ = prefix.rsplit(":", 1)
                safe_dsn = f"{base}:****@{suffix}"

        endpoint: dict[str, str | int] = {"name": db.name, "dsn": safe_dsn}
        for key in ("host", "port", "database"):
            try:
                v = asyncpg.connection._parse_connect_dsn(dsn)[key]  # type: ignore[attr-defined]
                if v is not None:
                    endpoint[key] = v
            except Exception:
                pass
        db_dsn_endpoints.append(endpoint)

    fingerprint_src = "|".join(
        [
            f"{db.name}:{db.dsn}" for db in settings.databases
        ]
        + [
            f"default={settings.default_database}",
            f"max_rows={settings.max_rows}",
            f"statement_timeout_ms={settings.statement_timeout_ms}",
            f"allow_multi_statement={settings.allow_multi_statement}",
        ]
    )

    config_fingerprint_sha256 = hashlib.sha256(fingerprint_src.encode("utf-8")).hexdigest()

    return {
        "status": "ok",
        "server": "pg-mcp",
        "tools": ["health", "query"],
        "configured_databases": db_names,
        "default_database": settings.default_database,
        "max_rows": settings.max_rows,
        "statement_timeout_ms": settings.statement_timeout_ms,
        "allow_multi_statement": settings.allow_multi_statement,
        "meaning_validation_enabled": settings.meaning_validation_enabled,
        "db_dsn_endpoints": db_dsn_endpoints,
        "config_fingerprint_sha256": config_fingerprint_sha256,
    }

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
    # Ensure UTF-8 output on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        
    logger.info("Starting pg-mcp server via FastMCP...")
    mcp.run()

if __name__ == "__main__":
    main()
