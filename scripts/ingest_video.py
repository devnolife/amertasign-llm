#!/usr/bin/env python3
"""Ingest dataset video publik (gestur dinamis) menjadi sampel urutan landmark.

Mengubah folder video berlabel menjadi sampel urutan (T, F) yang kompatibel
dengan penyimpanan dataset backend (data/recordings + manifest.jsonl), sehingga
bisa dilatih oleh `scripts/train.py --stage kata`.

Struktur input yang diharapkan (label = nama subfolder):
    <input_dir>/
      makan/  video1.mp4 video2.mp4 ...
      minum/  ...
      ...

Contoh sumber publik:
  - SIBI Dataset Mendeley (44pbrbsnkh): sampel video affix/number/alphabet
    di data/public/sibi_mendeley_44pbrbsnkh/sibi-dataset-dib-example-face-blurred/.
    Dataset lengkap memerlukan DUA; setelah diperoleh, arahkan --input-dir
    ke folder video lengkapnya.

Butuh `mediapipe` & `opencv-python` (scripts/requirements-ingest.txt) dan model
`hand_landmarker.task` (di-setup oleh scripts/fetch-assets.sh).

Penggunaan:
    python scripts/ingest_video.py \
        --input-dir data/public/sibi_mendeley_44pbrbsnkh/sibi-dataset-dib-example-face-blurred/number \
        --mode SIBI --stage kata
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

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
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


def _video_to_sequence(
    video_path: Path, detector, max_hands: int, stride: int
) -> np.ndarray | None:
    """Ekstrak urutan fitur (T, F) dari satu video; None bila tanpa tangan."""
    import cv2
    import mediapipe as mp

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    feats: list[np.ndarray] = []
    has_hand: list[bool] = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % stride == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(frame_idx * 1000.0 / fps)
            result = detector.detect_for_video(mp_image, ts_ms)
            hands = _to_hands(result)
            feats.append(frame_to_features(hands, max_hands=max_hands))
            has_hand.append(bool(hands))
        frame_idx += 1
    cap.release()

    if not any(has_hand):
        return None
    # Pangkas frame kosong di awal/akhir (sebelum/ sesudah gestur).
    first = has_hand.index(True)
    last = len(has_hand) - 1 - has_hand[::-1].index(True)
    seq = np.stack(feats[first : last + 1]).astype(np.float32)
    return seq if seq.shape[0] >= 2 else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", required=True, type=Path)
    ap.add_argument("--mode", required=True, choices=["BISINDO", "SIBI"])
    ap.add_argument("--stage", default="kata", choices=["kata", "kalimat"])
    ap.add_argument("--stride", type=int, default=2, help="ambil 1 dari N frame (default 2)")
    ap.add_argument("--limit-per-label", type=int, default=0, help="0 = tanpa batas")
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="path hand_landmarker.task")
    args = ap.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"Folder tidak ditemukan: {args.input_dir}")

    max_hands = max_hands_for_mode(args.mode)

    label_dirs = sorted(p for p in args.input_dir.iterdir() if p.is_dir())
    if not label_dirs:
        raise SystemExit("Tidak ada subfolder label di input-dir.")

    total_saved = 0
    total_skipped = 0
    for label_dir in label_dirs:
        label = label_dir.name
        videos = [p for p in sorted(label_dir.rglob("*")) if p.suffix.lower() in VIDEO_EXTS]
        if args.limit_per_label > 0:
            videos = videos[: args.limit_per_label]

        saved = 0
        for vid_path in videos:
            # Detector VIDEO mode butuh timestamp monoton -> satu detector per video.
            detector = _load_detector(args.model, num_hands=max(2, max_hands))
            seq = _video_to_sequence(vid_path, detector, max_hands, args.stride)
            detector.close()
            if seq is None:
                total_skipped += 1
                continue
            save_sample(
                mode=args.mode,
                stage=args.stage,
                label=label,
                features=seq,
                max_hands=max_hands,
                created_at=time.time(),
            )
            saved += 1
            total_saved += 1
        print(f"[{label}] tersimpan {saved} / {len(videos)} video", flush=True)

    print(f"\nSelesai. Total tersimpan: {total_saved}, dilewati (tanpa tangan): {total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
