"""Endpoint pengenalan isyarat: HTTP (single frame) + WebSocket (streaming).

Pada Fase 1 model belum ada -> registry mengembalikan stub (model_loaded=False),
namun jalur data webcam -> landmark -> backend -> hasil sudah berfungsi penuh.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.ml.registry import predict_frame
from app.schemas.landmarks import FramePayload, RecognitionResult

router = APIRouter(tags=["recognize"])


@router.post("/recognize", response_model=RecognitionResult)
def recognize(payload: FramePayload) -> RecognitionResult:
    """Kenali satu frame landmark (gestur statis)."""
    return predict_frame(payload)


@router.websocket("/ws/recognize")
async def ws_recognize(websocket: WebSocket) -> None:
    """Streaming pengenalan: client mengirim FramePayload (JSON) tiap frame,
    server membalas RecognitionResult (JSON)."""
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_json()
            try:
                payload = FramePayload.model_validate(raw)
            except ValidationError as exc:
                await websocket.send_json({"error": "invalid_payload", "detail": exc.errors()})
                continue
            result = predict_frame(payload)
            await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        return
