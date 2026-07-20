#!/usr/bin/env python3
"""Ingest dataset urutan frame (gambar hasil ekstraksi video) menjadi sampel landmark.

Mengubah folder frame berlabel (frame_00000.jpg, frame_00001.jpg, ...) menjadi
sampel urutan (T, F) yang kompatibel dengan penyimpanan dataset backend
(data/recordings + manifest.jsonl), sehingga bisa dilatih oleh
`scripts/train.py --stage kata`.

Struktur input yang didukung (label = nama subfolder):
    <input_dir>/
      Belajar/  frame_00000.jpg frame_00001.jpg ...   # satu rekaman per label
      Dimana/   ...

    atau beberapa rekaman per label (tiap subfolder = satu rekaman):
    <input_dir>/
      Belajar/
        rekaman1/ frame_00000.jpg ...
        rekaman2/ frame_00000.jpg ...

Karena satu folder frame = satu rekaman, opsi --window bisa dipakai untuk
memecah urutan panjang menjadi beberapa sampel (jendela geser tumpang-tindih)
agar data latih lebih banyak.

Butuh `mediapipe` & `opencv-python` (scripts/requirements-ingest.txt) dan model
`hand_landmarker.task` (di-setup oleh scripts/fetch-assets.sh).

Penggunaan:
    python scripts/ingest_frames.py --input-dir "data/Kata 1" \
        --mode SIBI --stage kata --window 24 --window-stride 8
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Pastikan paket `app` (di backend/) dapat diimpor.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402

from app.ml.dataset import save_sample  # noqa: E402
from app.ml.normalize import frame_to_features, max_hands_for_mode  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_MODEL = ROOT / "frontend" / "public" / "mediapipe" / "models" / "hand_landmarker.task"


def _load_detector(model_path: Path, num_hands: int):
    try:
        import cv2  # noqa: F401
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import (
            HandLandmarker,
            HandLandmarkerOptions,
            RunningMode,
        )
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Butuh mediapipe & opencv-python. Install: "
            "pip install -r scripts/requirements-ingest.txt"
        ) from exc

    if not model_path.exists():
        raise SystemExit(
            f"Model tidak ditemukan: {model_path}\n"
            "Jalankan scripts/fetch-assets.sh atau berikan --model."
        )

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=RunningMode.VIDEO,
        num_hands=num_hands,
    )
    return HandLandmarker.create_from_options(options)


def _to_hands(result) -> list[dict]:
    """Konversi HandLandmarkerResult (Tasks API) -> skema HandLandmarks (dict)."""
    hands: list[dict] = []
    landmarks_list = getattr(result, "hand_landmarks", None) or []
    handedness_list = getattr(result, "handedness", None) or []
    for i, hand_landmarks in enumerate(landmarks_list):
        label = "Right"
        if i < len(handedness_list) and handedness_list[i]:
            label = handedness_list[i][0].category_name or "Right"
        hands.append(
            {
                "handedness": label,
                "score": 1.0,
                "landmarks": [
                    {"x": lm.x, "y": lm.y, "z": getattr(lm, "z", 0.0)}
                    for lm in hand_landmarks
                ],
            }
        )
    return hands


def _frames_to_sequence(
    frame_paths: list[Path], model_path: Path, max_hands: int, fps: float
) -> np.ndarray | None:
    """Ekstrak urutan fitur (T, F) dari daftar frame terurut; None bila tanpa tangan."""
    import cv2
    import mediapipe as mp

    # Detector VIDEO mode butuh timestamp monoton -> satu detector per rekaman.
    detector = _load_detector(model_path, num_hands=max(2, max_hands))
    try:
        feats: list[np.ndarray] = []
        has_hand: list[bool] = []
        for idx, path in enumerate(frame_paths):
            frame = cv2.imread(str(path))
            if frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(idx * 1000.0 / fps)
            result = detector.detect_for_video(mp_image, ts_ms)
            hands = _to_hands(result)
            feats.append(frame_to_features(hands, max_hands=max_hands))
            has_hand.append(bool(hands))
    finally:
        detector.close()

    if not any(has_hand):
        return None
    # Pangkas frame kosong di awal/akhir (sebelum/ sesudah gestur).
    first = has_hand.index(True)
    last = len(has_hand) - 1 - has_hand[::-1].index(True)
    seq = np.stack(feats[first : last + 1]).astype(np.float32)
    return seq if seq.shape[0] >= 2 else None


def _split_windows(seq: np.ndarray, window: int, stride: int) -> list[np.ndarray]:
    """Pecah urutan menjadi jendela geser; urutan pendek dikembalikan utuh."""
    if window <= 0 or seq.shape[0] <= window:
        return [seq]
    out = [seq[start : start + window] for start in range(0, seq.shape[0] - window + 1, stride)]
    # Pastikan ekor urutan ikut terpakai.
    if (seq.shape[0] - window) % stride != 0:
        out.append(seq[-window:])
    return out


def _recording_dirs(label_dir: Path) -> list[list[Path]]:
    """Kumpulkan rekaman dalam satu folder label.

    - Bila ada subfolder berisi gambar: tiap subfolder = satu rekaman.
    - Bila tidak: frame langsung di folder label = satu rekaman.
    """
    recordings: list[list[Path]] = []
    subdirs = sorted(p for p in label_dir.iterdir() if p.is_dir())
    for sub in subdirs:
        frames = sorted(p for p in sub.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if frames:
            recordings.append(frames)
    direct = sorted(p for p in label_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if direct:
        recordings.append(direct)
    return recordings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", required=True, type=Path)
    ap.add_argument("--mode", required=True, choices=["BISINDO", "SIBI"])
    ap.add_argument("--stage", default="kata", choices=["kata", "kalimat"])
    ap.add_argument("--fps", type=float, default=30.0, help="asumsi fps sumber frame (default 30)")
    ap.add_argument(
        "--window",
        type=int,
        default=0,
        help="pecah urutan menjadi jendela N frame (0 = satu sampel per rekaman)",
    )
    ap.add_argument("--window-stride", type=int, default=8, help="geser antar jendela (default 8)")
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="path hand_landmarker.task")
    args = ap.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"Folder tidak ditemukan: {args.input_dir}")
    if args.window and args.window < 2:
        raise SystemExit("--window minimal 2 frame")
    if args.window_stride < 1:
        raise SystemExit("--window-stride minimal 1")

    max_hands = max_hands_for_mode(args.mode)

    label_dirs = sorted(p for p in args.input_dir.iterdir() if p.is_dir())
    if not label_dirs:
        raise SystemExit("Tidak ada subfolder label di input-dir.")

    total_saved = 0
    total_skipped = 0
    for label_dir in label_dirs:
        label = label_dir.name
        recordings = _recording_dirs(label_dir)
        if not recordings:
            print(f"[{label}] tidak ada frame gambar, dilewati", flush=True)
            continue

        saved = 0
        for frames in recordings:
            seq = _frames_to_sequence(frames, args.model, max_hands, args.fps)
            if seq is None:
                total_skipped += 1
                continue
            for window_seq in _split_windows(seq, args.window, args.window_stride):
                if window_seq.shape[0] < 2:
                    continue
                save_sample(
                    mode=args.mode,
                    stage=args.stage,
                    label=label,
                    features=window_seq,
                    max_hands=max_hands,
                    created_at=time.time(),
                )
                saved += 1
                total_saved += 1
        print(f"[{label}] tersimpan {saved} sampel dari {len(recordings)} rekaman", flush=True)

    print(f"\nSelesai. Total tersimpan: {total_saved}, dilewati (tanpa tangan): {total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
