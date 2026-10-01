from fastapi import APIRouter

from app.services.gemini_service import is_configured, model_name

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "gemini_configured": is_configured(),
        "gemini_model": model_name() if is_configured() else None,
    }
