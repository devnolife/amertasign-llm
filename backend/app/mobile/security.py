"""Keamanan: hash password (bcrypt) & token JWT untuk API mobile."""
from __future__ import annotations

import secrets
import time

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + settings.access_token_minutes * 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Kembalikan user_id bila token valid, selain itu None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def refresh_token_expiry() -> float:
    return time.time() + settings.refresh_token_days * 86400
