"""Serializer objek DB -> dict JSON (camelCase) sesuai kontrak mobile."""
from __future__ import annotations

from datetime import datetime, timezone

from app.mobile.models import DictionaryEntry, TranslationHistory, User


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "preferredSignLanguage": user.preferred_sign_language,
        "streak": user.streak,
        "avatarUrl": user.avatar_url,
    }


def history_to_dict(item: TranslationHistory) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "text": item.text,
        "signLanguageType": item.sign_language_type,
        "createdAt": iso(item.created_at),
    }


def entry_to_dict(entry: DictionaryEntry) -> dict:
    return {
        "id": entry.id,
        "word": entry.word,
        "category": entry.category,
        "type": entry.type,
        "description": entry.description,
        "imageUrl": entry.image_url,
        "videoUrl": entry.video_url,
    }
