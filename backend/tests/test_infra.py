"""
Unit tests for FastAPI Health Endpoint and In-Memory Corpus Cache (Phase 1).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import Settings
from backend.app.engine import corpus_cache
from backend.app.main import app


@pytest.fixture
def test_client():
    """Provides a synchronous FastAPI test client with managed lifespan."""
    with TestClient(app) as client:
        yield client


def test_config_settings_validation():
    """Ensures DATABASE_URL validation handles asyncpg scheme formats."""
    # Standard format
    s1 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s1.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"

    # Asyncpg prefix conversion
    s2 = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert s2.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"

    # Invalid scheme
    with pytest.raises(ValueError):
        Settings(DATABASE_URL="mysql://user:pass@localhost:3306/db")


def test_health_endpoint(test_client):
    """Verifies that GET /health returns expected schema and fields."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "db_connected" in data
    assert "matrix_cached" in data
    assert "total_cached_provisions" in data


@pytest.mark.asyncio
async def test_load_corpus_to_memory_mocked():
    """Tests that load_corpus_to_memory populates in-memory dictionaries accurately."""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    # Configure mock responses for the 3 queries
    mock_conn.fetch.side_effect = [
        # Query 1: provision_facts
        [
            {"provision_id": 101, "fact_key": "weapon", "expected_value": "TRUE"},
            {"provision_id": 101, "fact_key": "hurt", "expected_value": "TRUE"},
            {"provision_id": 102, "fact_key": "dwelling", "expected_value": "TRUE"},
        ],
        # Query 2: provision_hierarchy
        [
            {"parent_provision_id": 101, "child_provision_id": 102, "relation_type": "AGGRAVATED_FORM"}
        ],
        # Query 3: fact_questions
        [
            {"fact_key": "weapon", "locale": "en", "question_text": "Was a deadly weapon used?"},
            {"fact_key": "weapon", "locale": "hi", "question_text": "क्या घातक हथियार का प्रयोग किया गया था?"},
        ],
    ]

    # Context manager setup for pool.acquire()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Execute cache loader
    await corpus_cache.load_corpus_to_memory(mock_pool)

    # Assert matrix population
    matrix = corpus_cache.get_cached_matrix()
    assert 101 in matrix
    assert matrix[101]["weapon"] == "TRUE"
    assert matrix[101]["hurt"] == "TRUE"
    assert matrix[102]["dwelling"] == "TRUE"

    # Assert hierarchy graph
    hierarchy = corpus_cache.get_cached_hierarchy()
    assert 101 in hierarchy
    assert hierarchy[101] == [(102, "AGGRAVATED_FORM")]

    # Assert question catalog
    questions = corpus_cache.get_cached_questions()
    assert "weapon" in questions
    assert questions["weapon"]["en"] == "Was a deadly weapon used?"
    assert questions["weapon"]["hi"] == "क्या घातक हथियार का प्रयोग किया गया था?"
    assert corpus_cache.is_cache_initialized() is True
