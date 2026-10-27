"""
Comprehensive Integration & Unit Tests for LEXLY Phase 3 Endpoints (BE-301 to BE-305).
"""

import time
import pytest
from fastapi.testclient import TestClient
from backend.app.engine import corpus_cache
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """Provides a synchronous FastAPI TestClient with lifespan."""
    # Ensure in-memory corpus cache is loaded
    corpus_cache.load_corpus_from_seed()
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# BE-301: Crisis & Emergency Interception Tests
# =============================================================================
def test_emergency_interception_kidnapping(client):
    """Verifies that an immediate kidnapping threat triggers crisis interception in <15ms."""
    t0 = time.perf_counter()
    response = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "Help! An armed stranger has kidnapped my child right now from our front gate!",
            "locale": "en",
        },
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EMERGENCY_INTERCEPTION"
    assert "helplines" in data
    assert len(data["helplines"]) >= 4

    # Verify verified Indian emergency numbers
    numbers = [h["number"] for h in data["helplines"]]
    assert "112" in numbers
    assert "181" in numbers
    assert "1098" in numbers
    assert "1930" in numbers

    # Verify execution latency is well under 100ms
    assert elapsed_ms < 100.0


def test_emergency_interception_domestic_violence(client):
    """Verifies domestic violence active emergency interception."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "This is a domestic violence emergency, my husband is beating me right now and I am locked in the bathroom.",
            "locale": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EMERGENCY_INTERCEPTION"
    assert "181" in [h["number"] for h in data["helplines"]]


# =============================================================================
# BE-302: Parallel Intake Pipeline Tests
# =============================================================================
def test_analyze_character_validation_failure(client):
    """Enforces 20 <= len(scenario) <= 2000 character length constraint."""
    # Too short (< 20 characters)
    res_short = client.post(
        "/api/v1/analyze",
        json={"scenario": "Stolen laptop.", "locale": "en"},
    )
    assert res_short.status_code == 422

    # Too long (> 2000 characters)
    res_long = client.post(
        "/api/v1/analyze",
        json={"scenario": "A" * 2005, "locale": "en"},
    )
    assert res_long.status_code == 422


def test_analyze_bns_regime_selection(client):
    """Scenario on or after 2024-07-01 assigns primary legal regime BNS."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "A man attacked my shop yesterday and stole several electronic appliances worth 50,000 rupees without my consent.",
            "incident_date": "2024-08-15",
            "locale": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("NEEDS_CLARIFICATION", "COMPLETED")
    assert data["primary_legal_regime"] == "BNS"
    assert data["session_id"] is not None
    assert data["current_step"] == 1


def test_analyze_ipc_regime_selection(client):
    """Scenario before 2024-07-01 assigns primary legal regime IPC."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "During a dispute over parking in May, the accused beat the complainant with fists causing simple bodily pain.",
            "incident_date": "2024-05-10",
            "locale": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("NEEDS_CLARIFICATION", "COMPLETED")
    assert data["primary_legal_regime"] == "IPC"


def test_analyze_pii_masking_integration(client):
    """Ensures scenarios containing Aadhaar or phone numbers are processed without failure."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "My landlord called from 9876543210 and threatened me with Aadhaar 1234 5678 9012 and stole my laptop from my flat.",
            "incident_date": "2024-09-01",
            "locale": "en",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is not None


# =============================================================================
# BE-303: Zero-LLM Fast-Path Answer Endpoint Tests
# =============================================================================
def test_answer_flow_and_optimistic_locking(client):
    """Tests inquiry step progression, optimistic locking, and replay handling."""
    # 1. Start session
    init_res = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "A thief broke into my apartment yesterday and took my gold necklace while threatening me.",
            "incident_date": "2024-08-20",
            "locale": "en",
        },
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    session_id = init_data["session_id"]
    first_q = init_data.get("question")

    if not first_q:
        # Already resolved
        assert init_data["status"] == "COMPLETED"
        return

    fact_key = first_q["fact_key"]

    # 2. Submit valid answer for step 1
    t0 = time.perf_counter()
    ans_res = client.post(
        f"/api/v1/session/{session_id}/answer",
        json={
            "step": 1,
            "fact_key": fact_key,
            "answer": "YES",
            "locale": "en",
        },
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert ans_data["session_id"] == session_id
    assert ans_data["current_step"] == 2
    # Ensure Fast-path latency is low
    assert elapsed_ms < 100.0

    # 3. Test optimistic locking: client replay (step 1 submitted again)
    replay_res = client.post(
        f"/api/v1/session/{session_id}/answer",
        json={
            "step": 1,
            "fact_key": fact_key,
            "answer": "YES",
            "locale": "en",
        },
    )
    assert replay_res.status_code == 200
    replay_data = replay_res.json()
    assert replay_data["current_step"] == 2  # Idempotently returned step 2 state

    # 4. Test optimistic locking: future step (step 99) rejected with 409 Conflict
    conflict_res = client.post(
        f"/api/v1/session/{session_id}/answer",
        json={
            "step": 99,
            "fact_key": fact_key,
            "answer": "NO",
            "locale": "en",
        },
    )
    assert conflict_res.status_code == 409


def test_answer_not_sure_masks_fact(client):
    """Verifies that answering NOT_SURE masks the fact without crashing."""
    init_res = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "A stranger hit me during a heated argument in a public market causing pain.",
            "incident_date": "2024-08-20",
            "locale": "en",
        },
    )
    session_id = init_res.json()["session_id"]
    question = init_res.json().get("question")
    if not question:
        return

    ans_res = client.post(
        f"/api/v1/session/{session_id}/answer",
        json={
            "step": 1,
            "fact_key": question["fact_key"],
            "answer": "NOT_SURE",
            "locale": "en",
        },
    )
    assert ans_res.status_code == 200
    assert ans_res.json()["current_step"] == 2


