from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional, Protocol

from pg_mcp.models.schema import DatabaseSchema

logger = logging.getLogger(__name__)

class SchemaIntrospectorProtocol(Protocol):
    async def __call__(self, database_name: str) -> DatabaseSchema: ...

class SchemaCache:
    """
    Manages schema caching with background refresh and atomic updates.
    """
    def __init__(self, refresh_interval_s: int) -> None:
        self._refresh_interval_s = refresh_interval_s
        self._cache: Dict[str, DatabaseSchema] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._refreshing: Dict[str, bool] = {}
        self._global_lock = asyncio.Lock()

    async def get_schema(self, database_name: str) -> Optional[DatabaseSchema]:
        """Returns the cached schema if available."""
        return self._cache.get(database_name)

    async def ensure_loaded(
        self, 
        database_name: str, 
        introspector: SchemaIntrospectorProtocol
    ) -> DatabaseSchema:
        """
        Ensures schema is loaded. If not present, performs initial load.
        If expired, triggers background refresh.
        """
        lock = await self._get_lock(database_name)
        
        async with lock:
            schema = self._cache.get(database_name)
            
            # Initial load
            if schema is None:
                logger.info(f"Performing initial schema load for database: {database_name}")
                schema = await introspector(database_name)
                self._cache[database_name] = schema
                return schema

            # Check for expiration and trigger background refresh
            if self._is_expired(schema) and not self._refreshing.get(database_name):
                self._refreshing[database_name] = True
                # Trigger background refresh without awaiting it
                asyncio.create_task(self._background_refresh(database_name, introspector))
                logger.info(f"Triggered background schema refresh for database: {database_name}")

            return schema

    async def _background_refresh(
        self, 
        database_name: str, 
        introspector: SchemaIntrospectorProtocol
    ) -> None:
        """Performs schema refresh in the background and updates atomically."""
        try:
            # We don't use the per-db lock here to avoid blocking readers,
            # but we use a local check to avoid concurrent refreshes.
            new_schema = await introspector(database_name)
            self._cache[database_name] = new_schema
            logger.info(f"Successfully refreshed schema for database: {database_name}")
        except Exception:
            logger.exception(f"Failed to refresh schema for database: {database_name}")
        finally:
            self._refreshing[database_name] = False

    def _is_expired(self, schema: DatabaseSchema) -> bool:
        return (time.time() - schema.loaded_at_epoch_s) > self._refresh_interval_s

    async def _get_lock(self, database_name: str) -> asyncio.Lock:
        async with self._global_lock:
            if database_name not in self._locks:
                self._locks[database_name] = asyncio.Lock()
            return self._locks[database_name]
