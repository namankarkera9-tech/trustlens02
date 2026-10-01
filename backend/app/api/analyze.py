"""Upload and analysis job endpoints."""

import os
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app import db
from app.services.analysis_service import run_analysis
from app.services.upload_service import stage_upload

router = APIRouter(prefix="/api/analyze", tags=["analysis"])


def _run_background(analysis_id: str, path: str, filename: str, content_type: str, media_kind: str) -> None:
    try:
        run_analysis(analysis_id, path, filename, content_type, media_kind)
    except Exception:
        # Failure details are stored safely on the job; do not log media or secrets.
        return


@router.post("")
async def analyze_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> Dict[str, Any]:
    filename = Path(file.filename or "upload").name
    content_type = file.content_type or "application/octet-stream"
    path = ""
    try:
        path, media_kind, expected_mime = await run_in_threadpool(stage_upload, file, filename, content_type)
    finally:
        await file.close()
    analysis_id = str(uuid.uuid4())
    try:
        db.create_analysis(analysis_id, filename, expected_mime)
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    background_tasks.add_task(_run_background, analysis_id, path, filename, expected_mime, media_kind)
    return {
        "id": analysis_id,
        "analysis_id": analysis_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "message": "Upload validated. Analysis has been queued.",
    }


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str) -> Dict[str, Any]:
    job = db.get_analysis(analysis_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if job.get("result") is not None:
        return job["result"]
    response = {
        "id": job["id"],
        "analysis_id": job["id"],
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
        "filename": job["filename"],
        "content_type": job["content_type"],
    }
    if job.get("error"):
        response["error"] = job["error"]
        response["message"] = job["error"]
    return response


@router.get("/{analysis_id}/evidence")
def get_analysis_evidence(analysis_id: str) -> Dict[str, Any]:
    job = db.get_analysis(analysis_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Evidence is not ready yet.")
    return {"id": analysis_id, "evidence": db.get_evidence(analysis_id)}


@router.get("/{analysis_id}/timeline")
def get_analysis_timeline(analysis_id: str) -> Dict[str, Any]:
    job = db.get_analysis(analysis_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Timeline is not ready yet.")
    result = job["result"]
    return {"id": analysis_id, "timeline": result.get("timeline", [])}
