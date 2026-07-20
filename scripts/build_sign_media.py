#!/usr/bin/env python3
"""Bangun media peraga BISINDO dari dataset frame dan sinkronkan kamus mobile.

Sumber default:
- data/public/drive_20260720/Huruf/<label>/*.jpg
- data/public/drive_20260720/Angka/<label>/*.jpg
- data/public/drive_20260720/Kata 1/<label>/*.jpg

Output:
- data/public/sign_media/bisindo/{alfabet,angka,kata_umum}/...
- entri ``dictionary_entries`` pada database mobile

Jalankan dari root repositori:
    backend/.venv/bin/python scripts/build_sign_media.py
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.mobile.db import SessionLocal, init_db  # noqa: E402
from app.mobile.models import DictionaryEntry  # noqa: E402

DEFAULT_SOURCE = ROOT / "data" / "public" / "drive_20260720"
DEFAULT_OUTPUT = ROOT / "data" / "public" / "sign_media" / "bisindo"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "-".join(normalized.lower().strip().split())


def frames(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)


def make_video(source: Path, output: Path, fps: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-pattern_type",
        "glob",
        "-i",
        str(source / "*.jpg"),
        "-vf",
        "scale=640:-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "25",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)


def upsert_entry(
    *, label: str, category: str, image_url: str = "", video_url: str = ""
) -> None:
    entry_id = f"media-bi-{category[:4]}-{slugify(label)}"[:32]
    descriptions = {
        "alfabet": f"Peragaan bentuk tangan BISINDO untuk huruf {label}.",
        "angka": f"Peragaan gerakan BISINDO untuk angka {label}.",
        "kata_umum": f"Peragaan gerakan BISINDO untuk kata “{label}”.",
    }
    with SessionLocal() as db:
        entry = db.get(DictionaryEntry, entry_id)
        if entry is None:
            entry = DictionaryEntry(id=entry_id)
        entry.word = label
        entry.category = category
        entry.type = "bisindo"
        entry.description = descriptions[category]
        entry.image_url = image_url
        entry.video_url = video_url
        db.add(entry)
        db.commit()


def build_alphabet(source_root: Path, output_root: Path) -> int:
    source = source_root / "Huruf"
    if not source.is_dir():
        return 0
    count = 0
    for label_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        images = frames(label_dir)
        if not images:
            continue
        label = label_dir.name.upper()
        destination = output_root / "alfabet" / f"{slugify(label)}.jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(images[len(images) // 2], destination)
        upsert_entry(
            label=label,
            category="alfabet",
            image_url=f"/api/v1/media/bisindo/alfabet/{destination.name}",
        )
        count += 1

    # Dataset drive hanya A-Y. Lengkapi Z dari dataset BISINDO publik bila ada.
    if not (source / "Z").exists():
        z_candidates = frames(ROOT / "data" / "public" / "bisindo_rhiosutoyo" / "Z")
        if z_candidates:
            destination = output_root / "alfabet" / "z.jpg"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(z_candidates[len(z_candidates) // 2], destination)
            upsert_entry(
                label="Z",
                category="alfabet",
                image_url="/api/v1/media/bisindo/alfabet/z.jpg",
            )
            count += 1
    return count


def build_sequences(
    source_root: Path,
    output_root: Path,
    source_name: str,
    category: str,
    output_name: str,
    fps: int,
) -> int:
    source = source_root / source_name
    if not source.is_dir():
        return 0
    count = 0
    for label_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        images = frames(label_dir)
        if len(images) < 2:
            continue
        slug = slugify(label_dir.name)
        media_dir = output_root / output_name
        video = media_dir / f"{slug}.mp4"
        thumbnail = media_dir / f"{slug}.jpg"
        make_video(label_dir, video, fps)
        shutil.copy2(images[len(images) // 2], thumbnail)
        base = f"/api/v1/media/bisindo/{output_name}/{slug}"
        upsert_entry(
            label=label_dir.name,
            category=category,
            image_url=f"{base}.jpg",
            video_url=f"{base}.mp4",
        )
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fps", type=int, default=12)
    args = parser.parse_args()

    if not args.source.is_dir():
        raise SystemExit(f"Folder sumber tidak ditemukan: {args.source}")
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg tidak ditemukan di PATH.")

    init_db()
    alphabet = build_alphabet(args.source, args.output)
    numbers = build_sequences(args.source, args.output, "Angka", "angka", "angka", args.fps)
    words = build_sequences(
        args.source, args.output, "Kata 1", "kata_umum", "kata", args.fps
    )
    print(
        f"Selesai: {alphabet} alfabet, {numbers} angka, {words} kata "
        f"→ {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
