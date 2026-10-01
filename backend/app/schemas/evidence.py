"""Canonical evidence and fused-result models shared by all backend services."""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TrustState(str, Enum):
    CONSISTENT = "CONSISTENT EVIDENCE"
    INSUFFICIENT = "INSUFFICIENT / CONFLICTING"
    HIGH_RISK = "HIGH MANIPULATION RISK"


class EvidenceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    type: str
    category: str
    timestamp: Optional[float] = None
    observation: str
    value: Optional[Any] = None
    strength: str = "informational"
    uncertainty: str = "medium"
    supporting_data: Dict[str, Any] = Field(default_factory=dict)


class FusionResult(BaseModel):
    trust_state: TrustState
    summary: str
    explanation: str
    conflicts: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    id: str
    status: str
    stage: str
    progress: int = 0
    message: str = ""
    filename: Optional[str] = None
    content_type: Optional[str] = None
    media_kind: Optional[str] = None
    trust_state: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    media_info: Dict[str, Any] = Field(default_factory=dict)
    gemini: Dict[str, Any] = Field(default_factory=dict)
