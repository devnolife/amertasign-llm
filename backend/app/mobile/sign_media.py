"""Sinkronisasi file media BISINDO ke tabel kamus mobile."""
from __future__ import annotations

import unicodedata
from pathlib import Path

from app.config import settings
from app.mobile.db import SessionLocal
from app.mobile.models import DictionaryEntry


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "-".join(normalized.lower().strip().split())


def _display_word(stem: str, category: str) -> str:
    value = stem.replace("-", " ")
    if category == "alfabet":
        return value.upper()
    if category == "angka":
        return value
    return value.title()


def sync_sign_media_dictionary() -> int:
    """Upsert media pada data/public/sign_media; aman dipanggil tiap startup."""
    root = settings.data_dir / "public" / "sign_media" / "bisindo"
    if not root.is_dir():
        return 0
    categories = {
        "alfabet": "alfabet",
        "angka": "angka",
        "kata": "kata_umum",
    }
    changed = 0
    with SessionLocal() as db:
        for folder_name, category in categories.items():
            folder = root / folder_name
            if not folder.is_dir():
                continue
            stems = {path.stem for path in folder.iterdir() if path.is_file()}
            for stem in sorted(stems):
                image = folder / f"{stem}.jpg"
                video = folder / f"{stem}.mp4"
                if not image.exists() and not video.exists():
                    continue
                word = _display_word(stem, category)
                entry_id = f"media-bi-{category[:4]}-{slugify(word)}"[:32]
                entry = db.get(DictionaryEntry, entry_id)
                if entry is None:
                    entry = DictionaryEntry(id=entry_id)
                entry.word = word
                entry.category = category
                entry.type = "bisindo"
                entry.description = (
                    f"Peragaan bentuk tangan BISINDO untuk huruf {word}."
                    if category == "alfabet"
                    else f"Peragaan gerakan BISINDO untuk {word}."
                )
                base = f"/api/v1/media/bisindo/{folder_name}/{stem}"
                entry.image_url = f"{base}.jpg" if image.exists() else ""
                entry.video_url = f"{base}.mp4" if video.exists() else ""
                db.add(entry)
                changed += 1
        db.commit()
    return changed
