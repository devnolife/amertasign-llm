"""Entry point FastAPI untuk amertasign-llm backend."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.mobile.db import init_db
from app.mobile.deps import ApiError
from app.mobile.sign_media import sync_sign_media_dictionary
from app.routers import (
    compose,
    data,
    health,
    mobile_auth,
    mobile_dictionary,
    mobile_history,
    mobile_translation,
    mobile_users,
    recognize,
    train,
)

app = FastAPI(title=settings.app_name, debug=settings.debug)
init_db()
if settings.auto_sync_sign_media:
    sync_sign_media_dictionary()


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(recognize.router)
app.include_router(data.router)
app.include_router(train.router)
app.include_router(compose.router)

# API mobile (React Native / Expo) — lihat mobile.md
app.include_router(mobile_auth.router)
app.include_router(mobile_history.router)
app.include_router(mobile_dictionary.router)
app.include_router(mobile_translation.router)
app.include_router(mobile_users.router)

# Media peraga hasil scripts/build_sign_media.py. Folder selalu dibuat agar
# backend tetap bisa start sebelum proses build media pertama.
sign_media_dir = settings.data_dir / "public" / "sign_media"
sign_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/v1/media", StaticFiles(directory=sign_media_dir), name="sign-media")


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
