"""Endpoint auth mobile: register, login, refresh, logout, me."""
from __future__ import annotations

import re
import time
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
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
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["mobile-auth"])

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,20}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Credentials(BaseModel):
    username: str
    password: str
    email: str | None = None


class RefreshRequest(BaseModel):
    refreshToken: str


class ForgotPasswordRequest(BaseModel):
    username: str
    email: str
    newPassword: str


class GoogleTokenRequest(BaseModel):
    idToken: str


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
    email = body.email.strip().lower() if body.email else None
    if email and not EMAIL_RE.match(email):
        raise ApiError(400, "INVALID_EMAIL", "Format email tidak valid.")
    exists = db.scalar(select(User).where(User.username == username))
    if exists:
        raise ApiError(409, "USERNAME_TAKEN", "Username sudah dipakai.")
    if email and db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "EMAIL_TAKEN", "Email sudah dipakai.")

    user = User(
        username=username,
        email=email,
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


@router.post("/forgot-password", dependencies=[Depends(rate_limit_auth)])
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    username = body.username.strip().lower()
    email = body.email.strip().lower()
    if len(body.newPassword) < 6:
        raise ApiError(400, "INVALID_PASSWORD", "Password baru minimal 6 karakter.")
    user = db.scalar(
        select(User).where(User.username == username, User.email == email)
    )
    if not user:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Username dan email tidak cocok.")
    user.password_hash = hash_password(body.newPassword)
    db.add(user)
    db.commit()
    return ok({"changed": True})


def _google_client_ids() -> list[str]:
    return [item.strip() for item in settings.google_client_ids.split(",") if item.strip()]


def _verify_google_token(id_token: str) -> dict:
    client_ids = _google_client_ids()
    if not client_ids:
        raise ApiError(503, "GOOGLE_NOT_CONFIGURED", "Login Google belum dikonfigurasi di server.")
    try:
        response = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=15.0,
        )
        response.raise_for_status()
        profile = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApiError(401, "INVALID_GOOGLE_TOKEN", "Token Google tidak valid.") from exc
    if profile.get("aud") not in client_ids or profile.get("email_verified") not in (True, "true"):
        raise ApiError(401, "INVALID_GOOGLE_TOKEN", "Token Google tidak ditujukan untuk aplikasi ini.")
    return profile


def _unique_google_username(db: Session, email: str) -> str:
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@", 1)[0].lower())[:16]
    base = base if len(base) >= 3 else f"user{base}"
    candidate = base
    suffix = 1
    while db.scalar(select(User.id).where(User.username == candidate)):
        candidate = f"{base[:16]}{suffix}"[:20]
        suffix += 1
    return candidate


def _login_google_profile(profile: dict, db: Session) -> dict:
    google_id = str(profile.get("sub", ""))
    email = str(profile.get("email", "")).strip().lower()
    if not google_id or not email:
        raise ApiError(401, "INVALID_GOOGLE_TOKEN", "Profil Google tidak lengkap.")
    user = db.scalar(select(User).where(User.google_id == google_id))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            username=_unique_google_username(db, email),
            email=email,
            google_id=google_id,
            password_hash="",
            name=str(profile.get("name") or email.split("@", 1)[0])[:64],
            avatar_url=profile.get("picture"),
        )
    else:
        user.google_id = google_id
        user.email = email
        if profile.get("picture") and not user.avatar_url:
            user.avatar_url = str(profile["picture"])
    db.add(user)
    db.commit()
    return _issue_tokens(db, user)


@router.post("/google", dependencies=[Depends(rate_limit_auth)])
def google_token_login(body: GoogleTokenRequest, db: Session = Depends(get_db)) -> dict:
    return ok(_login_google_profile(_verify_google_token(body.idToken), db))


def _valid_return_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"amertasign", "exp", "exps"}


@router.get("/google/start")
def google_start(request: Request, returnUrl: str = Query()) -> RedirectResponse:
    client_ids = _google_client_ids()
    if not client_ids or not settings.google_client_secret:
        raise ApiError(503, "GOOGLE_NOT_CONFIGURED", "Login Google belum dikonfigurasi di server.")
    if not _valid_return_url(returnUrl):
        raise ApiError(400, "INVALID_RETURN_URL", "URL kembali aplikasi tidak valid.")
    now = int(time.time())
    state = jwt.encode(
        {"type": "google-oauth", "returnUrl": returnUrl, "iat": now, "exp": now + 600},
        settings.jwt_secret,
        algorithm="HS256",
    )
    public_base = settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    redirect_uri = f"{public_base}/api/v1/auth/google/callback"
    query = urlencode(
        {
            "client_id": client_ids[0],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


@router.get("/google/callback")
def google_callback(
    request: Request,
    state: str,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "google-oauth":
            raise jwt.InvalidTokenError()
        return_url = str(payload["returnUrl"])
    except (jwt.PyJWTError, KeyError):
        raise ApiError(400, "INVALID_OAUTH_STATE", "Sesi login Google tidak valid.")
    if not _valid_return_url(return_url):
        raise ApiError(400, "INVALID_RETURN_URL", "URL kembali aplikasi tidak valid.")
    if error or not code:
        separator = "&" if "?" in return_url else "?"
        return RedirectResponse(f"{return_url}{separator}{urlencode({'error': error or 'CANCELLED'})}")

    public_base = settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    redirect_uri = f"{public_base}/api/v1/auth/google/callback"
    try:
        token_response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": _google_client_ids()[0],
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15.0,
        )
        token_response.raise_for_status()
        profile = _verify_google_token(token_response.json()["id_token"])
        tokens = _login_google_profile(profile, db)
        params = urlencode(
            {"accessToken": tokens["accessToken"], "refreshToken": tokens["refreshToken"]}
        )
    except (httpx.HTTPError, KeyError, ApiError):
        params = urlencode({"error": "GOOGLE_LOGIN_FAILED", "message": "Verifikasi Google gagal."})
    separator = "&" if "?" in return_url else "?"
    return RedirectResponse(f"{return_url}{separator}{params}")
