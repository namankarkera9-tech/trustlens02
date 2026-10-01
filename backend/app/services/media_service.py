"""Bounded FFmpeg/ffprobe and OpenCV media inspection and video frame sampling."""

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.evidence_service import make_evidence

MAX_SAMPLED_FRAMES = 8
MAX_VIDEO_SECONDS = 90.0


def _run_ffprobe(path: str) -> Optional[Dict[str, Any]]:
    executable = shutil.which("ffprobe")
    if not executable:
        return None
    completed = subprocess.run(
        [executable, "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def _probe_video_with_cv2(path: str) -> Dict[str, Any]:
    import cv2  # type: ignore

    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        capture.release()
        raise ValueError("The video could not be opened by OpenCV.")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()
    return {
        "duration": frame_count / fps if fps > 0 else None,
        "width": width,
        "height": height,
        "frame_rate": fps or None,
        "frame_count": frame_count or None,
        "video_codec": None,
        "container": Path(path).suffix.lstrip(".").lower(),
        "streams": [{"codec_type": "video"}],
        "inspection_tool": "OpenCV",
    }


def _normalize_probe(payload: Dict[str, Any], path: str) -> Dict[str, Any]:
    streams = payload.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    stream = video_streams[0] if video_streams else {}
    fmt = payload.get("format", {})
    duration_value = stream.get("duration") or fmt.get("duration")
    try:
        duration = float(duration_value) if duration_value is not None else None
    except (TypeError, ValueError):
        duration = None
    fps_value = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    fps = None
    if isinstance(fps_value, str) and "/" in fps_value:
        numerator, denominator = fps_value.split("/", 1)
        try:
            fps = float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            fps = None
    return {
        "duration": duration,
        "width": stream.get("width"),
        "height": stream.get("height"),
        "frame_rate": fps,
        "frame_count": stream.get("nb_frames"),
        "video_codec": stream.get("codec_name"),
        "audio_codec": next((item.get("codec_name") for item in streams if item.get("codec_type") == "audio"), None),
        "container": fmt.get("format_name", Path(path).suffix.lstrip(".")),
        "size_bytes": fmt.get("size"),
        "streams": [{"codec_type": item.get("codec_type"), "codec_name": item.get("codec_name")} for item in streams],
        "inspection_tool": "FFmpeg/ffprobe",
    }


def _timestamps(duration: float) -> List[float]:
    if duration <= 0:
        return [0.0]
    count = min(MAX_SAMPLED_FRAMES, max(1, int(math.ceil(duration / 3.0))))
    if count == 1:
        return [min(duration / 2.0, 1.0)]
    return [duration * index / (count - 1) for index in range(count)]


def _extract_frames_ffmpeg(path: str, timestamps: List[float]) -> List[Tuple[float, bytes]]:
    executable = shutil.which("ffmpeg")
    if not executable:
        return []
    frames: List[Tuple[float, bytes]] = []
    with tempfile.TemporaryDirectory(prefix="trustlens-frames-") as directory:
        for index, timestamp in enumerate(timestamps):
            output = str(Path(directory) / "frame-{}.jpg".format(index))
            completed = subprocess.run(
                [executable, "-v", "error", "-ss", "{:.3f}".format(timestamp), "-i", path, "-frames:v", "1", "-vf", "scale='min(960,iw)':-2", "-y", output],
                capture_output=True,
                timeout=15,
                check=False,
            )
            if completed.returncode == 0 and Path(output).is_file():
                frames.append((timestamp, Path(output).read_bytes()))
    return frames


def _extract_frames_cv2(path: str, timestamps: List[float]) -> List[Tuple[float, bytes]]:
    try:
        import cv2  # type: ignore
    except ImportError:
        return []
    capture = cv2.VideoCapture(path)
    frames: List[Tuple[float, bytes]] = []
    for timestamp in timestamps:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = capture.read()
        if ok:
            height, width = frame.shape[:2]
            scale = min(1.0, 960.0 / max(width, 1))
            if scale < 1.0:
                frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
            encoded, buffer = cv2.imencode(".jpg", frame)
            if encoded:
                frames.append((timestamp, buffer.tobytes()))
    capture.release()
    return frames


def _opencv_evidence(path: str, media_kind: str, frames: List[Tuple[float, bytes]]) -> List[Any]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return [make_evidence(
            source="opencv", evidence_type="processing_unavailable", category="media_processing",
            observation="OpenCV is not installed; image-statistics and frame-difference signals were unavailable.",
            strength="informational", uncertainty="high",
        )]

    evidence = []
    if media_kind == "image":
        image = cv2.imread(path)
        if image is None:
            return [make_evidence(source="opencv", evidence_type="processing_unavailable", category="media_processing", observation="OpenCV could not decode the image.", uncertainty="high")]
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        evidence.append(make_evidence(
            source="opencv", evidence_type="image_statistics", category="media_processing",
            observation="OpenCV decoded an image of {} × {} pixels; blur statistic is recorded as a basic quality signal.".format(width, height),
            value={"width": width, "height": height, "laplacian_variance": round(blur_score, 3)},
            strength="informational", uncertainty="high",
            supporting_data={"note": "Blur and dimensions are not forensic proof of editing or authenticity."},
        ))
    else:
        previous = None
        for timestamp, frame_bytes in frames:
            array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
            if frame is None:
                continue
            if previous is not None:
                resized = cv2.resize(frame, (previous.shape[1], previous.shape[0]))
                difference = float(cv2.absdiff(previous, resized).mean())
                if difference >= 45.0:
                    evidence.append(make_evidence(
                        source="opencv", evidence_type="frame_difference", category="temporal",
                        timestamp=timestamp,
                        observation="A large visual difference was measured between adjacent sampled frames (mean pixel difference {:.1f}/255).".format(difference),
                        value=round(difference, 3), strength="weak", uncertainty="high",
                        supporting_data={"signal": "neutral", "note": "Scene changes and camera motion can produce this signal; it is not proof of manipulation."},
                    ))
            previous = frame
        if not evidence:
            evidence.append(make_evidence(
                source="opencv", evidence_type="sampled_frame_statistics", category="temporal",
                observation="OpenCV decoded {} sampled video frame(s); no large adjacent-frame difference exceeded the conservative threshold.".format(len(frames)),
                value={"sampled_frames": len(frames)}, strength="weak", uncertainty="high",
                supporting_data={"signal": "neutral", "note": "Sparse sampling cannot rule out edits or establish authenticity."},
            ))
    return evidence


def inspect_media(path: str, media_kind: str) -> Tuple[Dict[str, Any], List[Tuple[float, bytes]], List[Any]]:
    if media_kind == "image":
        from PIL import Image

        with Image.open(path) as image:
            media_info: Dict[str, Any] = {
                "kind": "image",
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "inspection_tool": "Pillow",
            }
        evidence = _opencv_evidence(path, media_kind, [])
        return media_info, [], evidence

    probe = _run_ffprobe(path)
    if probe is not None:
        media_info = _normalize_probe(probe, path)
    else:
        try:
            media_info = _probe_video_with_cv2(path)
        except (ImportError, ValueError) as exc:
            raise RuntimeError("Video media inspection requires ffprobe or OpenCV: {}".format(exc)) from exc
    media_info["kind"] = "video"
    duration = float(media_info.get("duration") or 0.0)
    try:
        max_duration = max(1.0, float(os.getenv("MAX_VIDEO_SECONDS", str(MAX_VIDEO_SECONDS))))
    except ValueError:
        max_duration = MAX_VIDEO_SECONDS
    if duration > max_duration:
        raise RuntimeError("The clip is {:.1f} seconds long; the configured limit is {:.0f} seconds.".format(duration, max_duration))
    sample_times = _timestamps(duration)
    frames = _extract_frames_ffmpeg(path, sample_times)
    if len(frames) < 1:
        frames = _extract_frames_cv2(path, sample_times)
    if not frames:
        raise RuntimeError("The video was readable, but no sampled frame could be extracted with FFmpeg or OpenCV.")
    evidence = _opencv_evidence(path, media_kind, frames)
    for timestamp, _ in frames:
        evidence.append(make_evidence(
            source="ffmpeg" if shutil.which("ffmpeg") else "opencv",
            evidence_type="sampled_frame",
            category="temporal",
            timestamp=timestamp,
            observation="A frame was sampled at {:.2f} seconds for visual analysis.".format(timestamp),
            value={"timestamp": timestamp},
            strength="informational",
            uncertainty="low",
            supporting_data={"sampled_frames_total": len(frames)},
        ))
    return media_info, frames, evidence
