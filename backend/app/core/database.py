"""
Asynchronous PostgreSQL Connection Pool manager using asyncpg.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import asyncpg
from backend.app.core.config import settings

logger = logging.getLogger("lexly.database")

# Global connection pool reference
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> asyncpg.Pool:
    """
    Initializes and returns the global asyncpg connection pool.
    """
    global _pool
    if _pool is not None:
        return _pool

    logger.info("Initializing asyncpg database connection pool...")
    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            timeout=settings.DB_POOL_TIMEOUT,
            command_timeout=60.0,
            statement_cache_size=0,
        )
        logger.info("Database connection pool established successfully.")
        return _pool
    except Exception as exc:
        logger.error(f"Failed to initialize database connection pool: {exc}")
        raise


async def close_db_pool() -> None:
    """
    Gracefully terminates the global asyncpg connection pool.
    """
    global _pool
    if _pool is not None:
        logger.info("Closing database connection pool...")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


def get_pool() -> Optional[asyncpg.Pool]:
    """
    Returns the current active pool instance, if initialized.
    """
    return _pool


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Async context manager dependency that acquires a connection from the pool
    and safely releases it back upon completion.
    """
    if _pool is None:
        raise RuntimeError("Database connection pool is not initialized. Call init_db_pool() first.")

    async with _pool.acquire() as connection:
        yield connection
