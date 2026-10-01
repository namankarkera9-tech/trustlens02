"""Analysis orchestration: metadata, C2PA, media tools, Gemini, normalization, fusion."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from app import db
from app.schemas.evidence import EvidenceRecord
from app.services import gemini_service
from app.services.fusion_service import fuse_evidence
from app.services.media_service import inspect_media
from app.services.metadata_service import extract_metadata
from app.services.provenance_service import inspect_provenance


def _serialize_records(records: List[EvidenceRecord]) -> List[Dict[str, Any]]:
    return [record.model_dump(mode="json") for record in records]


def _progress(analysis_id: str, stage: str, progress: int, message: str) -> None:
    db.update_analysis(analysis_id, status="processing", stage=stage, progress=progress)


def _safe_gemini_error(exc: Exception) -> str:
    """Map provider failures to safe messages without including request details or secrets."""
    message = str(exc).lower()
    if isinstance(exc, RuntimeError) and not any(code in message for code in ("503", "429", "401", "403", "404")):
        return str(exc)
    if "503" in message or "unavailable" in message or "high demand" in message:
        return "Gemini is temporarily unavailable (HTTP 503); the configured model is at high demand. Retry this analysis later."
    if "429" in message or "resource_exhausted" in message or "rate limit" in message:
        return "Gemini API quota or rate limit was reached. Check project quota and retry later."
    if "401" in message or "403" in message or "unauthenticated" in message or "permission_denied" in message:
        return "Gemini authorization failed. Check that the backend key is valid and has access to the configured model."
    if "404" in message or "not_found" in message:
        return "The configured Gemini model was not found or is unavailable to this API project. Choose an enabled model."
    return "The Gemini request failed ({}). Check the backend model configuration and service availability.".format(type(exc).__name__)


def run_analysis(analysis_id: str, path: str, filename: str, content_type: str, media_kind: str) -> Dict[str, Any]:
    records: List[EvidenceRecord] = []
    try:
        _progress(analysis_id, "metadata", 12, "Inspecting available file metadata.")
        metadata, metadata_evidence, metadata_tool = extract_metadata(path, media_kind)
        records.extend(metadata_evidence)

        _progress(analysis_id, "provenance", 25, "Checking C2PA provenance where a verifier is available.")
        provenance, provenance_evidence = inspect_provenance(path)
        records.extend(provenance_evidence)

        _progress(analysis_id, "media_processing", 40, "Inspecting media properties and sampling video frames.")
        media_info, frames, media_evidence = inspect_media(path, media_kind)
        records.extend(media_evidence)

        _progress(analysis_id, "gemini", 65, "Requesting structured multimodal observations from Gemini.")
        gemini_result: Dict[str, Any]
        gemini_status = "unavailable"
        if gemini_service.is_configured():
            try:
                media_bytes = b""
                if media_kind == "image":
                    with open(path, "rb") as media_file:
                        media_bytes = media_file.read()
                context = {
                    "metadata": metadata,
                    "provenance_status": provenance.get("status"),
                    "media_info": media_info,
                    "tool_observations": [
                        {"source": record.source, "type": record.type, "observation": record.observation, "timestamp": record.timestamp}
                        for record in records
                    ],
                }
                observations, model = gemini_service.analyze_media(
                    media_bytes=media_bytes,
                    mime_type=content_type,
                    context=context,
                    sampled_frames=frames if media_kind == "video" else None,
                )
                gemini_result = {
                    "provider": "Google Gemini API",
                    "configured": True,
                    "model": model,
                    "status": "completed",
                    **observations,
                }
                gemini_status = "completed"
                for observation in observations.get("observations", []):
                    records.append(EvidenceRecord(
                        source="gemini",
                        type="gemini_observation",
                        category=observation.get("category", "other"),
                        timestamp=observation.get("timestamp"),
                        observation=observation.get("observation", ""),
                        strength=observation.get("strength", "weak"),
                        uncertainty=observation.get("uncertainty", "medium"),
                        supporting_data={"signal": observation.get("signal", "neutral"), "provider": "Google Gemini API", "model": model},
                    ))
            except Exception as exc:
                # Deliberately do not persist exception repr/headers, which might contain secrets.
                safe_error = _safe_gemini_error(exc)
                gemini_result = {
                    "provider": "Google Gemini API",
                    "configured": True,
                    "model": gemini_service.model_name(),
                    "status": "error",
                    "error": safe_error,
                    "observations": [],
                    "limitations": [safe_error],
                }
        else:
            gemini_result = {
                "provider": "Google Gemini API",
                "configured": False,
                "model": gemini_service.model_name() or None,
                "status": "not_configured",
                "observations": [],
                "limitations": ["Set GEMINI_API_KEY and GEMINI_MODEL in backend/.env to enable a real API call."],
            }

        _progress(analysis_id, "evidence_fusion", 87, "Normalizing evidence and applying conservative fusion rules.")
        fusion = fuse_evidence(records, provenance, gemini_status)
        limitations = list(fusion.limitations)
        limitations.extend(str(item) for item in gemini_result.get("limitations", []))
        result: Dict[str, Any] = {
            "id": analysis_id,
            "status": "completed",
            "stage": "complete",
            "progress": 100,
            "filename": filename,
            "content_type": content_type,
            "media_kind": media_kind,
            "trust_state": fusion.trust_state.value,
            "state": fusion.trust_state.value,
            "summary": fusion.summary,
            "explanation": fusion.explanation,
            "evidence": _serialize_records(records),
            "conflicts": fusion.conflicts,
            "limitations": list(dict.fromkeys(limitations)),
            "timeline": [
                {
                    "id": record.id,
                    "timestamp": record.timestamp,
                    "source": record.source,
                    "category": record.category,
                    "title": record.type.replace("_", " ").title(),
                    "observation": record.observation,
                    "strength": record.strength,
                }
                for record in records if record.timestamp is not None
            ],
            "metadata": metadata,
            "metadata_tool": metadata_tool,
            "provenance": provenance,
            "media_info": media_info,
            "gemini": gemini_result,
            "fusion": fusion.model_dump(mode="json"),
        }
        db.replace_evidence(analysis_id, result["evidence"])
        db.update_analysis(analysis_id, status="completed", stage="complete", progress=100, result=result)
        return result
    except Exception as exc:
        safe_message = "Media analysis failed ({}). Verify FFmpeg/OpenCV installation and that the media can be decoded.".format(type(exc).__name__)
        db.update_analysis(analysis_id, status="failed", stage="failed", progress=100, error=safe_message)
        raise
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
