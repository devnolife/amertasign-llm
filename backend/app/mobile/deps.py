"""Dependency bersama API mobile: DB session, auth Bearer, rate limit, error format."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.mobile.db import SessionLocal
from app.mobile.models import User
from app.mobile.security import decode_access_token


class ApiError(Exception):
    """Error API dengan format {success:false, error:{code,message}}."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ApiError(401, "UNAUTHORIZED", "Token akses tidak ditemukan.")
    user_id = decode_access_token(auth[7:].strip())
    if not user_id:
        raise ApiError(401, "UNAUTHORIZED", "Token akses tidak valid atau kedaluwarsa.")
    user = db.get(User, user_id)
    if not user:
        raise ApiError(401, "UNAUTHORIZED", "User tidak ditemukan.")
    return user


# --- Rate limiting sederhana (in-memory) untuk endpoint auth ---
_attempts: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT = 5
_RATE_WINDOW = 60.0


def rate_limit_auth(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = time.time()
    q = _attempts[key]
    while q and now - q[0] > _RATE_WINDOW:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise ApiError(429, "RATE_LIMITED", "Terlalu banyak percobaan. Coba lagi sebentar.")
    q.append(now)


def ok(data: dict | list) -> dict:
    return {"success": True, "data": data}
