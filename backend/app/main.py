"""TrustLens FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.api.analyze import router as analyze_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env", override=False)

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.initialize_database()
    yield


app = FastAPI(
    title="TrustLens AI API",
    description="Evidence-first multimodal media verification prototype.",
    version="1.0.0",
    lifespan=lifespan,
)

origins: List[str] = [
    item.strip()
    for item in os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(reports_router)


@app.get("/")
def root() -> dict:
    return {"service": "TrustLens AI API", "docs": "/docs", "health": "/api/health"}
