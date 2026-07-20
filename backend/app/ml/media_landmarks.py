"""Ekstraksi landmark MediaPipe dari gambar/video yang diunggah mobile."""
from __future__ import annotations

from pathlib import Path

from app.config import PROJECT_ROOT

HAND_MODEL = (
    PROJECT_ROOT
    / "frontend"
    / "public"
    / "mediapipe"
    / "models"
    / "hand_landmarker.task"
)


def _imports():
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import (
            HandLandmarker,
            HandLandmarkerOptions,
            RunningMode,
        )
    except ImportError as exc:  # pragma: no cover - tergantung environment deploy
        raise RuntimeError(
            "MediaPipe/OpenCV belum terpasang pada backend."
        ) from exc
    return cv2, mp, BaseOptions, HandLandmarker, HandLandmarkerOptions, RunningMode


def _to_hands(result) -> list[dict]:
    hands: list[dict] = []
    landmarks_list = getattr(result, "hand_landmarks", None) or []
    handedness_list = getattr(result, "handedness", None) or []
    for index, hand_landmarks in enumerate(landmarks_list):
        handedness = "Right"
        score = 1.0
        if index < len(handedness_list) and handedness_list[index]:
            category = handedness_list[index][0]
            handedness = category.category_name or "Right"
            score = float(category.score or 1.0)
        hands.append(
            {
                "handedness": handedness,
                "score": score,
                "landmarks": [
                    {"x": float(lm.x), "y": float(lm.y), "z": float(lm.z)}
                    for lm in hand_landmarks
                ],
            }
        )
    return hands


def image_hands(path: Path, num_hands: int = 2) -> list[dict]:
    cv2, mp, BaseOptions, HandLandmarker, Options, RunningMode = _imports()
    if not HAND_MODEL.exists():
        raise RuntimeError(f"Model HandLandmarker tidak ditemukan: {HAND_MODEL}")
    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError("Gambar tidak dapat dibaca.")
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    options = Options(
        base_options=BaseOptions(model_asset_path=str(HAND_MODEL)),
        running_mode=RunningMode.IMAGE,
        num_hands=num_hands,
    )
    with HandLandmarker.create_from_options(options) as detector:
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    return _to_hands(result)


def video_hands(path: Path, num_hands: int = 2, stride: int = 2) -> list[list[dict]]:
    cv2, mp, BaseOptions, HandLandmarker, Options, RunningMode = _imports()
    if not HAND_MODEL.exists():
        raise RuntimeError(f"Model HandLandmarker tidak ditemukan: {HAND_MODEL}")
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Video tidak dapat dibaca.")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    options = Options(
        base_options=BaseOptions(model_asset_path=str(HAND_MODEL)),
        running_mode=RunningMode.VIDEO,
        num_hands=num_hands,
    )
    frames: list[list[dict]] = []
    detected: list[bool] = []
    frame_index = 0
    try:
        with HandLandmarker.create_from_options(options) as detector:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % stride == 0:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    timestamp_ms = int(frame_index * 1000.0 / fps)
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                        timestamp_ms,
                    )
                    hands = _to_hands(result)
                    frames.append(hands)
                    detected.append(bool(hands))
                frame_index += 1
    finally:
        capture.release()

    if not any(detected):
        return []
    first = detected.index(True)
    last = len(detected) - 1 - detected[::-1].index(True)
    return frames[first : last + 1]
