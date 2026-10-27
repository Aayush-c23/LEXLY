"""
Pydantic Schemas for Scenario Intake & Emergency Analysis (Phase 3).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Scenario submission payload."""
    scenario: str = Field(
        ...,
        min_length=20,
        max_length=2000,
        description="Unstructured natural language incident narrative (20 to 2000 characters).",
        examples=["A person broke into my locked house yesterday and stole my laptop while I was at work."],
    )
    incident_date: Optional[str] = Field(
        default=None,
        description="Date of the incident in YYYY-MM-DD format (used to determine BNS vs IPC regime).",
        examples=["2024-08-15"],
    )
    locale: str = Field(
        default="en",
        description="Preferred language for clarification questions ('en' or 'hi').",
        examples=["en"],
    )

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str) -> str:
        loc = v.lower().strip()
        if loc not in ("en", "hi"):
            return "en"
        return loc


class HelplineInfo(BaseModel):
    """Emergency statutory helpline entry."""
    name: str
    number: str
    description: str


class EmergencyResponse(BaseModel):
    """Emergency interception response payload."""
    status: str = "EMERGENCY_INTERCEPTION"
    helplines: List[HelplineInfo]
    advisory: str


class ClarificationQuestion(BaseModel):
    """Dynamic Shannon Information-Gain clarification question."""
    fact_key: str
    question_text: str
    observable_proxy_hint: Optional[str] = None
    category: Optional[str] = None
    information_gain_bits: Optional[float] = None


class ProvisionResult(BaseModel):
    """Grounded statutory provision result."""
    provision_id: int
    section_number: str
    act_name: str
    primary_citation: str
    cross_reference_citation: str
    title: str
    plain_summary: str
    punishment: str
    is_cognizable: bool
    is_bailable: bool
    compoundable_type: str
    triable_by: str
    posterior_probability: float
    matched_facts: Dict[str, str] = Field(default_factory=dict)


class LesserOffenceResult(BaseModel):
    """Subsidiary or lesser-included offence from hierarchy graph."""
    provision_id: int
    section_number: str
    title: str
    relation_type: str


class AnalyzeResponse(BaseModel):
    """Unified response for scenario intake endpoint."""
    status: str = Field(
        ...,
        description="'EMERGENCY_INTERCEPTION', 'NEEDS_CLARIFICATION', or 'COMPLETED'",
    )
    session_id: Optional[str] = None
    primary_legal_regime: Optional[str] = None  # 'BNS' or 'IPC'
    current_step: Optional[int] = None
    max_steps: int = 5
    question: Optional[ClarificationQuestion] = None
    remaining_candidates_count: Optional[int] = None
    provisions: Optional[List[ProvisionResult]] = None
    lesser_offences: Optional[List[LesserOffenceResult]] = None
    helplines: Optional[List[HelplineInfo]] = None
    advisory: Optional[str] = None
    audit_trail: Optional[List[Dict[str, Any]]] = None