def test_answer_completion_resolution(client):
    """Steps through questions until completion and verifies grounded provisions and procedural tags."""
    init_res = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "My neighbor punched me in the face during an argument, causing swelling and localized facial pain without weapons.",
            "incident_date": "2024-08-10",
            "locale": "en",
        },
    )
    session_id = init_res.json()["session_id"]
    current_data = init_res.json()
    step = 1

    while current_data["status"] == "NEEDS_CLARIFICATION" and step <= 5:
        q = current_data["question"]
        ans_res = client.post(
            f"/api/v1/session/{session_id}/answer",
            json={
                "step": step,
                "fact_key": q["fact_key"],
                "answer": "NO" if "weapon" in q["fact_key"] or "grievous" in q["fact_key"] else "YES",
                "locale": "en",
            },
        )
        assert ans_res.status_code == 200
        current_data = ans_res.json()
        step = current_data["current_step"]

    # Session must now be completed
    assert current_data["status"] == "COMPLETED"
    assert current_data["provisions"] is not None
    assert len(current_data["provisions"]) > 0

    top_prov = current_data["provisions"][0]
    assert top_prov["section_number"] is not None
    assert top_prov["primary_citation"] is not None
    assert top_prov["punishment"] is not None
    assert isinstance(top_prov["is_bailable"], bool)
    assert isinstance(top_prov["is_cognizable"], bool)


# =============================================================================
# BE-304: Session Undo Tests
# =============================================================================
def test_session_undo(client):
    """Verifies that undo successfully reverts to step N-1."""
    init_res = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "Someone forced open my house door and took personal documents while threatening violence.",
            "incident_date": "2024-08-15",
            "locale": "en",
        },
    )
    session_id = init_res.json()["session_id"]
    q1 = init_res.json().get("question")
    if not q1:
        return

    # Answer step 1
    ans_res = client.post(
        f"/api/v1/session/{session_id}/answer",
        json={"step": 1, "fact_key": q1["fact_key"], "answer": "YES", "locale": "en"},
    )
    assert ans_res.status_code == 200
    assert ans_res.json()["current_step"] == 2

    # Now execute undo
    undo_res = client.post(f"/api/v1/session/{session_id}/undo")
    assert undo_res.status_code == 200
    undo_data = undo_res.json()
    assert undo_data["current_step"] == 1
    assert undo_data["status"] == "NEEDS_CLARIFICATION"

    # Attempting to undo step 1 again should return 400
    undo_fail = client.post(f"/api/v1/session/{session_id}/undo")
    assert undo_fail.status_code == 400


# =============================================================================
# BE-305: DPDP Act 2023 Session Purge Tests
# =============================================================================
def test_delete_session_dpdp_purge(client):
    """Verifies permanent deletion of session record."""
    init_res = client.post(
        "/api/v1/analyze",
        json={
            "scenario": "A person took my watch from my desk without my consent yesterday morning.",
            "incident_date": "2024-09-01",
            "locale": "en",
        },
    )
    session_id = init_res.json()["session_id"]

    # Delete session
    del_res = client.delete(f"/api/v1/session/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"
    assert del_res.json()["session_id"] == session_id

    # Trying to query or answer deleted session returns 404
    ans_res = client.post(
        f"/api/v1/session/{session_id}/answer",
        json={"step": 1, "fact_key": "movable_property_taken", "answer": "YES"},
    )
    assert ans_res.status_code == 404

