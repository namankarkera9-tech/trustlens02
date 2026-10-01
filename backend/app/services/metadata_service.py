"""Metadata extraction through ExifTool, with Pillow fallback for images."""

import json
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

from app.services.evidence_service import make_evidence


USEFUL_KEYS = {
    "Make", "Model", "CreateDate", "DateTimeOriginal", "ModifyDate", "Software",
    "ImageWidth", "ImageHeight", "ExifImageWidth", "ExifImageHeight", "GPSLatitude",
    "GPSLongitude", "GPSPosition", "Orientation", "FileType", "MIMEType", "Duration",
    "VideoFrameRate", "CompressorName", "CodecID", "MajorBrand",
}


def _extract_exiftool(path: str) -> Dict[str, Any]:
    executable = shutil.which("exiftool")
    if not executable:
        return {}
    completed = subprocess.run(
        [executable, "-json", "-G1", "-s", path],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        return {}
    try:
        parsed = json.loads(completed.stdout)
        if not parsed or not isinstance(parsed[0], dict):
            return {}
        metadata = parsed[0]
    except (json.JSONDecodeError, TypeError):
        return {}
    result: Dict[str, Any] = {}
    for key, value in metadata.items():
        short_key = key.rsplit(":", 1)[-1]
        if short_key in USEFUL_KEYS and value not in (None, ""):
            result[short_key] = value
    return result


def _extract_pillow(path: str) -> Dict[str, Any]:
    from PIL import Image, ExifTags

    result: Dict[str, Any] = {}
    with Image.open(path) as image:
        result["ImageWidth"] = image.width
        result["ImageHeight"] = image.height
        result["MIMEType"] = Image.MIME.get(image.format, "")
        exif = image.getexif()
        for tag_id, value in exif.items():
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if name in USEFUL_KEYS and isinstance(value, (str, int, float)):
                result[name] = value
    return result


def extract_metadata(path: str, media_kind: str) -> Tuple[Dict[str, Any], List[Any], str]:
    try:
        metadata = _extract_exiftool(path)
    except (OSError, subprocess.SubprocessError):
        metadata = {}
    extractor = "ExifTool" if metadata else "Pillow" if media_kind == "image" else "unavailable"
    if not metadata and media_kind == "image":
        try:
            metadata = _extract_pillow(path)
        except Exception:
            metadata = {}
    evidence = []
    if metadata:
        for key, value in metadata.items():
            sensitive = key.startswith("GPS")
            evidence.append(
                make_evidence(
                    source="metadata",
                    evidence_type="metadata_observation",
                    category="metadata",
                    observation="{} is present in the file metadata.".format(key),
                    value=value,
                    strength="informational",
                    uncertainty="low",
                    supporting_data={"field": key, "note": "Metadata describes recorded file properties; it does not establish authenticity."},
                )
            )
            if sensitive:
                evidence[-1].supporting_data["sensitive_location"] = True
    else:
        evidence.append(
            make_evidence(
                source="metadata",
                evidence_type="metadata_unavailable",
                category="metadata",
                observation="No useful metadata fields were extracted by the available tools.",
                strength="informational",
                uncertainty="high",
                supporting_data={"note": "Missing metadata is not proof of manipulation."},
            )
        )
    return metadata, evidence, extractor
