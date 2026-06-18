"""Registry & predictor model pengenalan.

Memuat model per kombinasi (mode, stage) dari MODELS_DIR bila tersedia.
Konvensi nama file: "{mode}_{stage}.joblib" (mis. SIBI_abjad.joblib).

Bundle model (disimpan via joblib) berupa dict:
    {
        "clf": estimator sklearn (punya predict_proba),
        "labels": list[str],
        "max_hands": int,
        "mode": str,
        "stage": str,
    }

Selama belum ada model terlatih (Fase 0/1), predictor mengembalikan stub
(model_loaded=False) sehingga pipeline end-to-end tetap dapat diuji.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import joblib
import numpy as np

from app.config import settings
from app.ml.normalize import (
    frame_to_features,
    max_hands_for_mode,
    sequence_feature_vector,
)
from app.schemas.landmarks import (
    Candidate,
    FramePayload,
    RecognitionResult,
    SequencePayload,
)

_lock = threading.Lock()
_cache: dict[str, Optional[dict]] = {}


def _model_path(mode: str, stage: str) -> Path:
    return settings.models_dir / f"{mode}_{stage}.joblib"


def _load_bundle(mode: str, stage: str) -> Optional[dict]:
    key = f"{mode}_{stage}"
    if key in _cache:
        return _cache[key]
    with _lock:
        if key in _cache:
            return _cache[key]
        path = _model_path(mode, stage)
        bundle = joblib.load(path) if path.exists() else None
        _cache[key] = bundle
        return bundle


def reload_models() -> None:
    """Kosongkan cache agar model terbaru dimuat ulang (dipakai setelah training)."""
    with _lock:
        _cache.clear()


def predict_frame(payload: FramePayload, top_k: int = 3) -> RecognitionResult:
    """Prediksi label dari satu frame (gestur statis, mis. abjad)."""
    bundle = _load_bundle(payload.mode, payload.stage)

    if bundle is None:
        return RecognitionResult(
            text="",
            confidence=0.0,
            mode=payload.mode,
            stage=payload.stage,
            model_loaded=False,
            note="Model belum dilatih untuk kombinasi ini. Kumpulkan data & latih (Fase 2-3).",
        )

    if not payload.hands:
        return RecognitionResult(
            text="",
            confidence=0.0,
            mode=payload.mode,
            stage=payload.stage,
            model_loaded=True,
            note="Tidak ada tangan terdeteksi.",
        )

    max_hands = bundle.get("max_hands", max_hands_for_mode(payload.mode))
    features = frame_to_features(payload.hands, max_hands=max_hands).reshape(1, -1)
    return _predict_with_bundle(
        bundle, features, payload.mode, payload.stage, top_k
    )


def _predict_with_bundle(
    bundle: dict,
    features: np.ndarray,
    mode: str,
    stage: str,
    top_k: int,
) -> RecognitionResult:
    clf = bundle["clf"]
    labels = bundle["labels"]
    proba = clf.predict_proba(features)[0]
    order = np.argsort(proba)[::-1][:top_k]
    candidates = [Candidate(label=labels[i], confidence=float(proba[i])) for i in order]

    best = candidates[0]
    text = best.label if best.confidence >= settings.min_confidence else ""
    return RecognitionResult(
        text=text,
        confidence=best.confidence,
        candidates=candidates,
        mode=mode,
        stage=stage,
        model_loaded=True,
    )


def predict_sequence(payload: SequencePayload, top_k: int = 3) -> RecognitionResult:
    """Prediksi label dari urutan frame (gestur dinamis, mis. kata)."""
    bundle = _load_bundle(payload.mode, payload.stage)

    if bundle is None:
        return RecognitionResult(
            text="",
            confidence=0.0,
            mode=payload.mode,
            stage=payload.stage,
            model_loaded=False,
            note="Model kata belum dilatih. Kumpulkan urutan & latih (Fase 4).",
        )

    if not payload.frames:
        return RecognitionResult(
            text="",
            confidence=0.0,
            mode=payload.mode,
            stage=payload.stage,
            model_loaded=True,
            note="Urutan kosong.",
        )

    max_hands = bundle.get("max_hands", max_hands_for_mode(payload.mode))
    seq_len = bundle.get("seq_len", 16)
    features = sequence_feature_vector(
        payload.frames, max_hands=max_hands, seq_len=seq_len
    ).reshape(1, -1)
    return _predict_with_bundle(
        bundle, features, payload.mode, payload.stage, top_k
    )
