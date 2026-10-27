"""
Core in-memory cache for statutory provisions, facts matrix, hierarchy relations,
metadata, and question templates to enable zero-latency, sub-50ms constraint satisfaction evaluation.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import asyncpg

logger = logging.getLogger("lexly.corpus_cache")

# Global in-memory data structures
# 1. Provision facts matrix: provision_id -> {fact_key: expected_value ('TRUE' | 'FALSE')}
PROVISION_FACTS_MATRIX: Dict[int, Dict[str, str]] = {}

# 2. Provision hierarchy graph: parent_provision_id -> [(child_provision_id, relation_type)]
HIERARCHY_GRAPH: Dict[int, List[Tuple[int, str]]] = {}

# 3. Fact questions catalog: fact_key -> {locale -> question_text}
FACT_QUESTION_CATALOG: Dict[str, Dict[str, str]] = {}

# 4. Fact question details (observable hints, categories)
FACT_QUESTION_DETAILS: Dict[str, Dict[str, Any]] = {}

# 5. Provision metadata: provision_id -> full provision details dictionary
PROVISION_METADATA: Dict[int, Dict[str, Any]] = {}

# Flag indicating cache status
_CACHE_INITIALIZED: bool = False


def load_corpus_from_seed() -> None:
    """
    Populates in-memory cache from static corpus_data.py.
    Used for local fallback, standalone testing, and offline execution.
    """
    global PROVISION_FACTS_MATRIX, HIERARCHY_GRAPH, FACT_QUESTION_CATALOG, FACT_QUESTION_DETAILS, PROVISION_METADATA, _CACHE_INITIALIZED
    try:
        from backend.app.scripts.corpus_data import (
            FACT_QUESTIONS_DATA,
            HIERARCHY_DATA,
            PROVISIONS_DATA,
        )

        matrix: Dict[int, Dict[str, str]] = {}
        metadata: Dict[int, Dict[str, Any]] = {}
        section_to_id: Dict[str, int] = {}

        for idx, p in enumerate(PROVISIONS_DATA, start=1):
            pid = idx
            section_to_id[p["section_number"]] = pid
            matrix[pid] = {k: v for k, v in p.get("facts", {}).items()}
            metadata[pid] = {
                "id": pid,
                "section_number": p["section_number"],
                "bns_equivalent": p.get("bns_equivalent", f"Section {p['section_number']} BNS"),
                "ipc_equivalent": p.get("ipc_equivalent", ""),
                "title": p.get("title", ""),
                "statutory_text": p.get("statutory_text", ""),
                "plain_summary": p.get("plain_summary", ""),
                "punishment": p.get("punishment", ""),
                "is_cognizable": p.get("is_cognizable", True),
                "is_bailable": p.get("is_bailable", False),
                "compoundable_type": p.get("compoundable_type", "NON_COMPOUNDABLE"),
                "triable_by": p.get("triable_by", "Court of Session"),
            }

        hierarchy: Dict[int, List[Tuple[int, str]]] = {}
        for h in HIERARCHY_DATA:
            p_sec = h["parent_section"]
            c_sec = h["child_section"]
            rel = h["relation_type"]
            p_id = section_to_id.get(p_sec)
            c_id = section_to_id.get(c_sec)
            if p_id and c_id:
                if p_id not in hierarchy:
                    hierarchy[p_id] = []
                hierarchy[p_id].append((c_id, rel))

        catalog: Dict[str, Dict[str, str]] = {}
        details: Dict[str, Dict[str, Any]] = {}
        for q in FACT_QUESTIONS_DATA:
            f_key = q["fact_key"]
            loc = q.get("locale", "en")
            q_text = q["question_text"]
            if f_key not in catalog:
                catalog[f_key] = {}
            catalog[f_key][loc] = q_text

            if f_key not in details:
                details[f_key] = {
                    "observable_proxy_hint": {},
                    "category": q.get("category", "general"),
                }
            details[f_key]["observable_proxy_hint"][loc] = q.get("observable_proxy_hint", "")

        PROVISION_FACTS_MATRIX = matrix
        PROVISION_METADATA = metadata
        HIERARCHY_GRAPH = hierarchy
        FACT_QUESTION_CATALOG = catalog
        FACT_QUESTION_DETAILS = details
        _CACHE_INITIALIZED = True
        logger.info(f"Loaded {len(PROVISION_FACTS_MATRIX)} provisions into memory from static seed.")
    except Exception as exc:
        logger.error(f"Failed to load corpus from seed: {exc}")


async def load_corpus_to_memory(pool: asyncpg.Pool) -> None:
    """
    Reads all statutory provision facts, metadata, hierarchies, and multilingual question templates
    from the database and populates thread-safe in-memory dictionaries.
    """
    global PROVISION_FACTS_MATRIX, HIERARCHY_GRAPH, FACT_QUESTION_CATALOG, FACT_QUESTION_DETAILS, PROVISION_METADATA, _CACHE_INITIALIZED

    logger.info("Loading statutory corpus into memory from database...")

    try:
        async with pool.acquire() as conn:
            # Query 1: Read all records from provision_facts
            try:
                facts_rows = await conn.fetch(
                    """
                    SELECT provision_id, fact_key, expected_value
                    FROM provision_facts
                    ORDER BY provision_id, fact_key;
                    """
                )
                if facts_rows:
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
                logger.warning(f"Could not load provision_facts: {exc}")

            # Query 2: Read all records from provision_hierarchy
            try:
                hierarchy_rows = await conn.fetch(
                    """
                    SELECT parent_provision_id, child_provision_id, relation_type
                    FROM provision_hierarchy
                    ORDER BY parent_provision_id;
                    """
                )
                if hierarchy_rows:
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

            # Query 3: Read all records from fact_questions
            try:
                question_rows = await conn.fetch(
                    """
                    SELECT fact_key, locale, question_text, observable_proxy_hint, category
                    FROM fact_questions;
                    """
                )
                if question_rows:
                    catalog: Dict[str, Dict[str, str]] = {}
                    details: Dict[str, Dict[str, Any]] = {}
                    for row in question_rows:
                        f_key = str(row["fact_key"])
                        loc = str(row["locale"]) if "locale" in row else "en"
                        q_text = str(row["question_text"])
                        if f_key not in catalog:
                            catalog[f_key] = {}
                        catalog[f_key][loc] = q_text

                        if f_key not in details:
                            details[f_key] = {
                                "observable_proxy_hint": {},
                                "category": str(row.get("category", "general")),
                            }
                        hint = row.get("observable_proxy_hint")
                        if hint:
                            details[f_key]["observable_proxy_hint"][loc] = str(hint)
                    FACT_QUESTION_CATALOG = catalog
                    FACT_QUESTION_DETAILS = details
                    logger.info(f"Cached {len(FACT_QUESTION_CATALOG)} fact questions.")
            except Exception as exc:
                logger.warning(f"Could not load fact_questions: {exc}")

            # Query 4: Read legal_provisions metadata
            try:
                prov_rows = await conn.fetch(
                    """
                    SELECT id, section_number, bns_equivalent, ipc_equivalent, title,
                           statutory_text, plain_summary, punishment, is_cognizable,
                           is_bailable, compoundable_type, triable_by
                    FROM legal_provisions
                    ORDER BY id;
                    """
                )
                if prov_rows:
                    meta: Dict[int, Dict[str, Any]] = {}
                    for row in prov_rows:
                        pid = int(row["id"])
                        meta[pid] = {
                            "id": pid,
                            "section_number": str(row["section_number"]),
                            "bns_equivalent": str(row["bns_equivalent"] or ""),
                            "ipc_equivalent": str(row["ipc_equivalent"] or ""),
                            "title": str(row["title"]),
                            "statutory_text": str(row["statutory_text"]),
                            "plain_summary": str(row["plain_summary"]),
                            "punishment": str(row["punishment"]),
                            "is_cognizable": bool(row["is_cognizable"]),
                            "is_bailable": bool(row["is_bailable"]),
                            "compoundable_type": str(row["compoundable_type"]),
                            "triable_by": str(row["triable_by"]),
                        }
                    PROVISION_METADATA = meta
                    logger.info(f"Cached {len(PROVISION_METADATA)} provisions metadata from DB.")
            except Exception as exc:
                logger.debug(f"Could not load legal_provisions from DB: {exc}")

        # If database was empty or unseeded, populate from static seed data
        if not PROVISION_FACTS_MATRIX:
            logger.info("Database cache was empty, falling back to static seed data.")
            load_corpus_from_seed()
        else:
            _CACHE_INITIALIZED = True
    except Exception as exc:
        logger.warning(f"Database query error during corpus cache loading: {exc}")
        if not PROVISION_FACTS_MATRIX:
            load_corpus_from_seed()

    logger.info("Corpus caching complete.")


def is_cache_initialized() -> bool:
    """Returns True if the in-memory cache has been populated."""
    return _CACHE_INITIALIZED


def get_cached_matrix() -> Dict[int, Dict[str, str]]:
    """Returns the immutable provision facts matrix."""
    if not _CACHE_INITIALIZED and not PROVISION_FACTS_MATRIX:
        load_corpus_from_seed()
    return PROVISION_FACTS_MATRIX


def get_cached_hierarchy() -> Dict[int, List[Tuple[int, str]]]:
    """Returns the provision hierarchy graph."""
    if not _CACHE_INITIALIZED and not HIERARCHY_GRAPH:
        load_corpus_from_seed()
    return HIERARCHY_GRAPH


def get_cached_questions() -> Dict[str, Dict[str, str]]:
    """Returns the multilingual fact questions catalog."""
    if not _CACHE_INITIALIZED and not FACT_QUESTION_CATALOG:
        load_corpus_from_seed()
    return FACT_QUESTION_CATALOG


def get_cached_question_details() -> Dict[str, Dict[str, Any]]:
    """Returns question hints and categories."""
    if not _CACHE_INITIALIZED and not FACT_QUESTION_DETAILS:
        load_corpus_from_seed()
    return FACT_QUESTION_DETAILS


def get_cached_metadata() -> Dict[int, Dict[str, Any]]:
    """Returns statutory provision metadata."""
    if not _CACHE_INITIALIZED and not PROVISION_METADATA:
        load_corpus_from_seed()
    return PROVISION_METADATA
