"""Analyzer interfaces and the structured output contract.

The analyzer receives a target passage plus pre-retrieved evidence candidates
(each with an `evidence_id`). It must reference only those ids. Output is
validated against a strict schema; unknown/foreign ids are rejected before
anything is persisted (see apps.analysis.services).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

from apps.common.constants import FindingStatus

VALID_STATUSES = {c.value for c in FindingStatus}


@dataclass
class EvidenceCandidate:
    evidence_id: str
    document_id: str
    filename: str
    page_number: int | None
    text: str
    score: float
    match_source: str = "semantic"  # semantic | exact | fuzzy


class AIAssessment(BaseModel):
    status: str
    explanation: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    needs_human_review: bool = False

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"Unknown status: {v}")
        return v


class AIWritingNote(BaseModel):
    category: str
    severity: str = "info"
    message: str = Field(min_length=1, max_length=1000)
    suggestion: str = ""


class Analyzer(abc.ABC):
    name: str = "base"
    version: str = "0"

    @abc.abstractmethod
    def assess_claim(self, *, claim_text: str, candidates: list[EvidenceCandidate]) -> AIAssessment: ...

    @abc.abstractmethod
    def review_writing(self, *, text: str) -> list[AIWritingNote]: ...


@dataclass
class AnalyzerMetadata:
    name: str
    version: str
    provider: str
    field_extra: dict = field(default_factory=dict)
