from app.schemas.evidence import EvidenceRecord, TrustState
from app.services.fusion_service import fuse_evidence


def make_record(source: str, signal: str, strength: str = "moderate") -> EvidenceRecord:
    return EvidenceRecord(
        source=source,
        type="test_observation",
        category="visual",
        observation="A test-only observation.",
        strength=strength,
        uncertainty="medium",
        supporting_data={"signal": signal},
    )


def test_high_risk_requires_independent_concern_sources() -> None:
    result = fuse_evidence(
        [make_record("gemini", "concern"), make_record("opencv", "concern")],
        {"status": "verified"},
        "completed",
    )
    assert result.trust_state is TrustState.HIGH_RISK


def test_single_source_concern_is_insufficient() -> None:
    result = fuse_evidence([make_record("gemini", "concern")], {"status": "not_found"}, "completed")
    assert result.trust_state is TrustState.INSUFFICIENT
    assert any("not proof" in item.lower() or "absent" in item.lower() for item in result.limitations)


def test_conflicting_sources_remain_visible() -> None:
    result = fuse_evidence(
        [make_record("gemini", "concern"), make_record("metadata", "consistent")],
        {"status": "verified"},
        "completed",
    )
    assert result.trust_state is TrustState.INSUFFICIENT
    assert result.conflicts


def test_consistent_state_needs_two_independent_sources() -> None:
    result = fuse_evidence(
        [make_record("gemini", "consistent"), make_record("opencv", "consistent")],
        {"status": "verified"},
        "completed",
    )
    assert result.trust_state is TrustState.CONSISTENT
