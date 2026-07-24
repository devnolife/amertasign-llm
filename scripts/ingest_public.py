#!/usr/bin/env python3
"""Ingest dataset gambar publik (mis. SIBI alphabet) menjadi sampel landmark.

Mengubah folder gambar berlabel menjadi sampel fitur landmark yang kompatibel
dengan penyimpanan dataset backend (data/recordings + manifest.jsonl), sehingga
bisa langsung dilatih oleh `scripts/train.py`.

Struktur input yang diharapkan (image-folder, label = nama subfolder):
    <input_dir>/
      A/ img001.jpg img002.jpg ...
      B/ ...
      ...

Contoh sumber publik:
  - SIBI alphabet (Kaggle): cari "SIBI alphabet" / "Indonesian Sign Language SIBI".
  - BISINDO: sumber terbuka terbatas; pertimbangkan merekam sendiri via Recorder UI.

Catatan: butuh `mediapipe` & `opencv-python`. Skrip memakai **MediaPipe Tasks API**
(HandLandmarker) — konsisten dengan ekstraksi landmark di frontend — sehingga butuh
file model `hand_landmarker.task`. Secara default diambil dari
`frontend/public/mediapipe/models/hand_landmarker.task` (di-setup oleh
`scripts/fetch-assets.sh`); override dengan `--model`.

    pip install mediapipe opencv-python

Penggunaan:
    python scripts/ingest_public.py --input-dir data/public/sibi_alphabet \
        --mode SIBI --stage abjad
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
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import (
            HandLandmarker,
            HandLandmarkerOptions,
            RunningMode,
        )
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Butuh mediapipe & Pillow. Install: pip install mediapipe pillow"
        ) from exc

    if not model_path.exists():
        raise SystemExit(
            f"Model tidak ditemukan: {model_path}\n"
            "Jalankan scripts/fetch-assets.sh atau berikan --model."
        )

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=RunningMode.IMAGE,
        num_hands=num_hands,
        # Foto dataset sering memotong tangan di tepi frame — threshold rendah
        # + padding (di _read_image) menaikkan tingkat deteksi signifikan.
        min_hand_detection_confidence=0.1,
        min_hand_presence_confidence=0.1,
    )
    return HandLandmarker.create_from_options(options)


def _read_image(img_path: Path, max_side: int = 1024, pad_frac: float = 0.2):
    """Baca gambar -> array RGB: koreksi EXIF, resize, dan padding tepi.

    Padding membuat tangan yang terpotong tepi foto tetap 'utuh' di mata palm
    detector MediaPipe (menaikkan yield deteksi pada foto HP).
    """
    import numpy as _np
    from PIL import Image, ImageOps

    try:
        im = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")
    except Exception:
        return None
    im.thumbnail((max_side, max_side))
    w, h = im.size
    pad = int(pad_frac * max(w, h))
    canvas = Image.new("RGB", (w + 2 * pad, h + 2 * pad), (20, 20, 20))
    canvas.paste(im, (pad, pad))
    return _np.asarray(canvas)


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", required=True, type=Path)
    ap.add_argument("--mode", required=True, choices=["BISINDO", "SIBI"])
    ap.add_argument("--stage", default="abjad", choices=["abjad", "kata", "kalimat"])
    ap.add_argument("--limit-per-label", type=int, default=0, help="0 = tanpa batas")
    ap.add_argument("--min-hands", type=int, default=1, help="minimal tangan terdeteksi agar disimpan")
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="path hand_landmarker.task")
    args = ap.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"Folder tidak ditemukan: {args.input_dir}")

    import mediapipe as mp

    max_hands = max_hands_for_mode(args.mode)
    detector = _load_detector(args.model, num_hands=max(2, max_hands))

    label_dirs = sorted(p for p in args.input_dir.iterdir() if p.is_dir())
    if not label_dirs:
        raise SystemExit("Tidak ada subfolder label di input-dir.")

    total_saved = 0
    total_skipped = 0
    for label_dir in label_dirs:
        label = label_dir.name
        images = [
            p
            for p in sorted(label_dir.iterdir())
            if p.suffix.lower() in IMAGE_EXTS and not p.name.startswith("._")
        ]
        if args.limit_per_label > 0:
            images = images[: args.limit_per_label]

        saved = 0
        for img_path in images:
            rgb = _read_image(img_path)
            if rgb is None:
                total_skipped += 1
                continue
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)
            hands = _to_hands(result)
            if len(hands) < args.min_hands:
                total_skipped += 1
                continue
            features = frame_to_features(hands, max_hands=max_hands)
            save_sample(
                mode=args.mode,
                stage=args.stage,
                label=label,
                features=np.asarray(features, dtype=np.float32),
                max_hands=max_hands,
                created_at=time.time(),
            )
            saved += 1
            total_saved += 1
        print(f"[{label}] tersimpan {saved} / {len(images)} gambar")

    print(f"\nSelesai. Total tersimpan: {total_saved}, dilewati (tanpa tangan): {total_skipped}")
    detector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
