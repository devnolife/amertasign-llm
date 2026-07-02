"""Endpoint auth mobile: register, login, refresh, logout, me."""
from __future__ import annotations

import re
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.mobile.deps import ApiError, get_current_user, get_db, ok, rate_limit_auth
from app.mobile.models import RefreshToken, User
from app.mobile.security import (
    create_access_token,
    hash_password,
    new_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.mobile.serializers import user_to_dict

router = APIRouter(prefix="/api/v1/auth", tags=["mobile-auth"])

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,20}$")


class Credentials(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


def _issue_tokens(db: Session, user: User) -> dict:
    token = new_refresh_token()
    db.add(RefreshToken(token=token, user_id=user.id, expires_at=refresh_token_expiry()))
    db.commit()
    return {
        "user": user_to_dict(user),
        "accessToken": create_access_token(user.id),
        "refreshToken": token,
    }


@router.post("/register", dependencies=[Depends(rate_limit_auth)])
def register(body: Credentials, db: Session = Depends(get_db)) -> dict:
    username = body.username.strip().lower()
    if not USERNAME_RE.match(username):
        raise ApiError(
            400,
            "INVALID_USERNAME",
            "Username harus 3-20 karakter: huruf kecil, angka, titik, underscore, atau strip.",
        )
    if len(body.password) < 6:
        raise ApiError(400, "INVALID_PASSWORD", "Password minimal 6 karakter.")
    exists = db.scalar(select(User).where(User.username == username))
    if exists:
        raise ApiError(409, "USERNAME_TAKEN", "Username sudah dipakai.")

    user = User(
        username=username,
        password_hash=hash_password(body.password),
        name=username.replace(".", " ").replace("_", " ").replace("-", " ").title(),
    )
    db.add(user)
    db.commit()
    return ok(_issue_tokens(db, user))


@router.post("/login", dependencies=[Depends(rate_limit_auth)])
def login(body: Credentials, db: Session = Depends(get_db)) -> dict:
    username = body.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Username atau password salah.")
    return ok(_issue_tokens(db, user))


@router.post("/refresh", dependencies=[Depends(rate_limit_auth)])
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    record = db.get(RefreshToken, body.refreshToken)
    if not record or record.revoked or record.expires_at < time.time():
        raise ApiError(401, "INVALID_REFRESH_TOKEN", "Refresh token tidak valid atau kedaluwarsa.")
    return ok({"accessToken": create_access_token(record.user_id)})


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
    db.commit()
    return ok({"loggedOut": True})


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return ok({"user": user_to_dict(user)})
