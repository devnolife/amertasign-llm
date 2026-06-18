"""Endpoint training & evaluasi model (Fase 3)."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from app.ml.registry import reload_models
from app.ml.train import confusion, train_alphabet
from app.schemas.landmarks import Mode, Stage

router = APIRouter(tags=["train"])


class TrainRequest(BaseModel):
    mode: Mode
    stage: Stage = "abjad"
    augment_times: int = 2


@router.post("/train")
def train(req: TrainRequest) -> dict:
    result = train_alphabet(
        mode=req.mode, stage=req.stage, augment_times=req.augment_times
    )
    # Muat ulang cache agar /recognize langsung memakai model terbaru.
    reload_models()
    return asdict(result)


@router.get("/train/confusion")
def train_confusion(mode: Mode, stage: Stage = "abjad") -> dict:
    return confusion(mode=mode, stage=stage)
