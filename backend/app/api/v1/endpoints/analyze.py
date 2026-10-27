"""
FastAPI Scenario Intake & Crisis Routing Endpoint (BE-301, BE-302).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Header, status
import numpy as np

from backend.app.core.database import get_pool
from backend.app.engine.candidate_retrieval import hybrid_retrieve_candidates
from backend.app.engine.corpus_cache import (
    get_cached_hierarchy,
    get_cached_matrix,
    get_cached_metadata,
    get_cached_question_details,
    get_cached_questions,
)
from backend.app.engine.crisis import detect_emergency_crisis
from backend.app.engine.extractor import (
    determine_legal_regime,
    extract_facts_from_scenario,
    get_scenario_embedding,
    mask_pii,
)
from backend.app.engine.resolver import resolve_provisions_and_lesser_offences
from backend.app.engine.session_store import create_session
from backend.app.schemas.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    ClarificationQuestion,
)
from engine.core import (
    calculate_shannon_entropy,
    evaluate_best_question,
    update_posterior_soft,
)

logger = logging.getLogger("lexly.endpoints.analyze")
router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Scenario Intake, Crisis Interception, and Provision Initialization",
    description="Submits an incident description for crisis interception, concurrent embedding + fact extraction, and initial Information-Gain clarification.",
)
async def analyze_scenario(
    request: AnalyzeRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> AnalyzeResponse:
    """
    Intake pipeline:
    1. Crisis Guardrail (BE-301): Short-circuits immediate emergencies to 112/181/1098 in <15ms.
    2. PII Masking: Redacts Indian phones, Aadhaar, PAN, emails.
    3. Incident Date & Legal Regime: Pre- vs Post-1 July 2024 (IPC vs BNS).
    4. Concurrency: Parallel embedding generation & fact extraction via asyncio.gather.
    5. Hybrid Candidate Retrieval & Softmax Prior Initialization.
    6. Decision Gate: First Shannon Information-Gain question or direct resolution.
    """
    # -------------------------------------------------------------------------
    # 1. Crisis & Emergency Interception (BE-301)
    # -------------------------------------------------------------------------
    is_emergency, advisory, helplines = detect_emergency_crisis(request.scenario)
    if is_emergency:
        logger.info("Emergency crisis detected in scenario text. Intercepting.")
        return AnalyzeResponse(
            status="EMERGENCY_INTERCEPTION",
            helplines=helplines,
            advisory=advisory,
        )

    # -------------------------------------------------------------------------
    # 2. PII Masking (DPDP Act Compliance)
    # -------------------------------------------------------------------------
    masked_scenario = mask_pii(request.scenario)

    # -------------------------------------------------------------------------
    # 3. Incident Date & Legal Regime Selection
    # -------------------------------------------------------------------------
    primary_regime, parsed_incident_date = determine_legal_regime(
        request.incident_date, request.scenario
    )

    # -------------------------------------------------------------------------
    # 4. Concurrent Execution: Embeddings + Fact Extraction (asyncio.gather)
    # -------------------------------------------------------------------------
    task_embed = get_scenario_embedding(masked_scenario)
    task_extract = extract_facts_from_scenario(masked_scenario)

    query_embedding, extracted_facts = await asyncio.gather(task_embed, task_extract)

    # -------------------------------------------------------------------------
    # 5. Hybrid Retrieval & Initial Posterior Distribution
    # -------------------------------------------------------------------------
    pool = get_pool()
    candidates = await hybrid_retrieve_candidates(
        pool=pool,
        query_text=masked_scenario,
        query_embedding=query_embedding,
        limit=20,
    )

    candidate_ids = [c[0] for c in candidates]
    if not candidate_ids:
        # Fallback to top cached provision IDs if candidate retrieval returned empty
        matrix = get_cached_matrix()
        candidate_ids = list(matrix.keys())[:20]

    # Temperature-scaled softmax prior (tau = 0.5) over retrieval scores
    tau = 0.5
    scores = np.array([c[1] for c in candidates], dtype=np.float64) if candidates else np.ones(len(candidate_ids))
    exp_scores = np.exp(scores / tau)
    sum_exp = float(np.sum(exp_scores))
    p_initial = exp_scores / sum_exp if sum_exp > 1e-12 else np.ones(len(candidate_ids)) / len(candidate_ids)

    posterior: Dict[int, float] = {pid: float(p_initial[i]) for i, pid in enumerate(candidate_ids)}

    # Apply soft evidence updates for known extracted facts
    matrix = get_cached_matrix()
    known_facts: Dict[str, str] = {}
    ignored_facts: set = set()

    for f_key, f_val in extracted_facts.items():
        if f_val in ("TRUE", "FALSE"):
            known_facts[f_key] = f_val
            posterior = update_posterior_soft(
                candidate_ids=candidate_ids,
                current_posterior=posterior,
                fact_key=f_key,
                answer="YES" if f_val == "TRUE" else "NO",
                matrix=matrix,
                epsilon=0.08,
            )

    # -------------------------------------------------------------------------
    # 6. Decision Gate & First Clarification Question
    # -------------------------------------------------------------------------
    max_p = max(posterior.values()) if posterior else 0.0
    best_fact, best_ig = evaluate_best_question(
        candidate_ids=candidate_ids,
        current_posterior=posterior,
        known_facts=known_facts,
        ignored_facts=ignored_facts,
        matrix=matrix,
        epsilon=0.08,
    )

    p_vector = np.array([posterior.get(pid, 0.0) for pid in candidate_ids], dtype=np.float64)
    current_entropy = calculate_shannon_entropy(p_vector)

    session_id = str(uuid.uuid4())
    audit_trail: List[Dict[str, Any]] = [
        {
            "step": 0,
            "action": "INITIAL_ANALYSIS",
            "primary_regime": primary_regime,
            "extracted_facts": known_facts,
            "entropy": round(current_entropy, 4),
            "max_probability": round(max_p, 4),
        }
    ]

    metadata = get_cached_metadata()
    hierarchy = get_cached_hierarchy()
    catalog = get_cached_questions()
    question_details = get_cached_question_details()

    # Stopping condition: high certainty or no informative questions remaining
    if max_p >= 0.85 or best_ig < 0.10 or not best_fact:
        provisions, lesser_offences = resolve_provisions_and_lesser_offences(
            candidate_ids=candidate_ids,
            posterior=posterior,
            primary_legal_regime=primary_regime,
            known_facts=known_facts,
            matrix=matrix,
            hierarchy=hierarchy,
            metadata=metadata,
        )

        state_payload = {
            "known_facts": known_facts,
            "ignored_facts": list(ignored_facts),
            "candidate_ids": candidate_ids,
            "posterior": {str(k): round(v, 4) for k, v in posterior.items()},
            "audit_trail": audit_trail,
            "locale": request.locale,
        }

        await create_session(
            session_id=session_id,
            initial_scenario=masked_scenario,
            incident_date=parsed_incident_date,
            primary_legal_regime=primary_regime,
            state_payload=state_payload,
            pool=pool,
        )

        return AnalyzeResponse(
            status="COMPLETED",
            session_id=session_id,
            primary_legal_regime=primary_regime,
            current_step=1,
            max_steps=5,
            remaining_candidates_count=len(candidate_ids),
            provisions=provisions,
            lesser_offences=lesser_offences,
            audit_trail=audit_trail,
        )

    # Otherwise return NEEDS_CLARIFICATION with the highest-gain question
    q_locale = request.locale
    q_text = catalog.get(best_fact, {}).get(q_locale) or catalog.get(best_fact, {}).get("en") or f"Is {best_fact} true?"
    hint_dict = question_details.get(best_fact, {}).get("observable_proxy_hint", {})
    hint_text = hint_dict.get(q_locale) or hint_dict.get("en")
    category = question_details.get(best_fact, {}).get("category", "general")

    question_obj = ClarificationQuestion(
        fact_key=best_fact,
        question_text=q_text,
        observable_proxy_hint=hint_text,
        category=category,
        information_gain_bits=round(best_ig, 4),
    )

    state_payload = {
        "known_facts": known_facts,
        "ignored_facts": list(ignored_facts),
        "candidate_ids": candidate_ids,
        "posterior": {str(k): round(v, 4) for k, v in posterior.items()},
        "audit_trail": audit_trail,
        "current_question": best_fact,
        "locale": request.locale,
    }

    await create_session(
        session_id=session_id,
        initial_scenario=masked_scenario,
        incident_date=parsed_incident_date,
        primary_legal_regime=primary_regime,
        state_payload=state_payload,
        pool=pool,
    )

    return AnalyzeResponse(
        status="NEEDS_CLARIFICATION",
        session_id=session_id,
        primary_legal_regime=primary_regime,
        current_step=1,
        max_steps=5,
        question=question_obj,
        remaining_candidates_count=len(candidate_ids),
        audit_trail=audit_trail,
    )

