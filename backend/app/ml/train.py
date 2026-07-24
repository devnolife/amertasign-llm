"""Training classifier abjad (gestur statis) dari sampel terkumpul.

Mengumpulkan semua sampel statis (num_frames==1) untuk (mode, stage='abjad'),
melatih MLPClassifier sederhana dengan StandardScaler, lalu menyimpan bundle
joblib ke MODELS_DIR sebagai "{mode}_{stage}.joblib".

Bundle kompatibel dengan app.ml.registry: { clf, labels, max_hands, mode, stage }.
Augmentasi opsional (jitter gaussian) menambah ketahanan untuk data kecil.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.config import settings
from app.ml.dataset import iter_records, load_features
from app.ml.normalize import max_hands_for_mode, resample_sequence


@dataclass
class TrainResult:
    mode: str
    stage: str
    labels: list[str]
    n_samples: int
    n_classes: int
    train_accuracy: float
    val_accuracy: float
    model_path: str
    note: Optional[str] = None


def _collect_static_samples(
    mode: str,
    stage: str,
    created_before: Optional[float] = None,
    created_after: Optional[float] = None,
) -> tuple[np.ndarray, list[str], list[float]]:
    X: list[np.ndarray] = []
    y: list[str] = []
    ts: list[float] = []
    for rec in iter_records():
        if rec.mode != mode or rec.stage != stage or rec.num_frames != 1:
            continue
        if created_before is not None and rec.created_at >= created_before:
            continue
        if created_after is not None and rec.created_at < created_after:
            continue
        X.append(load_features(rec).reshape(-1))
        y.append(rec.label)
        ts.append(rec.created_at)
    if not X:
        return np.empty((0, 0), dtype=np.float32), [], []
    return np.stack(X), y, ts


def _augment(X: np.ndarray, y: list[str], times: int, sigma: float) -> tuple[np.ndarray, list[str]]:
    """Augmentasi geometris: rotasi in-plane + skala acak per sampel + jitter kecil.

    Fitur adalah blok-blok 63 dim (21 titik xyz per tangan, wrist-origin), sehingga
    rotasi/skala bisa diterapkan langsung pada titik-titiknya. Jauh lebih efektif
    daripada noise gaussian murni karena meniru variasi pose nyata.
    """
    if times <= 0 or X.shape[0] == 0:
        return X, y
    from app.ml.normalize import FEATURES_PER_HAND

    n, d = X.shape
    if d % FEATURES_PER_HAND != 0:
        # Dimensi tak terduga -> fallback jitter gaussian.
        parts = [X]
        labels = list(y)
        rng = np.random.default_rng(42)
        for _ in range(times):
            parts.append(X + rng.normal(0.0, sigma, size=X.shape).astype(np.float32))
            labels.extend(y)
        return np.concatenate(parts, axis=0), labels

    n_blocks = d // FEATURES_PER_HAND
    rng = np.random.default_rng(42)
    parts = [X]
    labels = list(y)
    for _ in range(times):
        pts = X.reshape(n, n_blocks, 21, 3).copy()
        # Satu transformasi per sampel agar konsisten antar tangan/frame.
        # Augmentasi lebih kuat (terbukti +4pt akurasi lintas-sesi via
        # scripts/holdout_abjad.py): rotasi ±15°, skala 0.85–1.15, translasi
        # kecil per-tangan → model lebih tahan variasi sudut/jarak/posisi kamera.
        angles = rng.normal(0.0, np.deg2rad(15.0), size=n)
        scales = rng.uniform(0.85, 1.15, size=n)
        cos, sin = np.cos(angles), np.sin(angles)
        x_old = pts[..., 0].copy()
        y_old = pts[..., 1].copy()
        c = cos[:, None, None]
        s = sin[:, None, None]
        pts[..., 0] = c * x_old - s * y_old
        pts[..., 1] = s * x_old + c * y_old
        pts *= scales[:, None, None, None]
        # Geser kecil per blok tangan (bukan per titik) meniru pergeseran ROI.
        pts += rng.normal(0.0, 0.03, size=(n, n_blocks, 1, 3))
        pts += rng.normal(0.0, sigma, size=pts.shape)
        # Slot tangan kosong (semua nol) harus tetap nol.
        mask = (X.reshape(n, n_blocks, 21, 3) == 0).all(axis=(2, 3))
        pts[mask] = 0.0
        parts.append(pts.reshape(n, d).astype(np.float32))
        labels.extend(y)
    return np.concatenate(parts, axis=0), labels


def _temporal_split(
    X: np.ndarray, y: list[str], ts: list[float], test_size: float
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Split train/val berbasis waktu per label.

    Auto-capture menghasilkan frame beruntun yang nyaris identik; split acak
    membuat duplikat bocor ke validasi (akurasi menipu). Dengan menahan sampel
    TERBARU tiap label sebagai validasi, evaluasi jadi jujur terhadap sesi baru
    tanpa mengorbankan banyak data latih.
    """
    y_arr = np.asarray(y)
    ts_arr = np.asarray(ts)
    train_idx: list[int] = []
    val_idx: list[int] = []
    for label in np.unique(y_arr):
        idx = np.where(y_arr == label)[0]
        idx = idx[np.argsort(ts_arr[idx])]
        if len(idx) < 3:
            train_idx.extend(idx.tolist())
            continue
        n_val = max(1, int(round(len(idx) * test_size)))
        train_idx.extend(idx[:-n_val].tolist())
        val_idx.extend(idx[-n_val:].tolist())
    if not val_idx:  # dataset terlalu kecil -> evaluasi pada train (dgn catatan)
        val_idx = train_idx
    return (
        X[train_idx],
        X[val_idx],
        [y[i] for i in train_idx],
        [y[i] for i in val_idx],
    )


