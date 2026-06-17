"""Endpoint health & info."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    models = sorted(p.name for p in settings.models_dir.glob("*.joblib"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "models_available": models,
        "min_confidence": settings.min_confidence,
    }
