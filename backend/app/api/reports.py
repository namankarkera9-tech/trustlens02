"""Printable analysis report endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app import db
from app.services.report_service import render_pdf

router = APIRouter(prefix="/api/analyze", tags=["reports"])


@router.get("/{analysis_id}/report")
def get_report(analysis_id: str) -> dict:
    job = db.get_analysis(analysis_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="The report is not ready yet.")
    return job["result"]


@router.get("/{analysis_id}/report.pdf")
def get_report_pdf(analysis_id: str) -> Response:
    job = db.get_analysis(analysis_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="The report is not ready yet.")
    pdf = render_pdf(job["result"])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="trustlens-{}.pdf"'.format(analysis_id)},
    )
