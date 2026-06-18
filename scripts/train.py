#!/usr/bin/env python3
"""CLI training model abjad/kata dari sampel terkumpul.

Penggunaan:
    python scripts/train.py --mode SIBI                 # abjad
    python scripts/train.py --mode BISINDO --stage kata # kata (urutan)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.train import train_alphabet, train_words  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=["BISINDO", "SIBI"])
    ap.add_argument("--stage", default="abjad", choices=["abjad", "kata"])
    ap.add_argument("--augment-times", type=int, default=2)
    ap.add_argument("--seq-len", type=int, default=16, help="panjang resample (stage kata)")
    args = ap.parse_args()

    if args.stage == "kata":
        result = train_words(
            mode=args.mode,
            stage=args.stage,
            seq_len=args.seq_len,
            augment_times=args.augment_times,
        )
    else:
        result = train_alphabet(
            mode=args.mode, stage=args.stage, augment_times=args.augment_times
        )
    print(f"Mode={result.mode} Stage={result.stage}")
    print(f"Sampel={result.n_samples} Kelas={result.n_classes} -> {result.labels}")
    print(f"Train acc={result.train_accuracy:.3f} Val acc={result.val_accuracy:.3f}")
    if result.note:
        print(f"Catatan: {result.note}")
    else:
        print(f"Model disimpan: {result.model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
