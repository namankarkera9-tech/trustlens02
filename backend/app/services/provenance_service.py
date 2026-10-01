"""C2PA inspection through the optional open-source c2patool CLI."""

import json
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

from app.services.evidence_service import make_evidence


def inspect_provenance(path: str) -> Tuple[Dict[str, Any], List[Any]]:
    executable = shutil.which("c2patool")
    if not executable:
        outcome = {
            "status": "inspection_unavailable",
            "tool": None,
            "message": "c2patool is not installed; provenance could not be inspected.",
        }
        return outcome, [make_evidence(
            source="c2pa",
            evidence_type="provenance_unavailable",
            category="provenance",
            observation=outcome["message"],
            strength="informational",
            uncertainty="high",
            supporting_data={"status": outcome["status"], "note": "No conclusion about authenticity can be drawn."},
        )]

    try:
        completed = subprocess.run(
            [executable, path, "--json"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        outcome = {"status": "inspection_unavailable", "tool": "c2patool", "message": str(exc)}
        return outcome, [make_evidence(
            source="c2pa", evidence_type="provenance_unavailable", category="provenance",
            observation="C2PA inspection could not complete.", strength="informational", uncertainty="high",
            supporting_data={"status": outcome["status"]},
        )]

    payload: Dict[str, Any] = {}
    try:
        candidate = json.loads(completed.stdout or "{}")
        if isinstance(candidate, dict):
            payload = candidate
    except json.JSONDecodeError:
        payload = {}

    output_text = "{} {}".format(completed.stdout, completed.stderr).lower()
    if completed.returncode != 0 and any(term in output_text for term in ("no manifest", "no c2pa", "not found", "not present")):
        outcome = {"status": "not_found", "tool": "c2patool", "message": "No C2PA manifest was found."}
        evidence = [make_evidence(
            source="c2pa", evidence_type="provenance_absent", category="provenance",
            observation="No C2PA provenance manifest was found by c2patool.", strength="informational", uncertainty="low",
            supporting_data={"status": "not_found", "note": "No C2PA is not proof of manipulation."},
        )]
        return outcome, evidence
    if completed.returncode != 0 and not payload:
        outcome = {"status": "inspection_unavailable", "tool": "c2patool", "message": "c2patool returned an unreadable or unsupported result."}
        return outcome, [make_evidence(
            source="c2pa", evidence_type="provenance_unavailable", category="provenance",
            observation=outcome["message"], strength="informational", uncertainty="high",
            supporting_data={"status": outcome["status"]},
        )]

    validation = payload.get("validation_status", payload.get("validationStatus", {}))
    validation_text = json.dumps(validation, ensure_ascii=False).lower()
    has_manifest = bool(payload.get("active_manifest") or payload.get("activeManifest") or payload.get("manifests"))
    if not has_manifest and (completed.returncode != 0 or "no manifest" in output_text):
        status = "not_found"
        observation = "No C2PA provenance manifest was found by c2patool."
    elif "invalid" in validation_text or "error" in validation_text or "failure" in validation_text:
        status = "verification_issue"
        observation = "C2PA data was present, but the tool reported a validation issue."
    elif has_manifest and completed.returncode == 0:
        status = "verified"
        observation = "c2patool reported a valid C2PA manifest. This verifies the signed manifest, not every claim about the depicted scene."
    else:
        status = "inspection_unavailable"
        observation = "c2patool output did not establish a verifiable C2PA status."

    outcome = {
        "status": status,
        "tool": "c2patool",
        "message": observation,
        "validation_status": validation,
        "active_manifest": payload.get("active_manifest", payload.get("activeManifest")),
        "manifest_count": len(payload.get("manifests", {})) if isinstance(payload.get("manifests"), dict) else None,
    }
    evidence = [make_evidence(
        source="c2pa",
        evidence_type="provenance_observation",
        category="provenance",
        observation=observation,
        strength="moderate" if status in ("verified", "verification_issue") else "informational",
        uncertainty="low" if status in ("verified", "not_found") else "high",
        supporting_data={
            "status": status,
            "validation_status": validation,
            "signal": "concern" if status == "verification_issue" else "consistent" if status == "verified" else "neutral",
            "note": "A valid C2PA manifest verifies a signed provenance record, not every claim about the depicted scene.",
        },
    )]
    return outcome, evidence