def _collect_sequence_samples(
    mode: str,
    stage: str,
    seq_len: int,
    created_before: Optional[float] = None,
    created_after: Optional[float] = None,
) -> tuple[np.ndarray, list[str], list[float]]:
    """Kumpulkan sampel urutan (num_frames>1), resample ke seq_len, lalu flatten."""
    X: list[np.ndarray] = []
    y: list[str] = []
    ts: list[float] = []
    for rec in iter_records():
        if rec.mode != mode or rec.stage != stage or rec.num_frames <= 1:
            continue
        if created_before is not None and rec.created_at >= created_before:
            continue
        if created_after is not None and rec.created_at < created_after:
            continue
        seq = load_features(rec)  # (T, F)
        if seq.ndim != 2:
            continue
        X.append(resample_sequence(seq, seq_len).reshape(-1))
        y.append(rec.label)
        ts.append(rec.created_at)
    if not X:
        return np.empty((0, 0), dtype=np.float32), [], []
    return np.stack(X), y, ts


def _fit_and_save(
    X: np.ndarray,
    y: list[str],
    mode: str,
    stage: str,
    augment_times: int,
    augment_sigma: float,
    test_size: float,
    ts: Optional[list[float]] = None,
    extra_bundle: Optional[dict] = None,
) -> TrainResult:
    """Inti training bersama: split, augmentasi, latih MLP, simpan bundle."""
    n_classes = len(set(y))
    if X.shape[0] < 2 or n_classes < 2:
        return TrainResult(
            mode=mode,
            stage=stage,
            labels=sorted(set(y)),
            n_samples=int(X.shape[0]),
            n_classes=n_classes,
            train_accuracy=0.0,
            val_accuracy=0.0,
            model_path="",
            note="Butuh >=2 kelas & cukup sampel. Kumpulkan data lebih banyak via /collect.",
        )

    if ts is not None and len(ts) == X.shape[0]:
        # Split temporal per label: sampel terbaru jadi validasi (anti-bocor
        # untuk frame beruntun yang nyaris identik dari auto-capture).
        X_train, X_val, y_train, y_val = _temporal_split(X, y, ts, test_size)
    else:
        stratify = (
            y if min(np.bincount(np.unique(y, return_inverse=True)[1])) >= 2 else None
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=stratify
        )

    X_train_aug, y_train_aug = _augment(X_train, list(y_train), augment_times, augment_sigma)

    # Catatan: early_stopping sklearn bermasalah dgn label string (isnan) ->
    # andalkan konvergensi adam (tol + n_iter_no_change pada loss training).
    clf = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=(128, 64),
                    activation="relu",
                    max_iter=800,
                    early_stopping=False,
                    n_iter_no_change=20,
                    random_state=42,
                ),
            ),
        ]
    )
    clf.fit(X_train_aug, y_train_aug)

    train_acc = accuracy_score(y_train, clf.predict(X_train))
    val_acc = accuracy_score(y_val, clf.predict(X_val))

    bundle = {
        "clf": clf,
        "labels": list(clf.classes_),
        "max_hands": max_hands_for_mode(mode),
        "mode": mode,
        "stage": stage,
    }
    if extra_bundle:
        bundle.update(extra_bundle)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    model_path = settings.models_dir / f"{mode}_{stage}.joblib"
    joblib.dump(bundle, model_path)

    return TrainResult(
        mode=mode,
        stage=stage,
        labels=sorted(set(y)),
        n_samples=int(X.shape[0]),
        n_classes=n_classes,
        train_accuracy=float(train_acc),
        val_accuracy=float(val_acc),
        model_path=str(model_path),
    )


def train_alphabet(
    mode: str,
    stage: str = "abjad",
    augment_times: int = 4,
    augment_sigma: float = 0.01,
    test_size: float = 0.2,
    created_before: Optional[float] = None,
    created_after: Optional[float] = None,
) -> TrainResult:
    X, y, ts = _collect_static_samples(mode, stage, created_before, created_after)
    return _fit_and_save(
        X, y, mode, stage, augment_times, augment_sigma, test_size, ts=ts
    )


def train_words(
    mode: str,
    stage: str = "kata",
    seq_len: int = 16,
    augment_times: int = 2,
    augment_sigma: float = 0.01,
    test_size: float = 0.2,
    created_before: Optional[float] = None,
    created_after: Optional[float] = None,
) -> TrainResult:
    """Latih classifier kata dari sampel urutan (resample ke seq_len lalu flatten)."""
    X, y, ts = _collect_sequence_samples(
        mode, stage, seq_len, created_before, created_after
    )
    return _fit_and_save(
        X,
        y,
        mode,
        stage,
        augment_times,
        augment_sigma,
        test_size,
        ts=ts,
        extra_bundle={"seq_len": seq_len},
    )


def confusion(mode: str, stage: str = "abjad") -> dict:
    """Confusion matrix sederhana memakai model tersimpan pada seluruh sampel."""
    X, y, _ts = _collect_static_samples(mode, stage)
    model_path = settings.models_dir / f"{mode}_{stage}.joblib"
    if X.shape[0] == 0 or not model_path.exists():
        return {"labels": [], "matrix": []}
    bundle = joblib.load(model_path)
    preds = bundle["clf"].predict(X)
    labels = list(bundle["labels"])
    cm = confusion_matrix(y, preds, labels=labels)
    return {"labels": labels, "matrix": cm.tolist()}
