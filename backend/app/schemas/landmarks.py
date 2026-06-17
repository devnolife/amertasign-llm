"""Skema data landmark tangan & hasil pengenalan.

Kontrak bersama antara frontend (MediaPipe HandLandmarker) dan backend.
MediaPipe mengembalikan 21 titik per tangan (x, y dinormalisasi 0..1, z relatif).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Mode = Literal["BISINDO", "SIBI"]
Stage = Literal["abjad", "kata", "kalimat"]
Handedness = Literal["Left", "Right"]

NUM_HAND_LANDMARKS = 21  # standar MediaPipe Hands


class Landmark(BaseModel):
    x: float
    y: float
    z: float = 0.0


class HandLandmarks(BaseModel):
    """Landmark satu tangan beserta handedness-nya."""

    handedness: Handedness
    score: float = 1.0
    landmarks: list[Landmark] = Field(..., min_length=NUM_HAND_LANDMARKS, max_length=NUM_HAND_LANDMARKS)


class FramePayload(BaseModel):
    """Satu frame: kumpulan tangan yang terdeteksi (0..2)."""

    mode: Mode
    stage: Stage
    hands: list[HandLandmarks] = Field(default_factory=list)
    timestamp: Optional[float] = None


class SequencePayload(BaseModel):
    """Urutan frame untuk gestur dinamis (kata / kalimat)."""

    mode: Mode
    stage: Stage
    frames: list[list[HandLandmarks]] = Field(default_factory=list)


class Candidate(BaseModel):
    label: str
    confidence: float


class RecognitionResult(BaseModel):
    """Hasil pengenalan yang dikirim balik ke frontend."""

    text: str
    confidence: float
    candidates: list[Candidate] = Field(default_factory=list)
    mode: Mode
    stage: Stage
    model_loaded: bool = False
    note: Optional[str] = None
