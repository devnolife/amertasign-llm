"""Endpoint penyusunan kalimat dari gloss (Fase 5)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.llm.compose import compose_sentence
from app.schemas.landmarks import Mode

router = APIRouter(tags=["compose"])


class ComposeRequest(BaseModel):
    mode: Mode
    gloss: list[str] = Field(default_factory=list)


class ComposeResponse(BaseModel):
    sentence: str
    provider: str
    gloss: list[str]
    note: str | None = None


@router.post("/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest) -> ComposeResponse:
    result = compose_sentence(req.gloss, req.mode)
    return ComposeResponse(**result)
