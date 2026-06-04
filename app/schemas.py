"""Pydantic schemas: the shared response contract.

Every substantive answer ParaPilot returns is an ``AnswerEnvelope`` carrying
citations, a confidence score, the standing disclaimer, ``is_legal_information``,
and an escalation block, the SPEC §6 UPL/safety contract.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AnswerKind(str, Enum):
    """How an answer was produced."""

    GROUNDED = "grounded"          # supported by retrieved corpus chunks
    REFUSAL_SCOPE = "refusal_scope"        # out of scope (non-IL / non-divorce)
    REFUSAL_ADVICE = "refusal_advice"      # advice-seeking ("what should I do")
    REFUSAL_LOW_CONFIDENCE = "refusal_low_confidence"  # no grounded answer found


class Citation(BaseModel):
    """A clickable pointer back to an authoritative source chunk."""

    marker: str = Field(..., description="Inline marker, e.g. '1'.")
    source_id: str
    chunk_id: str
    title: str
    url: str
    publisher: str
    retrieved: str
    snippet: str = Field(..., description="Short supporting excerpt from the source.")


class Escalation(BaseModel):
    """Where to get real legal help. Always present."""

    message: str = (
        "For advice about your specific situation, contact a licensed Illinois "
        "attorney or legal aid."
    )
    legal_aid_name: str = "Illinois Legal Aid Online (ILAO)"
    legal_aid_url: str = "https://www.illinoislegalaid.org/get-legal-help"
    lawyer_finder_name: str = "Illinois Lawyer Finder (ISBA)"
    lawyer_finder_url: str = "https://www.isba.org/public/illinoislawyerfinder"


class AnswerEnvelope(BaseModel):
    """The single response shape returned by the Ask endpoint."""

    kind: AnswerKind
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    is_legal_information: bool = True
    disclaimer: str
    escalation: Escalation = Field(default_factory=Escalation)
    provider: str = "stub"

    @property
    def is_refusal(self) -> bool:
        return self.kind != AnswerKind.GROUNDED


class RetrievedChunk(BaseModel):
    """A retrieval hit (internal)."""

    source_id: str
    chunk_id: str
    title: str
    url: str
    publisher: str
    retrieved: str
    heading: str
    text: str
    score: float
