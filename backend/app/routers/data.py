"""Endpoint pengumpulan data berlabel untuk training.

- POST /collect      : simpan satu sampel (frame statis ATAU urutan frame).
- GET  /datasets     : statistik sampel terkumpul.
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ml.dataset import dataset_stats, save_sample
from app.ml.normalize import (
    frame_to_features,
    max_hands_for_mode,
    sequence_to_features,
)
from app.schemas.landmarks import HandLandmarks, Mode, Stage

router = APIRouter(tags=["data"])


class CollectRequest(BaseModel):
    mode: Mode
    stage: Stage
    label: str = Field(..., min_length=1, max_length=64)
    # Gestur statis (abjad): isi `hands`. Gestur dinamis (kata/kalimat): isi `frames`.
    hands: Optional[list[HandLandmarks]] = None
    frames: Optional[list[list[HandLandmarks]]] = None


class CollectResponse(BaseModel):
    id: str
    label: str
    num_frames: int
    feature_dim: int
    total_for_label: int


@router.post("/collect", response_model=CollectResponse)
def collect(req: CollectRequest) -> CollectResponse:
    max_hands = max_hands_for_mode(req.mode)

    if req.frames is not None and len(req.frames) > 0:
        features = sequence_to_features(req.frames, max_hands=max_hands)
        if features.shape[0] == 0:
            raise HTTPException(status_code=400, detail="Urutan frame kosong.")
    elif req.hands is not None and len(req.hands) > 0:
        features = frame_to_features(req.hands, max_hands=max_hands)
    else:
        raise HTTPException(
            status_code=400,
            detail="Sertakan `hands` (statis) atau `frames` (urutan) yang berisi tangan.",
        )

    record = save_sample(
        mode=req.mode,
        stage=req.stage,
        label=req.label,
        features=features,
        max_hands=max_hands,
        created_at=time.time(),
    )

    stats = dataset_stats(mode=req.mode, stage=req.stage)
    total_for_label = (
        stats["counts"].get(req.mode, {}).get(req.stage, {}).get(req.label, 0)
    )

    return CollectResponse(
        id=record.id,
        label=record.label,
        num_frames=record.num_frames,
        feature_dim=record.feature_dim,
        total_for_label=total_for_label,
    )


@router.get("/datasets")
def datasets(mode: Optional[Mode] = None, stage: Optional[Stage] = None) -> dict:
    return dataset_stats(mode=mode, stage=stage)
