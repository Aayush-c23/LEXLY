"""
Session State Persistence with Optimistic Locking & Audit Logging (BE-302, BE-303, BE-304, BE-305).
"""

from datetime import date, datetime
import json
import logging
from typing import Any, Dict, Optional, Tuple
import uuid
import asyncpg

logger = logging.getLogger("lexly.session_store")

# In-memory session store fallback when database connection pool is not active
_IN_MEMORY_SESSIONS: Dict[str, Dict[str, Any]] = {}
_IN_MEMORY_SESSION_FACTS: Dict[str, list] = {}


async def create_session(
    session_id: str,
    initial_scenario: str,
    incident_date: Optional[date],
    primary_legal_regime: str,
    state_payload: Dict[str, Any],
    pool: Optional[asyncpg.Pool],
) -> Dict[str, Any]:
    """
    Inserts a new analysis session record with initial JSONB state.
    """
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analysis_sessions (
                        id, initial_scenario, incident_date, primary_legal_regime,
                        current_step, status, state_payload
                    )
                    VALUES ($1::uuid, $2, $3, $4, 1, 'IN_PROGRESS', $5::jsonb);
                    """,
                    session_id,
                    initial_scenario,
                    incident_date,
                    primary_legal_regime,
                    json.dumps(state_payload),
                )
        except Exception as exc:
            logger.warning(f"Could not persist session to DB: {exc}. Using in-memory store.")

    session_record = {
        "id": session_id,
        "initial_scenario": initial_scenario,
        "incident_date": incident_date.isoformat() if incident_date else None,
        "primary_legal_regime": primary_legal_regime,
        "current_step": 1,
        "status": "IN_PROGRESS",
        "state_payload": state_payload,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _IN_MEMORY_SESSIONS[session_id] = session_record
    return session_record


async def get_session(session_id: str, pool: Optional[asyncpg.Pool]) -> Optional[Dict[str, Any]]:
    """
    Retrieves analysis session by UUID.
    """
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, initial_scenario, incident_date, primary_legal_regime,
                           current_step, status, state_payload
                    FROM analysis_sessions
                    WHERE id = $1::uuid;
                    """,
                    session_id,
                )
                if row:
                    payload = row["state_payload"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    return {
                        "id": str(row["id"]),
                        "initial_scenario": row["initial_scenario"],
                        "incident_date": row["incident_date"],
                        "primary_legal_regime": row["primary_legal_regime"],
                        "current_step": int(row["current_step"]),
                        "status": row["status"],
                        "state_payload": payload,
                    }
        except Exception as exc:
            logger.warning(f"DB get_session failed: {exc}. Checking in-memory store.")

    return _IN_MEMORY_SESSIONS.get(session_id)


async def atomic_step_update(
    session_id: str,
    expected_step: int,
    new_state_payload: Dict[str, Any],
    new_status: str,
    pool: Optional[asyncpg.Pool],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Executes atomic optimistic locking update:
    UPDATE analysis_sessions
    SET current_step = current_step + 1, state_payload = $1, status = $2, updated_at = NOW()
    WHERE id = $3 AND current_step = $4
    RETURNING *;

    Returns
    -------
    Tuple[bool, Optional[Dict[str, Any]]]
        (success, updated_or_existing_session)
    """
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    UPDATE analysis_sessions
                    SET current_step = current_step + 1,
                        state_payload = $1::jsonb,
                        status = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3::uuid AND current_step = $4
                    RETURNING id, current_step, status, state_payload, primary_legal_regime;
                    """,
                    json.dumps(new_state_payload),
                    new_status,
                    session_id,
                    expected_step,
                )
                if row:
                    payload = row["state_payload"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    rec = {
                        "id": str(row["id"]),
                        "current_step": int(row["current_step"]),
                        "status": row["status"],
                        "state_payload": payload,
                        "primary_legal_regime": row["primary_legal_regime"],
                    }
                    _IN_MEMORY_SESSIONS[session_id] = rec
                    return True, rec
                else:
                    # No rows updated: fetch existing session for idempotent replay check
                    existing = await get_session(session_id, pool)
                    return False, existing
        except Exception as exc:
            logger.warning(f"DB atomic_step_update failed: {exc}. Using in-memory fallback.")

    # In-memory optimistic lock
    existing = _IN_MEMORY_SESSIONS.get(session_id)
    if not existing:
        return False, None

    if existing["current_step"] == expected_step:
        existing["current_step"] += 1
        existing["state_payload"] = new_state_payload
        existing["status"] = new_status
        existing["updated_at"] = datetime.now().isoformat()
        return True, existing
    else:
        # Step mismatch (double-tap or stale step)
        return False, existing


async def save_session_state(
    session_id: str,
    current_step: int,
    state_payload: Dict[str, Any],
    status: str,
    pool: Optional[asyncpg.Pool],
) -> None:
    """
    Directly updates session state payload and current step (used for undo).
    """
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE analysis_sessions
                    SET current_step = $1, state_payload = $2::jsonb, status = $3, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $4::uuid;
                    """,
                    current_step,
                    json.dumps(state_payload),
                    status,
                    session_id,
                )
        except Exception as exc:
            logger.warning(f"DB save_session_state failed: {exc}")

    if session_id in _IN_MEMORY_SESSIONS:
        _IN_MEMORY_SESSIONS[session_id]["current_step"] = current_step
        _IN_MEMORY_SESSIONS[session_id]["state_payload"] = state_payload
        _IN_MEMORY_SESSIONS[session_id]["status"] = status
        _IN_MEMORY_SESSIONS[session_id]["updated_at"] = datetime.now().isoformat()


async def delete_session_cascade(session_id: str, pool: Optional[asyncpg.Pool]) -> bool:
    """
    Permanently erases session and associated facts for DPDP Act 2023 compliance.
    """
    deleted_db = False
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    DELETE FROM session_facts WHERE session_id = $1::uuid;
                    DELETE FROM analysis_sessions WHERE id = $1::uuid;
                    """,
                    session_id,
                )
                deleted_db = True
        except Exception as exc:
            logger.warning(f"DB delete_session_cascade failed: {exc}")

    deleted_mem = bool(_IN_MEMORY_SESSIONS.pop(session_id, None) is not None)
    _IN_MEMORY_SESSION_FACTS.pop(session_id, None)
    return deleted_db or deleted_mem


async def cleanup_expired_sessions(pool: Optional[asyncpg.Pool], ttl_hours: int = 24) -> int:
    """
    Deletes all sessions and facts older than ttl_hours (default: 24h) per DPDP Act 2023.
    Returns the count of purged sessions.
    """
    purged_count = 0
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                res = await conn.execute(
                    """
                    DELETE FROM session_facts
                    WHERE session_id IN (
                        SELECT id FROM analysis_sessions
                        WHERE created_at < NOW() - ($1 || ' hours')::interval
                    );
                    DELETE FROM analysis_sessions
                    WHERE created_at < NOW() - ($1 || ' hours')::interval;
                    """,
                    str(ttl_hours),
                )
                # Parse delete count from command tag
                if "DELETE" in res:
                    purged_count += int(res.split()[-1])
        except Exception as exc:
            logger.warning(f"DB cleanup_expired_sessions failed: {exc}")

    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=ttl_hours)
    expired_ids = [
        sid for sid, rec in _IN_MEMORY_SESSIONS.items()
        if datetime.fromisoformat(rec.get("created_at", datetime.now().isoformat())) < cutoff
    ]
    for sid in expired_ids:
        _IN_MEMORY_SESSIONS.pop(sid, None)
        _IN_MEMORY_SESSION_FACTS.pop(sid, None)
        purged_count += 1

    logger.info(f"Purged {purged_count} expired sessions exceeding {ttl_hours}h TTL.")
    return purged_count


async def record_session_fact_audit(
    session_id: str,
    step_number: int,
    fact_key: str,
    fact_value: str,
    source: str,
    pool: Optional[asyncpg.Pool],
) -> None:
    """
    Asynchronous audit logger inserting a fact entry into session_facts.
    Runs in background task without blocking API latency.
    """
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO session_facts (session_id, step_number, fact_key, fact_value, source)
                    VALUES ($1::uuid, $2, $3, $4, $5);
                    """,
                    session_id,
                    step_number,
                    fact_key,
                    fact_value,
                    source,
                )
        except Exception as exc:
            logger.debug(f"Asynchronous DB fact audit logging skipped or failed: {exc}")

    if session_id not in _IN_MEMORY_SESSION_FACTS:
        _IN_MEMORY_SESSION_FACTS[session_id] = []
    _IN_MEMORY_SESSION_FACTS[session_id].append({
        "step_number": step_number,
        "fact_key": fact_key,
        "fact_value": fact_value,
        "source": source,
        "created_at": datetime.now().isoformat(),
    })
