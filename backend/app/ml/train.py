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
from app.ml.normalize import max_hands_for_mode


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


def _collect_static_samples(mode: str, stage: str) -> tuple[np.ndarray, list[str]]:
    X: list[np.ndarray] = []
    y: list[str] = []
    for rec in iter_records():
        if rec.mode != mode or rec.stage != stage or rec.num_frames != 1:
            continue
        X.append(load_features(rec).reshape(-1))
        y.append(rec.label)
    if not X:
        return np.empty((0, 0), dtype=np.float32), []
    return np.stack(X), y


def _augment(X: np.ndarray, y: list[str], times: int, sigma: float) -> tuple[np.ndarray, list[str]]:
    if times <= 0:
        return X, y
    parts = [X]
    labels = list(y)
    rng = np.random.default_rng(42)
    for _ in range(times):
        parts.append(X + rng.normal(0.0, sigma, size=X.shape).astype(np.float32))
        labels.extend(y)
    return np.concatenate(parts, axis=0), labels


def train_alphabet(
    mode: str,
    stage: str = "abjad",
    augment_times: int = 2,
    augment_sigma: float = 0.01,
    test_size: float = 0.2,
) -> TrainResult:
    X, y = _collect_static_samples(mode, stage)
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

    stratify = y if min(np.bincount(np.unique(y, return_inverse=True)[1])) >= 2 else None
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )

    X_train_aug, y_train_aug = _augment(X_train, list(y_train), augment_times, augment_sigma)

    clf = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=(128, 64),
                    activation="relu",
                    max_iter=500,
                    early_stopping=False,
                    random_state=42,
                ),
            ),
        ]
    )
    clf.fit(X_train_aug, y_train_aug)

    train_acc = accuracy_score(y_train, clf.predict(X_train))
    val_acc = accuracy_score(y_val, clf.predict(X_val))

    labels = sorted(set(y))
    bundle = {
        "clf": clf,
        "labels": list(clf.classes_),
        "max_hands": max_hands_for_mode(mode),
        "mode": mode,
        "stage": stage,
    }
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    model_path = settings.models_dir / f"{mode}_{stage}.joblib"
    joblib.dump(bundle, model_path)

    return TrainResult(
        mode=mode,
        stage=stage,
        labels=labels,
        n_samples=int(X.shape[0]),
        n_classes=n_classes,
        train_accuracy=float(train_acc),
        val_accuracy=float(val_acc),
        model_path=str(model_path),
    )


def confusion(mode: str, stage: str = "abjad") -> dict:
    """Confusion matrix sederhana memakai model tersimpan pada seluruh sampel."""
    X, y = _collect_static_samples(mode, stage)
    model_path = settings.models_dir / f"{mode}_{stage}.joblib"
    if X.shape[0] == 0 or not model_path.exists():
        return {"labels": [], "matrix": []}
    bundle = joblib.load(model_path)
    preds = bundle["clf"].predict(X)
    labels = list(bundle["labels"])
    cm = confusion_matrix(y, preds, labels=labels)
    return {"labels": labels, "matrix": cm.tolist()}
