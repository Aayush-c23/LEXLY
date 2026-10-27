"""
FastAPI Fast-Path Answer, Undo, and DPDP Purge Endpoints (BE-303, BE-304, BE-305).
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, status
import numpy as np

from backend.app.core.database import get_pool
from backend.app.engine.corpus_cache import (
    get_cached_hierarchy,
    get_cached_matrix,
    get_cached_metadata,
    get_cached_question_details,
    get_cached_questions,
)
from backend.app.engine.resolver import resolve_provisions_and_lesser_offences
from backend.app.engine.session_store import (
    atomic_step_update,
    cleanup_expired_sessions,
    delete_session_cascade,
    get_session,
    record_session_fact_audit,
    save_session_state,
)
from backend.app.schemas.analyze import ClarificationQuestion
from backend.app.schemas.session import (
    AnswerRequest,
    AnswerResponse,
    DeleteSessionResponse,
    UndoResponse,
)
from engine.core import (
    calculate_shannon_entropy,
    evaluate_best_question,
    update_posterior_soft,
)

logger = logging.getLogger("lexly.endpoints.session")
router = APIRouter()


@router.post(
    "/session/{session_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Zero-LLM Fast-Path Answer Resolution (BE-303)",
    description="Processes user clarification answers purely in RAM using Bayesian soft updates and Shannon Information Gain in <15ms.",
)
async def submit_answer(
    background_tasks: BackgroundTasks,
    session_id: str = Path(..., description="UUID of the active analysis session"),
    request: AnswerRequest = ...,
) -> AnswerResponse:
    """
    Zero-LLM Fast Path:
    1. Optimistic Locking: Validates step counter; handles idempotent replays.
    2. Bayesian Soft Update: Updates in-memory posterior without LLM generative overhead.
    3. Stopping Check: If p_max >= 0.85, step >= 5, or IG < 0.10, resolves grounded provisions.
    4. Shannon Information Gain: Selects next best clarification question.
    5. Asynchronous Audit Logging: Dispatches non-blocking DB audit insert.
    """
    pool = get_pool()
    session = await get_session(session_id, pool)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis session '{session_id}' not found.",
        )

    current_step = session["current_step"]

    # 1. Optimistic Locking & Idempotent Replay Detection
    if request.step != current_step:
        if request.step < current_step:
            # Client replay or double-tap: return current state idempotently
            logger.info(f"Replay detected for session {session_id}: requested {request.step}, current {current_step}")
            return _build_current_step_response(session, request.locale)
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Step mismatch: Session is at step {current_step}, but received step {request.step}.",
            )

    payload = session.get("state_payload", {})
    candidate_ids: List[int] = payload.get("candidate_ids", [])
    raw_posterior: Dict[str, float] = payload.get("posterior", {})
    posterior: Dict[int, float] = {int(k): float(v) for k, v in raw_posterior.items()}
    known_facts: Dict[str, str] = payload.get("known_facts", {})
    ignored_facts: set = set(payload.get("ignored_facts", []))
    audit_trail: List[Dict[str, Any]] = payload.get("audit_trail", [])
    primary_regime: str = session.get("primary_legal_regime", "BNS")

    matrix = get_cached_matrix()
    metadata = get_cached_metadata()
    hierarchy = get_cached_hierarchy()
    catalog = get_cached_questions()
    question_details = get_cached_question_details()

    # 2. Bayesian Soft Update (<15ms in RAM)
    if request.answer == "NOT_SURE":
        ignored_facts.add(request.fact_key)
        fact_val_recorded = "UNKNOWN"
    else:
        norm_val = "TRUE" if request.answer == "YES" else "FALSE"
        known_facts[request.fact_key] = norm_val
        fact_val_recorded = norm_val
        posterior = update_posterior_soft(
            candidate_ids=candidate_ids,
            current_posterior=posterior,
            fact_key=request.fact_key,
            answer=request.answer,
            matrix=matrix,
            epsilon=0.08,
        )

    # Schedule fire-and-forget asynchronous audit log
    background_tasks.add_task(
        record_session_fact_audit,
        session_id=session_id,
        step_number=current_step,
        fact_key=request.fact_key,
        fact_value=fact_val_recorded,
        source="USER_RESPONSE",
        pool=pool,
    )

    # 3. Stopping Criteria Evaluation
    p_vector = np.array([posterior.get(pid, 0.0) for pid in candidate_ids], dtype=np.float64)
    new_entropy = calculate_shannon_entropy(p_vector)
    max_p = max(posterior.values()) if posterior else 0.0

    best_fact, best_ig = evaluate_best_question(
        candidate_ids=candidate_ids,
        current_posterior=posterior,
        known_facts=known_facts,
        ignored_facts=ignored_facts,
        matrix=matrix,
        epsilon=0.08,
    )

    next_step_index = current_step + 1

    # Record audit step
    audit_trail.append(
        {
            "step": current_step,
            "fact_key": request.fact_key,
            "answer": request.answer,
            "resulting_entropy": round(new_entropy, 4),
            "max_probability": round(max_p, 4),
            "top_candidate": int(candidate_ids[int(np.argmax(p_vector))]) if len(p_vector) > 0 else None,
        }
    )

    is_completed = (
        max_p >= 0.85 or
        next_step_index > 5 or
        best_ig < 0.10 or
        not best_fact
    )

    if is_completed:
        # Resolve Grounded Provisions
        provisions, lesser_offences = resolve_provisions_and_lesser_offences(
            candidate_ids=candidate_ids,
            posterior=posterior,
            primary_legal_regime=primary_regime,
            known_facts=known_facts,
            matrix=matrix,
            hierarchy=hierarchy,
            metadata=metadata,
        )

        new_payload = {
            "known_facts": known_facts,
            "ignored_facts": list(ignored_facts),
            "candidate_ids": candidate_ids,
            "posterior": {str(k): round(v, 4) for k, v in posterior.items()},
            "audit_trail": audit_trail,
            "locale": request.locale,
        }

        await atomic_step_update(
            session_id=session_id,
            expected_step=current_step,
            new_state_payload=new_payload,
            new_status="RESOLVED",
            pool=pool,
        )

        return AnswerResponse(
            status="COMPLETED",
            session_id=session_id,
            current_step=next_step_index,
            max_steps=5,
            primary_legal_regime=primary_regime,
            remaining_candidates_count=len(candidate_ids),
            provisions=provisions,
            lesser_offences=lesser_offences,
            audit_trail=audit_trail,
        )

    # Otherwise: Next Shannon Information-Gain Question
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

    new_payload = {
        "known_facts": known_facts,
        "ignored_facts": list(ignored_facts),
        "candidate_ids": candidate_ids,
        "posterior": {str(k): round(v, 4) for k, v in posterior.items()},
        "audit_trail": audit_trail,
        "current_question": best_fact,
        "locale": request.locale,
    }

    await atomic_step_update(
        session_id=session_id,
        expected_step=current_step,
        new_state_payload=new_payload,
        new_status="IN_PROGRESS",
        pool=pool,
    )

    return AnswerResponse(
        status="NEEDS_CLARIFICATION",
        session_id=session_id,
        current_step=next_step_index,
        max_steps=5,
        primary_legal_regime=primary_regime,
        question=question_obj,
        remaining_candidates_count=len(candidate_ids),
        audit_trail=audit_trail,
    )


@router.post(
    "/session/{session_id}/undo",
    response_model=UndoResponse,
    status_code=status.HTTP_200_OK,
    summary="Session Undo & Revert Endpoint (BE-304)",
    description="Rolls back session state to step N-1 without corrupting session integrity.",
)
async def undo_step(
    session_id: str = Path(..., description="UUID of the active analysis session"),
) -> UndoResponse:
    """
    Rolls back the last answered fact:
    1. Reverts state to step N-1 from session audit trail.
    2. Removes the last answered fact from known_facts or ignored_facts.
    3. Re-evaluates best question and returns previous inquiry state.
    """
    pool = get_pool()
    session = await get_session(session_id, pool)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis session '{session_id}' not found.",
        )

    current_step = session["current_step"]
    payload = session.get("state_payload", {})
    audit_trail: List[Dict[str, Any]] = payload.get("audit_trail", [])

    if current_step <= 1 or len(audit_trail) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot undo beyond the initial question step.",
        )

    # Pop the last step from audit trail
    last_action = audit_trail.pop()
    reverted_fact_key = last_action.get("fact_key")

    known_facts: Dict[str, str] = payload.get("known_facts", {})
    ignored_facts: set = set(payload.get("ignored_facts", []))

    if reverted_fact_key:
        known_facts.pop(reverted_fact_key, None)
        ignored_facts.discard(reverted_fact_key)

    candidate_ids: List[int] = payload.get("candidate_ids", [])
    matrix = get_cached_matrix()
    catalog = get_cached_questions()
    question_details = get_cached_question_details()

    # Recompute posterior distribution from step 0
    tau = 0.5
    p_initial = np.ones(len(candidate_ids)) / len(candidate_ids)
    posterior: Dict[int, float] = {pid: float(p_initial[i]) for i, pid in enumerate(candidate_ids)}

    for f_k, f_v in known_facts.items():
        posterior = update_posterior_soft(
            candidate_ids=candidate_ids,
            current_posterior=posterior,
            fact_key=f_k,
            answer="YES" if f_v == "TRUE" else "NO",
            matrix=matrix,
            epsilon=0.08,
        )

    reverted_step = current_step - 1

    # Re-evaluate best question
    best_fact, best_ig = evaluate_best_question(
        candidate_ids=candidate_ids,
        current_posterior=posterior,
        known_facts=known_facts,
        ignored_facts=ignored_facts,
        matrix=matrix,
        epsilon=0.08,
    )

    q_locale = payload.get("locale", "en")
    question_obj: Optional[ClarificationQuestion] = None
    if best_fact:
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

    new_payload = {
        "known_facts": known_facts,
        "ignored_facts": list(ignored_facts),
        "candidate_ids": candidate_ids,
        "posterior": {str(k): round(v, 4) for k, v in posterior.items()},
        "audit_trail": audit_trail,
        "current_question": best_fact,
        "locale": q_locale,
    }

    await save_session_state(
        session_id=session_id,
        current_step=reverted_step,
        state_payload=new_payload,
        status="IN_PROGRESS",
        pool=pool,
    )

    return UndoResponse(
        status="NEEDS_CLARIFICATION",
        session_id=session_id,
        current_step=reverted_step,
        question=question_obj,
        remaining_candidates_count=len(candidate_ids),
        message=f"Reverted answer for '{reverted_fact_key}'. Returned to step {reverted_step}.",
    )


@router.delete(
    "/session/{session_id}",
    response_model=DeleteSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="DPDP Act 2023 Session Purge Endpoint (BE-305)",
    description="Permanently erases all session records, vector associations, and audit facts.",
)
async def delete_session(
    session_id: str = Path(..., description="UUID of the analysis session to erase"),
) -> DeleteSessionResponse:
    """
    Indian DPDP Act 2023 compliance:
    Executes permanent cascade deletion of session state and associated fact logs.
    """
    pool = get_pool()
    await delete_session_cascade(session_id, pool)

    return DeleteSessionResponse(
        status="DELETED",
        session_id=session_id,
        message="Session and all associated audit traces have been permanently erased.",
    )


@router.post(
    "/session/cleanup",
    status_code=status.HTTP_200_OK,
    summary="DPDP Act 2023 24-Hour TTL Scrubber (SEC-601)",
    description="Purges sessions and audit traces older than 24 hours.",
)
async def cleanup_sessions(ttl_hours: int = 24) -> Dict[str, Any]:
    pool = get_pool()
    purged = await cleanup_expired_sessions(pool, ttl_hours=ttl_hours)
    return {
        "status": "CLEANUP_COMPLETED",
        "purged_sessions_count": purged,
        "ttl_hours": ttl_hours,
    }


def _build_current_step_response(session: Dict[str, Any], locale: str) -> AnswerResponse:
    """Builds idempotent response for replayed step requests."""
    payload = session.get("state_payload", {})
    candidate_ids = payload.get("candidate_ids", [])
    current_q = payload.get("current_question")
    catalog = get_cached_questions()
    question_details = get_cached_question_details()

    question_obj: Optional[ClarificationQuestion] = None
    if current_q:
        q_text = catalog.get(current_q, {}).get(locale) or catalog.get(current_q, {}).get("en") or f"Is {current_q} true?"
        hint_dict = question_details.get(current_q, {}).get("observable_proxy_hint", {})
        hint_text = hint_dict.get(locale) or hint_dict.get("en")
        category = question_details.get(current_q, {}).get("category", "general")
        question_obj = ClarificationQuestion(
            fact_key=current_q,
            question_text=q_text,
            observable_proxy_hint=hint_text,
            category=category,
        )

    return AnswerResponse(
        status="NEEDS_CLARIFICATION",
        session_id=session["id"],
        current_step=session["current_step"],
        max_steps=5,
        primary_legal_regime=session.get("primary_legal_regime", "BNS"),
        question=question_obj,
        remaining_candidates_count=len(candidate_ids),
        audit_trail=payload.get("audit_trail", []),
    )

