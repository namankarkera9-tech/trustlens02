"""Conservative deterministic evidence fusion with explicit conflicts and limitations."""

from typing import Any, Dict, List, Tuple

from app.schemas.evidence import EvidenceRecord, FusionResult, TrustState


def _direction(record: EvidenceRecord) -> str:
    direction = record.supporting_data.get("signal")
    if direction in ("concern", "consistent"):
        return str(direction)
    if record.source == "gemini":
        return str(record.supporting_data.get("signal", "neutral"))
    return "neutral"


def fuse_evidence(records: List[EvidenceRecord], provenance: Dict[str, Any], gemini_status: str) -> FusionResult:
    concern = [item for item in records if _direction(item) == "concern" and item.strength in ("moderate", "strong")]
    consistent = [item for item in records if _direction(item) == "consistent" and item.strength in ("moderate", "strong")]
    concern_sources = {item.source for item in concern}
    consistent_sources = {item.source for item in consistent}
    conflicts: List[str] = []
    limitations: List[str] = []

    if concern and consistent:
        conflicts.append("Some evidence sources reported concerning signals while others reported consistent observations.")
    if len(concern_sources) == 1 and len(concern) > 1:
        limitations.append("Multiple observations from one source are not independent corroboration.")
    if gemini_status != "completed":
        limitations.append("Gemini multimodal observations were unavailable; no AI observations were fabricated.")
    if provenance.get("status") in ("not_found", "inspection_unavailable"):
        limitations.append("C2PA provenance was absent or could not be inspected; this does not imply manipulation.")
    if any(item.uncertainty == "high" for item in records):
        limitations.append("At least one evidence source reported high uncertainty or a restricted inspection scope.")

    # State thresholds require source-independent agreement. Tool availability and
    # missing metadata never count as manipulation evidence or authenticating evidence.
    if len(concern_sources) >= 2 and not consistent_sources:
        state = TrustState.HIGH_RISK
        summary = "At least two independent evidence sources reported moderate or strong concerns."
        explanation = "Multiple independent sources reported specific concerning observations. This raises manipulation risk but is not a definitive authenticity verdict; review the individual observations and verify the media through independent sources."
        supporting = [item.id for item in concern]
    elif len(consistent_sources) >= 2 and not concern_sources and not conflicts:
        state = TrustState.CONSISTENT
        summary = "At least two independent sources reported consistent observations, with no material disagreement recorded."
        explanation = "The available independent observations are broadly consistent. This does not prove that the media is authentic, and the limitations below still apply."
        supporting = [item.id for item in consistent]
    else:
        state = TrustState.INSUFFICIENT
        if concern and consistent:
            summary = "Evidence sources disagree; the system is preserving that conflict rather than forcing a verdict."
            explanation = "Some observations raise concerns while other evidence is consistent or inconclusive. The disagreement prevents a well-supported conclusion. Review the source-level details and verify the media independently."
        elif concern:
            summary = "A concern was observed, but independent corroboration is insufficient for a high-risk state."
            explanation = "At least one source raised a concern, but the available evidence does not meet the conservative threshold for an elevated manipulation-risk state. This remains inconclusive."
        else:
            summary = "The available evidence is too limited to support a consistent or high-risk state."
            explanation = "The inspected sources did not provide enough independent, conclusive evidence for a stronger state. Missing metadata, absent provenance, and AI confidence are not treated as proof."
        supporting = [item.id for item in concern + consistent]

    if not records:
        limitations.append("No normalized evidence records were returned by the inspection services.")
    return FusionResult(
        trust_state=state,
        summary=summary,
        explanation=explanation,
        conflicts=conflicts,
        limitations=list(dict.fromkeys(limitations)),
        supporting_evidence_ids=supporting,
    )
