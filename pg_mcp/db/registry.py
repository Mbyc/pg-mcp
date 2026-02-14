from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import asyncpg


@dataclass(frozen=True)
class PoolHandle:
    pool: asyncpg.Pool
    last_used_monotonic: float


class PoolRegistry:
    def __init__(
        self,
        *,
        pool_factory: Callable[[str], Awaitable[asyncpg.Pool]],
        idle_timeout_s: int,
    ) -> None:
        self._pool_factory = pool_factory
        self._idle_timeout_s = idle_timeout_s
        self._lock = asyncio.Lock()
        self._pools: dict[str, PoolHandle] = {}

    async def get_pool(self, database_name: str) -> asyncpg.Pool:
        async with self._lock:
            handle = self._pools.get(database_name)
            if handle is None:
                pool = await self._pool_factory(database_name)
                self._pools[database_name] = PoolHandle(pool=pool, last_used_monotonic=time.monotonic())
                return pool

            self._pools[database_name] = PoolHandle(pool=handle.pool, last_used_monotonic=time.monotonic())
            return handle.pool

    async def close_idle_pools(self) -> None:
        now = time.monotonic()
        async with self._lock:
            to_close: list[tuple[str, asyncpg.Pool]] = []
            for name, handle in list(self._pools.items()):
                if now - handle.last_used_monotonic >= self._idle_timeout_s:
                    to_close.append((name, handle.pool))
                    del self._pools[name]

        for _, pool in to_close:
            await pool.close()

    async def close_all(self) -> None:
        async with self._lock:
            pools = [h.pool for h in self._pools.values()]
            self._pools.clear()
        for pool in pools:
            await pool.close()
