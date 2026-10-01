"""Helpers to normalize heterogeneous tool output to the TrustLens evidence schema."""

from typing import Any, Dict, Optional

from app.schemas.evidence import EvidenceRecord


def make_evidence(
    source: str,
    evidence_type: str,
    category: str,
    observation: str,
    strength: str = "informational",
    uncertainty: str = "medium",
    timestamp: Optional[float] = None,
    value: Any = None,
    supporting_data: Optional[Dict[str, Any]] = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        source=source,
        type=evidence_type,
        category=category,
        timestamp=timestamp,
        observation=observation,
        value=value,
        strength=strength,
        uncertainty=uncertainty,
        supporting_data=supporting_data or {},
    )
