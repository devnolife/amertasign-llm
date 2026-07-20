"""Endpoint profil & preferensi user mobile."""
from __future__ import annotations

import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mobile.deps import ApiError, get_current_user, get_db, ok
from app.mobile.models import User
from app.mobile.security import hash_password, verify_password
from app.mobile.serializers import user_to_dict

router = APIRouter(prefix="/api/v1/users", tags=["mobile-users"])
USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,20}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    username: Optional[str] = Field(None, min_length=3, max_length=20)
    email: Optional[str] = Field(None, max_length=254)
    avatarUrl: Optional[str] = Field(None, max_length=512)
    preferredSignLanguage: Optional[Literal["bisindo", "sibi"]] = None


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


@router.patch("/me")
def update_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.name is not None:
        user.name = body.name.strip()
    if body.username is not None:
        username = body.username.strip().lower()
        if not USERNAME_RE.match(username):
            raise ApiError(400, "INVALID_USERNAME", "Format username tidak valid.")
        owner = db.scalar(select(User).where(User.username == username, User.id != user.id))
        if owner:
            raise ApiError(409, "USERNAME_TAKEN", "Username sudah dipakai.")
        user.username = username
    if body.email is not None:
        email = body.email.strip().lower()
        if email and not EMAIL_RE.match(email):
            raise ApiError(400, "INVALID_EMAIL", "Format email tidak valid.")
        owner = db.scalar(select(User).where(User.email == email, User.id != user.id)) if email else None
        if owner:
            raise ApiError(409, "EMAIL_TAKEN", "Email sudah dipakai.")
        user.email = email or None
    if body.avatarUrl is not None:
        user.avatar_url = body.avatarUrl
    if body.preferredSignLanguage is not None:
        user.preferred_sign_language = body.preferredSignLanguage
    db.add(user)
    db.commit()
    return ok({"user": user_to_dict(user)})


@router.patch("/me/password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not user.password_hash:
        raise ApiError(400, "NO_PASSWORD", "Akun Google belum memiliki password lokal.")
    if not verify_password(body.currentPassword, user.password_hash):
        raise ApiError(401, "INVALID_PASSWORD", "Password saat ini salah.")
    if len(body.newPassword) < 6:
        raise ApiError(400, "INVALID_PASSWORD", "Password baru minimal 6 karakter.")
    user.password_hash = hash_password(body.newPassword)
    db.add(user)
    db.commit()
    return ok({"changed": True})
