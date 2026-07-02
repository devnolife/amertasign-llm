"""Endpoint riwayat terjemahan (wajib auth)."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.mobile.deps import ApiError, get_current_user, get_db, ok
from app.mobile.models import TranslationHistory, User
from app.mobile.serializers import history_to_dict

router = APIRouter(prefix="/api/v1/history", tags=["mobile-history"])

Kind = Literal["isyarat-ke-teks", "teks-ke-isyarat"]
SignLanguage = Literal["bisindo", "sibi"]


class CreateHistoryRequest(BaseModel):
    kind: Kind
    text: str = Field(..., min_length=1, max_length=2000)
    signLanguageType: SignLanguage


@router.get("")
def list_history(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    kind: Optional[Kind] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(TranslationHistory)
        .where(TranslationHistory.user_id == user.id)
        .order_by(TranslationHistory.created_at.desc(), TranslationHistory.id.desc())
    )
    if kind:
        stmt = stmt.where(TranslationHistory.kind == kind)
    if cursor:
        anchor = db.get(TranslationHistory, cursor)
        if anchor and anchor.user_id == user.id:
            stmt = stmt.where(TranslationHistory.created_at < anchor.created_at)
    rows = db.scalars(stmt.limit(limit + 1)).all()
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return ok({
        "items": [history_to_dict(r) for r in rows[:limit]],
        "nextCursor": next_cursor,
    })


@router.post("")
def create_history(
    body: CreateHistoryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = TranslationHistory(
        user_id=user.id,
        kind=body.kind,
        text=body.text,
        sign_language_type=body.signLanguageType,
    )
    db.add(item)
    db.commit()
    return ok({"item": history_to_dict(item)})


@router.delete("/{item_id}")
def delete_history_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(TranslationHistory, item_id)
    if not item or item.user_id != user.id:
        raise ApiError(404, "NOT_FOUND", "Riwayat tidak ditemukan.")
    db.delete(item)
    db.commit()
    return ok({"deleted": True})


@router.delete("")
def clear_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.execute(delete(TranslationHistory).where(TranslationHistory.user_id == user.id))
    db.commit()
    return ok({"deleted": True})
