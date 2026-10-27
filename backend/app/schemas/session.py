"""
Pydantic Schemas for Interactive Clarification Session Endpoints (Phase 3).
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from backend.app.schemas.analyze import (
    ClarificationQuestion,
    LesserOffenceResult,
    ProvisionResult,
)


class AnswerRequest(BaseModel):
    """User response to clarification inquiry question."""
    step: int = Field(..., ge=1, description="Current step index matching optimistic lock.")
    fact_key: str = Field(..., description="The statutory fact key being answered.")
    answer: Literal["YES", "NO", "NOT_SURE", "TRUE", "FALSE"] = Field(
        ...,
        description="User tri-state response: 'YES', 'NO', or 'NOT_SURE'.",
    )
    locale: str = Field(default="en", description="Preferred response locale ('en' or 'hi').")

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, v: str) -> str:
        val = v.upper().strip()
        if val in ("YES", "TRUE"):
            return "YES"
        if val in ("NO", "FALSE"):
            return "NO"
        return "NOT_SURE"


class AnswerResponse(BaseModel):
    """Zero-LLM fast path response payload."""
    status: Literal["NEEDS_CLARIFICATION", "COMPLETED"]
    session_id: str
    current_step: int
    max_steps: int = 5
    question: Optional[ClarificationQuestion] = None
    remaining_candidates_count: Optional[int] = None
    primary_legal_regime: Optional[str] = None
    provisions: Optional[List[ProvisionResult]] = None
    lesser_offences: Optional[List[LesserOffenceResult]] = None
    audit_trail: Optional[List[Dict[str, Any]]] = None


class UndoResponse(BaseModel):
    """Response returned upon reverting to the previous state."""
    status: str = "NEEDS_CLARIFICATION"
    session_id: str
    current_step: int
    question: Optional[ClarificationQuestion] = None
    remaining_candidates_count: Optional[int] = None
    message: str = "Reverted to previous inquiry step."


class DeleteSessionResponse(BaseModel):
    """Response returned upon DPDP Act right-to-erasure deletion."""
    status: str = "DELETED"
    session_id: str
    message: str = "Session and associated audit traces permanently erased."

