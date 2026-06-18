"""Penyimpanan & manajemen dataset sampel landmark berlabel.

Setiap sampel disimpan sebagai baris pada manifest JSONL per (mode, stage) plus
array fitur landmark pada file NPZ append-friendly. Untuk kesederhanaan & ketahanan,
fitur disimpan sebagai file .npy individual di bawah data/recordings/<mode>/<stage>/<label>/
dan diindeks oleh manifest.

Struktur:
    data/recordings/
      manifest.jsonl                 # 1 baris per sampel (lihat SampleRecord)
      SIBI/abjad/A/<uuid>.npy         # array (T, F) atau (F,) untuk statis
      BISINDO/kata/makan/<uuid>.npy
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from app.config import settings

RECORDINGS_DIR = settings.data_dir / "recordings"
MANIFEST_PATH = RECORDINGS_DIR / "manifest.jsonl"

_write_lock = threading.Lock()


@dataclass
class SampleRecord:
    id: str
    mode: str
    stage: str
    label: str
    path: str  # relatif terhadap RECORDINGS_DIR
    num_frames: int  # 1 untuk gestur statis (abjad)
    feature_dim: int
    max_hands: int
    created_at: float


def _ensure_dirs() -> None:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def _sample_dir(mode: str, stage: str, label: str) -> Path:
    # Label disanitasi agar aman jadi nama folder.
    safe_label = "".join(c for c in label if c.isalnum() or c in ("-", "_")) or "_"
    return RECORDINGS_DIR / mode / stage / safe_label


def save_sample(
    mode: str,
    stage: str,
    label: str,
    features: np.ndarray,
    max_hands: int,
    created_at: float,
) -> SampleRecord:
    """Simpan satu sampel fitur (statis (F,) atau urutan (T,F)) + catat di manifest."""
    _ensure_dirs()
    features = np.asarray(features, dtype=np.float32)
    num_frames = 1 if features.ndim == 1 else features.shape[0]
    feature_dim = features.shape[-1]

    sample_id = uuid.uuid4().hex
    target_dir = _sample_dir(mode, stage, label)
    target_dir.mkdir(parents=True, exist_ok=True)
    npy_path = target_dir / f"{sample_id}.npy"
    np.save(npy_path, features)

    record = SampleRecord(
        id=sample_id,
        mode=mode,
        stage=stage,
        label=label,
        path=str(npy_path.relative_to(RECORDINGS_DIR)),
        num_frames=num_frames,
        feature_dim=int(feature_dim),
        max_hands=int(max_hands),
        created_at=created_at,
    )

    with _write_lock:
        with MANIFEST_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    return record


def iter_records() -> Iterator[SampleRecord]:
    if not MANIFEST_PATH.exists():
        return
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield SampleRecord(**json.loads(line))


def load_features(record: SampleRecord) -> np.ndarray:
    return np.load(RECORDINGS_DIR / record.path)


def dataset_stats(mode: Optional[str] = None, stage: Optional[str] = None) -> dict:
    """Ringkasan jumlah sampel per (mode, stage, label)."""
    counts: dict[str, dict[str, dict[str, int]]] = {}
    total = 0
    for rec in iter_records():
        if mode and rec.mode != mode:
            continue
        if stage and rec.stage != stage:
            continue
        counts.setdefault(rec.mode, {}).setdefault(rec.stage, {})
        counts[rec.mode][rec.stage][rec.label] = (
            counts[rec.mode][rec.stage].get(rec.label, 0) + 1
        )
        total += 1
    return {"total": total, "counts": counts}
