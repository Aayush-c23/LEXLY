"""
Core in-memory cache for statutory provisions, facts matrix, hierarchy relations,
and question templates to enable zero-latency, sub-50ms constraint satisfaction evaluation.
"""

import logging
from typing import Dict, List, Optional, Tuple
import asyncpg

logger = logging.getLogger("lexly.corpus_cache")

# Global in-memory data structures
# 1. Provision facts matrix: provision_id -> {fact_key: expected_value ('TRUE' | 'FALSE')}
PROVISION_FACTS_MATRIX: Dict[int, Dict[str, str]] = {}

# 2. Provision hierarchy graph: parent_provision_id -> [(child_provision_id, relation_type)]
HIERARCHY_GRAPH: Dict[int, List[Tuple[int, str]]] = {}

# 3. Fact questions catalog: fact_key -> {locale -> question_text}
FACT_QUESTION_CATALOG: Dict[str, Dict[str, str]] = {}

# Flag indicating cache status
_CACHE_INITIALIZED: bool = False


async def load_corpus_to_memory(pool: asyncpg.Pool) -> None:
    """
    Reads all statutory provision facts, hierarchies, and multilingual question templates
    from the database and populates thread-safe in-memory dictionaries.

    Parameters
    ----------
    pool : asyncpg.Pool
        Active PostgreSQL connection pool.
    """
    global PROVISION_FACTS_MATRIX, HIERARCHY_GRAPH, FACT_QUESTION_CATALOG, _CACHE_INITIALIZED

    logger.info("Loading statutory corpus into memory from database...")

    async with pool.acquire() as conn:
        # Query 1: Read all records from provision_facts
        # Schema: provision_id (int), fact_key (varchar), expected_value (varchar)
        try:
            facts_rows = await conn.fetch(
                """
                SELECT provision_id, fact_key, expected_value
                FROM provision_facts
                ORDER BY provision_id, fact_key;
                """
            )
            matrix: Dict[int, Dict[str, str]] = {}
            for row in facts_rows:
                pid = int(row["provision_id"])
                f_key = str(row["fact_key"])
                exp_val = str(row["expected_value"])
                if pid not in matrix:
                    matrix[pid] = {}
                matrix[pid][f_key] = exp_val
            PROVISION_FACTS_MATRIX = matrix
            logger.info(f"Cached {len(PROVISION_FACTS_MATRIX)} provisions in facts matrix.")
        except Exception as exc:
            logger.warning(f"Could not load provision_facts (table may not be seeded yet): {exc}")
            PROVISION_FACTS_MATRIX = {}

        # Query 2: Read all records from provision_hierarchy
        # Schema: parent_provision_id (int), child_provision_id (int), relation_type (varchar)
        try:
            hierarchy_rows = await conn.fetch(
                """
                SELECT parent_provision_id, child_provision_id, relation_type
                FROM provision_hierarchy
                ORDER BY parent_provision_id;
                """
            )
            hierarchy: Dict[int, List[Tuple[int, str]]] = {}
            for row in hierarchy_rows:
                parent_id = int(row["parent_provision_id"])
                child_id = int(row["child_provision_id"])
                rel_type = str(row["relation_type"])
                if parent_id not in hierarchy:
                    hierarchy[parent_id] = []
                hierarchy[parent_id].append((child_id, rel_type))
            HIERARCHY_GRAPH = hierarchy
            logger.info(f"Cached {len(HIERARCHY_GRAPH)} parent nodes in hierarchy graph.")
        except Exception as exc:
            logger.warning(f"Could not load provision_hierarchy: {exc}")
            HIERARCHY_GRAPH = {}

        # Query 3: Read all records from fact_questions
        # Schema: fact_key (varchar), locale (varchar), question_text (text)
        try:
            question_rows = await conn.fetch(
                """
                SELECT fact_key, locale, question_text
                FROM fact_questions;
                """
            )
            catalog: Dict[str, Dict[str, str]] = {}
            for row in question_rows:
                f_key = str(row["fact_key"])
                loc = str(row["locale"]) if "locale" in row else "en"
                q_text = str(row["question_text"])
                if f_key not in catalog:
                    catalog[f_key] = {}
                catalog[f_key][loc] = q_text
            FACT_QUESTION_CATALOG = catalog
            logger.info(f"Cached {len(FACT_QUESTION_CATALOG)} fact questions in question catalog.")
        except Exception as exc:
            logger.warning(f"Could not load fact_questions: {exc}")
            FACT_QUESTION_CATALOG = {}

    _CACHE_INITIALIZED = True
    logger.info("Corpus caching complete.")


def is_cache_initialized() -> bool:
    """Returns True if the in-memory cache has been populated."""
    return _CACHE_INITIALIZED


def get_cached_matrix() -> Dict[int, Dict[str, str]]:
    """Returns the immutable provision facts matrix."""
    return PROVISION_FACTS_MATRIX


def get_cached_hierarchy() -> Dict[int, List[Tuple[int, str]]]:
    """Returns the provision hierarchy graph."""
    return HIERARCHY_GRAPH


def get_cached_questions() -> Dict[str, Dict[str, str]]:
    """Returns the multilingual fact questions catalog."""
    return FACT_QUESTION_CATALOG
