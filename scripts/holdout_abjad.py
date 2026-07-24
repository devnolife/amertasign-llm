#!/usr/bin/env python3
"""Uji jujur generalisasi lintas-sesi untuk model abjad BISINDO.

Protokol: latih pada satu hari perekaman, uji pada hari lain (benar-benar sesi
berbeda). Ini mengukur seberapa baik model bekerja pada sesi baru yang belum
pernah dilihat — angka yang relevan untuk penggunaan nyata, bukan akurasi pada
data latih.

Membandingkan kekuatan augmentasi geometris (rotasi/skala/translasi) sebagai
satu-satunya lever yang belum diuji tuntas.

Jalankan:
    backend/.venv/bin/python scripts/holdout_abjad.py
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sklearn.neural_network import MLPClassifier  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app.ml.dataset import iter_records, load_features  # noqa: E402
from app.ml.normalize import FEATURES_PER_HAND  # noqa: E402


def load_cohort():
    X, y, day = [], [], []
    for rec in iter_records():
        if rec.mode != "BISINDO" or rec.stage != "abjad" or rec.num_frames != 1:
            continue
        X.append(load_features(rec).reshape(-1))
        y.append(rec.label)
        day.append(datetime.date.fromtimestamp(rec.created_at).isoformat())
    return np.stack(X), np.array(y), np.array(day)


def augment(X, y, times, deg, scale_lo, scale_hi, trans, sigma, seed=42):
    if times <= 0:
        return X, y
    n, d = X.shape
    n_blocks = d // FEATURES_PER_HAND
    rng = np.random.default_rng(seed)
    parts, labels = [X], list(y)
    for _ in range(times):
        pts = X.reshape(n, n_blocks, 21, 3).copy()
        angles = rng.normal(0.0, np.deg2rad(deg), size=n)
        scales = rng.uniform(scale_lo, scale_hi, size=n)
        cos, sin = np.cos(angles), np.sin(angles)
        xo, yo = pts[..., 0].copy(), pts[..., 1].copy()
        c, s = cos[:, None, None], sin[:, None, None]
        pts[..., 0] = c * xo - s * yo
        pts[..., 1] = s * xo + c * yo
        pts *= scales[:, None, None, None]
        if trans > 0:
            shift = rng.normal(0.0, trans, size=(n, n_blocks, 1, 3))
            pts += shift
        pts += rng.normal(0.0, sigma, size=pts.shape)
        mask = (X.reshape(n, n_blocks, 21, 3) == 0).all(axis=(2, 3))
        pts[mask] = 0.0
        parts.append(pts.reshape(n, d).astype(np.float32))
        labels.extend(y)
    return np.concatenate(parts, axis=0), labels


def make_clf(hidden=(128, 64)):
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=hidden,
                    activation="relu",
                    max_iter=800,
                    early_stopping=False,
                    n_iter_no_change=20,
                    random_state=42,
                ),
            ),
        ]
    )


def evaluate(Xtr, ytr, Xte, yte, aug):
    Xa, ya = augment(Xtr, ytr, **aug)
    clf = make_clf()
    clf.fit(Xa, ya)
    return (clf.predict(Xte) == yte).mean()


def main() -> int:
    X, y, day = load_cohort()
    days = sorted(set(day.tolist()))
    print("Cohort hari:", {d: int((day == d).sum()) for d in days})

    # Hari live (webcam) = yang punya banyak sampel; drive 07-20 domain beda.
    live_days = ["2026-06-18", "2026-07-15"]
    live_days = [d for d in live_days if d in days]
    if len(live_days) < 2:
        print("Butuh >=2 hari live untuk holdout lintas-sesi.")
        return 1

    configs = {
        "sekarang (deg8 sc.92-1.08 t0)": dict(
            times=2, deg=8.0, scale_lo=0.92, scale_hi=1.08, trans=0.0, sigma=0.01
        ),
        "kuat (deg15 sc.85-1.15 t0.03)": dict(
            times=4, deg=15.0, scale_lo=0.85, scale_hi=1.15, trans=0.03, sigma=0.015
        ),
        "ekstrem (deg22 sc.8-1.2 t0.05)": dict(
            times=6, deg=22.0, scale_lo=0.80, scale_hi=1.20, trans=0.05, sigma=0.02
        ),
    }

    for name, aug in configs.items():
        accs = []
        for test_day in live_days:
            tr = day != test_day
            te = day == test_day
            # Latih pada semua hari KECUALI test_day (lintas-sesi jujur).
            accs.append(evaluate(X[tr], y[tr], X[te], y[te], aug))
        mean = float(np.mean(accs))
        detail = ", ".join(f"{d}={a:.3f}" for d, a in zip(live_days, accs))
        print(f"{name:34s} lintas-sesi rata2={mean:.3f}  ({detail})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
