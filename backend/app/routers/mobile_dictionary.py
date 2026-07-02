"""Endpoint kamus isyarat & favorit."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.mobile.deps import ApiError, get_current_user, get_db, ok
from app.mobile.models import DictionaryEntry, Favorite, User
from app.mobile.serializers import entry_to_dict

router = APIRouter(prefix="/api/v1", tags=["mobile-dictionary"])

SignLanguage = Literal["bisindo", "sibi"]
Category = Literal["alfabet", "angka", "kata_umum", "frasa"]


@router.get("/dictionary")
def list_dictionary(
    type: Optional[SignLanguage] = None,
    category: Optional[Category] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(DictionaryEntry).order_by(DictionaryEntry.word.asc(), DictionaryEntry.id.asc())
    if type:
        stmt = stmt.where(DictionaryEntry.type == type)
    if category:
        stmt = stmt.where(DictionaryEntry.category == category)
    if search:
        stmt = stmt.where(DictionaryEntry.word.ilike(f"%{search.strip()}%"))
    if cursor:
        anchor = db.get(DictionaryEntry, cursor)
        if anchor:
            stmt = stmt.where(
                (DictionaryEntry.word > anchor.word)
                | ((DictionaryEntry.word == anchor.word) & (DictionaryEntry.id > anchor.id))
            )
    rows = db.scalars(stmt.limit(limit + 1)).all()
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return ok({
        "items": [entry_to_dict(r) for r in rows[:limit]],
        "nextCursor": next_cursor,
    })


@router.get("/dictionary/daily")
def daily_word(db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.count()).select_from(DictionaryEntry)) or 0
    if total == 0:
        raise ApiError(404, "NO_ENTRIES", "Kamus masih kosong.")
    offset = date.today().toordinal() % total
    entry = db.scalars(
        select(DictionaryEntry).order_by(DictionaryEntry.id.asc()).offset(offset).limit(1)
    ).first()
    return ok({"entry": entry_to_dict(entry)})


@router.get("/dictionary/{entry_id}")
def dictionary_detail(entry_id: str, db: Session = Depends(get_db)) -> dict:
    entry = db.get(DictionaryEntry, entry_id)
    if not entry:
        raise ApiError(404, "NOT_FOUND", "Entri kamus tidak ditemukan.")
    related = db.scalars(
        select(DictionaryEntry)
        .where(
            DictionaryEntry.type == entry.type,
            DictionaryEntry.category == entry.category,
            DictionaryEntry.id != entry.id,
        )
        .order_by(DictionaryEntry.word.asc())
        .limit(6)
    ).all()
    return ok({
        "entry": entry_to_dict(entry),
        "related": [entry_to_dict(r) for r in related],
    })


@router.get("/favorites")
def list_favorites(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    ids = db.scalars(select(Favorite.entry_id).where(Favorite.user_id == user.id)).all()
    return ok({"ids": list(ids)})


@router.put("/favorites/{entry_id}")
def add_favorite(
    entry_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(DictionaryEntry, entry_id):
        raise ApiError(404, "NOT_FOUND", "Entri kamus tidak ditemukan.")
    if not db.get(Favorite, (user.id, entry_id)):
        db.add(Favorite(user_id=user.id, entry_id=entry_id))
        db.commit()
    return ok({"favorited": True})


@router.delete("/favorites/{entry_id}")
def remove_favorite(
    entry_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.execute(
        delete(Favorite).where(Favorite.user_id == user.id, Favorite.entry_id == entry_id)
    )
    db.commit()
    return ok({"favorited": False})
