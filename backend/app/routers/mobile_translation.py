"""Endpoint terjemahan mobile: teks → media isyarat BISINDO."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mobile.deps import ApiError, get_db, ok
from app.mobile.models import DictionaryEntry
from app.ml.media_landmarks import image_hands, video_hands
from app.ml.registry import predict_frame, predict_sequence
from app.schemas.landmarks import FramePayload, SequencePayload

router = APIRouter(prefix="/api/v1/translate", tags=["mobile-translation"])

_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÿ]+(?:[-'][0-9A-Za-zÀ-ÿ]+)?", re.UNICODE)


class TextToSignRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    signLanguageType: Literal["bisindo"] = "bisindo"


UploadedMedia = Annotated[UploadFile, File(description="Gambar atau video isyarat")]
RecognitionStage = Annotated[Literal["abjad", "kata"], Form()]


def _absolute_url(request: Request, value: str) -> str:
    if not value or value.startswith(("http://", "https://")):
        return value
    return f"{str(request.base_url).rstrip('/')}/{value.lstrip('/')}"


def _unit(request: Request, entry: DictionaryEntry, token: str, match_type: str) -> dict:
    video_url = _absolute_url(request, entry.video_url)
    image_url = _absolute_url(request, entry.image_url)
    return {
        "token": token,
        "word": entry.word,
        "category": entry.category,
        "description": entry.description,
        "videoUrl": video_url,
        "imageUrl": image_url,
        "mediaUrl": video_url or image_url,
        "mediaType": "video" if video_url else "image",
        "matchType": match_type,
    }


@router.post("/text-to-sign")
def text_to_sign(
    body: TextToSignRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Petakan teks ke media kamus; kata tak dikenal dieja per huruf."""
    clean_text = " ".join(body.text.strip().split())
    if not clean_text:
        raise ApiError(400, "EMPTY_TEXT", "Teks tidak boleh kosong.")

    entries = db.scalars(
        select(DictionaryEntry).where(DictionaryEntry.type == body.signLanguageType)
    ).all()
    if not entries:
        raise ApiError(
            503,
            "DICTIONARY_EMPTY",
            "Kamus media isyarat belum tersedia. Jalankan build_sign_media.py.",
        )

    by_word = {entry.word.casefold(): entry for entry in entries}
    by_letter = {
        entry.word.casefold(): entry
        for entry in entries
        if entry.category == "alfabet" and len(entry.word) == 1
    }

    # Utamakan kecocokan seluruh frasa/kata.
    exact = by_word.get(clean_text.casefold())
    if exact:
        units = [_unit(request, exact, clean_text, "exact")]
        unmatched: list[str] = []
    else:
        units = []
        unmatched = []
        for token in _TOKEN_RE.findall(clean_text):
            entry = by_word.get(token.casefold())
            if entry:
                units.append(_unit(request, entry, token, "exact"))
                continue

            # Fallback finger-spelling untuk kata yang belum ada di kamus.
            spelled = False
            for character in token:
                letter = by_letter.get(character.casefold())
                if letter:
                    units.append(_unit(request, letter, character.upper(), "spelling"))
                    spelled = True
                elif character.isalnum():
                    unmatched.append(character)
            if not spelled:
                unmatched.append(token)

    if not units:
        raise ApiError(
            404,
            "SIGN_NOT_FOUND",
            "Belum ada media isyarat atau alfabet yang cocok untuk teks tersebut.",
        )

    return ok(
        {
            "text": clean_text,
            "signLanguageType": body.signLanguageType,
            "units": units,
            "unmatched": list(dict.fromkeys(unmatched)),
        }
    )


@router.post("/sign-to-text")
def sign_to_text(file: UploadedMedia, stage: RecognitionStage = "abjad") -> dict:
    """Kenali isyarat dari foto (abjad) atau video (kata) yang diunggah."""
    suffix = Path(file.filename or "upload").suffix.lower()
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    allowed = image_extensions | video_extensions
    if suffix not in allowed:
        raise ApiError(415, "UNSUPPORTED_MEDIA", "Gunakan gambar JPG/PNG atau video MP4/MOV.")
    if stage == "abjad" and suffix not in image_extensions:
        raise ApiError(400, "STAGE_MEDIA_MISMATCH", "Mode abjad membutuhkan gambar.")
    if stage == "kata" and suffix not in video_extensions:
        raise ApiError(400, "STAGE_MEDIA_MISMATCH", "Mode kata membutuhkan video.")

    max_bytes = 30 * 1024 * 1024
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
            temp_path = Path(temp.name)
            total = 0
            while chunk := file.file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ApiError(413, "MEDIA_TOO_LARGE", "Ukuran media maksimal 30 MB.")
                temp.write(chunk)

        if stage == "abjad":
            hands = image_hands(temp_path)
            result = predict_frame(
                FramePayload(mode="BISINDO", stage="abjad", hands=hands)
            )
        else:
            frames = video_hands(temp_path)
            result = predict_sequence(
                SequencePayload(mode="BISINDO", stage="kata", frames=frames)
            )
        return ok(result.model_dump())
    except ApiError:
        raise
    except ValueError as exc:
        raise ApiError(400, "INVALID_MEDIA", str(exc)) from exc
    except RuntimeError as exc:
        raise ApiError(503, "RECOGNITION_UNAVAILABLE", str(exc)) from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
