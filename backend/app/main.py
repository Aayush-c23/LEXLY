"""
FastAPI Application Entry Point for LEXLY.

Manages application lifespan:
1. Initializes asyncpg PostgreSQL connection pool.
2. Loads statutory corpus from Supabase or static seed into zero-latency in-memory cache.
3. Configures API routing, middleware, and health monitoring.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.database import close_db_pool, get_pool, init_db_pool
from backend.app.engine.corpus_cache import (
    get_cached_matrix,
    is_cache_initialized,
    load_corpus_from_seed,
    load_corpus_to_memory,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lexly.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager that handles startup and shutdown tasks.
    """
    logger.info("Starting up LEXLY backend application...")
    
    # 1. Initialize asyncpg connection pool
    pool = None
    try:
        pool = await init_db_pool()
    except Exception as exc:
        logger.error(f"Database connection could not be established during startup: {exc}")

    # 2. Load corpus to in-memory cache
    if pool is not None:
        try:
            await load_corpus_to_memory(pool)
        except Exception as exc:
            logger.error(f"Error loading statutory corpus during startup: {exc}")
            load_corpus_from_seed()
    else:
        logger.info("Initializing in-memory corpus from static seed data.")
        load_corpus_from_seed()

    yield

    # 3. Graceful shutdown
    logger.info("Shutting down LEXLY backend application...")
    await close_db_pool()


# Initialize FastAPI instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(
    "/health",
    tags=["System"],
    status_code=status.HTTP_200_OK,
    summary="Application Health & In-Memory Cache Status",
)
async def health_check() -> Dict[str, Any]:
    """
    Returns application liveness, database pool connectivity, and
    in-memory statutory corpus cache status.
    """
    pool = get_pool()
    db_connected = False

    if pool is not None:
        try:
            async with pool.acquire() as conn:
                res = await conn.fetchval("SELECT 1;")
                db_connected = bool(res == 1)
        except Exception as exc:
            logger.warning(f"Health check database ping failed: {exc}")
            db_connected = False

    matrix = get_cached_matrix()
    total_cached = len(matrix)

    return {
        "status": "ok",
        "db_connected": db_connected,
        "matrix_cached": is_cache_initialized(),
        "total_cached_provisions": total_cached,
    }
