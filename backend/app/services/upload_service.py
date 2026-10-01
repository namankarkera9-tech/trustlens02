"""Safe upload validation and short-lived media staging."""

import os
import tempfile
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


EXTENSION_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".webm": "video/webm",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


def max_upload_bytes() -> int:
    try:
        return max(1, int(os.getenv("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024))))
    except ValueError:
        return 100 * 1024 * 1024


def max_video_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("MAX_VIDEO_SECONDS", "90")))
    except ValueError:
        return 90.0


def validate_declaration(filename: str, content_type: str) -> Tuple[str, str]:
    extension = Path(filename).suffix.lower()
    expected = EXTENSION_TYPES.get(extension)
    if expected is None:
        raise HTTPException(status_code=415, detail="Unsupported file type. Use JPG, PNG, WEBP, GIF, MP4, MOV, or WEBM.")
    supplied = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if supplied not in ("application/octet-stream", expected):
        if not (extension in {".jpg", ".jpeg"} and supplied == "image/jpg"):
            raise HTTPException(status_code=415, detail="The file extension and declared media type do not match.")
    kind = "image" if extension in IMAGE_EXTENSIONS else "video"
    return kind, expected


def _validate_image(path: str) -> None:
    try:
        with Image.open(path) as image:
            if image.width * image.height > 100_000_000:
                raise HTTPException(status_code=413, detail="The image dimensions exceed the safe processing limit.")
            image.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="The uploaded image is malformed or unreadable.") from exc


def _validate_video(path: str) -> None:
    """Verify video readability using ffprobe, then OpenCV as an optional fallback."""
    import json
    import shutil
    import subprocess

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            completed = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", path],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            payload = json.loads(completed.stdout or "{}")
            has_video = any(stream.get("codec_type") == "video" for stream in payload.get("streams", []))
            if completed.returncode != 0 or not has_video:
                raise HTTPException(status_code=422, detail="The uploaded video is malformed or contains no video stream.")
            duration = float(payload.get("format", {}).get("duration") or 0.0)
            if duration > max_video_seconds():
                raise HTTPException(status_code=413, detail="The video exceeds the configured {:.0f}-second duration limit.".format(max_video_seconds()))
            return
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=422, detail="The video could not be inspected within the allowed time.") from exc
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="The uploaded video could not be read.") from exc
    try:
        import cv2  # type: ignore

        capture = cv2.VideoCapture(path)
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frame_rate = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        readable = capture.isOpened() and frame_count > 0
        capture.release()
        if not readable:
            raise HTTPException(status_code=422, detail="The uploaded video is malformed or unreadable.")
        if frame_rate > 0 and frame_count / frame_rate > max_video_seconds():
            raise HTTPException(status_code=413, detail="The video exceeds the configured {:.0f}-second duration limit.".format(max_video_seconds()))
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Video validation is unavailable: install FFmpeg (ffprobe) or opencv-python-headless on the backend.",
        ) from exc


def validate_media(path: str, filename: str, content_type: str) -> Tuple[str, str]:
    kind, expected_mime = validate_declaration(filename, content_type)
    if kind == "image":
        _validate_image(path)
    else:
        _validate_video(path)
    return kind, expected_mime


def stage_upload(upload: UploadFile, filename: str, content_type: str) -> Tuple[str, str, str]:
    kind, expected_mime = validate_declaration(filename, content_type)
    suffix = Path(filename).suffix.lower()
    file_descriptor, path = tempfile.mkstemp(prefix="trustlens-", suffix=suffix)
    size = 0
    try:
        with os.fdopen(file_descriptor, "wb") as output:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_upload_bytes():
                    limit_mb = max_upload_bytes() / (1024 * 1024)
                    raise HTTPException(status_code=413, detail="The file exceeds the configured {:.1f} MB upload limit.".format(limit_mb))
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="The uploaded file is empty.")
        validate_media(path, filename, content_type)
        return path, kind, expected_mime
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
