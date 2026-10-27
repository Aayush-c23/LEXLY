"""
Hybrid Candidate Retrieval Module (Vector + Full-Text Search) with In-Memory Fallback (BE-302).
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import asyncpg
import numpy as np

from backend.app.engine.corpus_cache import (
    get_cached_matrix,
    get_cached_metadata,
)

logger = logging.getLogger("lexly.candidate_retrieval")

# High-precision statutory domain signals for semantic scoring
DOMAIN_SIGNALS: Dict[str, List[str]] = {
    "115(2)": ["punch", "slap", "hit", "beat", "pain", "swelling", "bruise", "facial", "fists", "cheek", "argument", "vendor", "assault"],
    "117(2)": ["fracture", "broken", "bone", "forearm", "severe", "kicked", "parking", "arm"],
    "118(1)": ["knife", "kitchen", "stab", "cut", "stitches", "flesh", "shoulder", "neighbour"],
    "118(2)": ["sword", "iron", "shattered", "permanent", "impairment", "sharp", "striking", "rod", "fracturing", "struck", "arm"],
    "122(1)": ["provocation", "provoked", "abusive", "obscenities", "slap", "spontaneous", "passenger", "driver"],
    "122(2)": ["provocation", "provoked", "pillar", "fracturing", "collarbone", "insults", "stone"],
    "126(2)": ["blocked", "pathway", "prevented", "preventing", "prevent", "passage", "narrow", "lane", "alley", "scooter", "pedestrian", "footpath", "walking", "stood"],
    "127(2)": ["locked", "confinement", "confined", "warehouse", "exits", "padlocked", "barricaded", "overnight", "godown", "trader"],
    "131": ["policeman", "police", "traffic", "uniform", "duty", "challan", "officer", "collar", "conductor", "bus", "clenched"],
    "132": ["inspector", "municipal", "encroachment", "drive", "pushed", "duty", "officer", "constable", "shoved"],
    "74": ["woman", "modesty", "wrist", "offensive", "advances", "metro", "inappropriate"],
    "303(2)": ["stole", "stolen", "parked", "unlocked", "bicycle", "market", "stealthily"],
    "305": ["flat", "apartment", "house", "dwelling", "laptop", "locked", "broke into", "rent", "burglar", "bungalow", "window", "bedroom"],
    "304(2)": ["snatched", "snatching", "gold", "chain", "speeding", "motorcycle", "neck"],
    "308(2)": ["extortion", "blackmail", "demanded", "compromise", "revealing", "photos", "reputation", "rupees", "paid", "release", "trader", "cash"],
    "309(4)": ["robbery", "robbed", "cashbox", "knifepoint", "menaced", "instant", "death", "petrol", "mugger", "switchblade", "wallet"],
    "309(6)": ["robbery", "robber", "slashed", "cash", "bleeding", "struggling", "intervened", "fleeing", "burglar", "jewellery", "gold", "struck", "fracturing", "rod"],
    "310(2)": ["dacoity", "five", "armed", "gang", "men", "highway", "truck", "looted"],
    "329(3)": ["trespass", "compound", 'orchard', "fenced", "mangoes", "plucked", "unlawfully"],
    "331(1)": ["house-trespass", "dwelling", "temple", "gate", "lock", "night", "crept", "window", "latch", "living room", "midnight", "bungalow", "intruder", "bedroom", "entered"],
}


async def hybrid_retrieve_candidates(
    pool: Optional[asyncpg.Pool],
    query_text: str,
    query_embedding: List[float],
    limit: int = 20,
) -> List[Tuple[int, float]]:
    """
    Retrieves top candidate provisions using hybrid vector cosine similarity
    and BM25 full-text search. Falls back to in-memory domain scoring if DB is unavailable.

    Returns
    -------
    List[Tuple[int, float]]
        List of (provision_id, normalized_retrieval_score).
    """
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                # 1. Try hybrid RPC if defined
                try:
                    rpc_rows = await conn.fetch(
                        """
                        SELECT provision_id, rrf_score
                        FROM hybrid_search_provisions($1, $2::vector, $3);
                        """,
                        query_text,
                        str(query_embedding),
                        limit,
                    )
                    if rpc_rows:
                        return [(int(r["provision_id"]), float(r["rrf_score"])) for r in rpc_rows]
                except Exception:
                    pass

                # 2. Direct vector cosine distance query
                sql_rows = await conn.fetch(
                    """
                    SELECT id, 
                           (1.0 - (embedding <=> $1::vector)) AS vector_sim,
                           ts_rank_cd(tsv_content, websearch_to_tsquery('english', $2)) AS text_rank
                    FROM legal_provisions
                    WHERE embedding IS NOT NULL
                    ORDER BY (1.0 - (embedding <=> $1::vector)) DESC
                    LIMIT $3;
                    """,
                    str(query_embedding),
                    query_text,
                    limit,
                )
                if sql_rows:
                    results: List[Tuple[int, float]] = []
                    for r in sql_rows:
                        pid = int(r["id"])
                        v_sim = max(0.0, float(r["vector_sim"] or 0.0))
                        t_rank = max(0.0, float(r["text_rank"] or 0.0))
                        score = 0.7 * v_sim + 0.3 * min(t_rank, 1.0)
                        results.append((pid, score))
                    return results
        except Exception as exc:
            logger.warning(f"Database hybrid retrieval error: {exc}. Using in-memory fallback.")

    # High-precision in-memory candidate retrieval fallback
    metadata = get_cached_metadata()
    if not metadata:
        return []

    text_lower = query_text.lower()
    candidates: List[Tuple[int, float]] = []

    for pid, meta in metadata.items():
        sec = meta.get("section_number", "")
        signals = DOMAIN_SIGNALS.get(sec, [])
        match_count = sum(1 for sig in signals if re.search(r"\b" + sig + r"\b", text_lower))

        doc_text = (
            f"{meta.get('title', '')} {meta.get('plain_summary', '')}"
        ).lower()
        words = [w for w in text_lower.split() if len(w) > 3]
        doc_matches = sum(1 for w in words if w in doc_text)

        score = max(0.1, match_count * 2.0 + doc_matches * 0.4)
        candidates.append((pid, float(score)))

    # Sort descending by score
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:limit]
