"""Tes integrasi API: health, collect→train→recognize, compose.

Memakai direktori data & model sementara agar tidak mengganggu data nyata.
"""
from __future__ import annotations

import importlib

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Arahkan penyimpanan ke tmp sebelum modul di-load.
    monkeypatch.setenv("AMERTASIGN_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AMERTASIGN_MODELS_DIR", str(tmp_path / "models"))

    import app.config as config

    importlib.reload(config)
    import app.ml.dataset as dataset
    import app.ml.registry as registry
    import app.ml.train as train

    importlib.reload(dataset)
    importlib.reload(train)
    importlib.reload(registry)
    import app.routers.data as data_router
    import app.routers.recognize as recognize_router
    import app.routers.train as train_router
    import app.routers.compose as compose_router

    importlib.reload(data_router)
    importlib.reload(recognize_router)
    importlib.reload(train_router)
    importlib.reload(compose_router)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def _hand(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-0.15, 0.15, (21, 3)).astype("float32")
    pts[0] = [0.5, 0.8, 0.0]
    pts[9] = [0.5, 0.6, 0.0]
    return {
        "handedness": "Right",
        "score": 0.9,
        "landmarks": [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in pts],
    }


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_recognize_without_model_is_stub(client):
    res = client.post(
        "/recognize",
        json={"mode": "SIBI", "stage": "abjad", "hands": [_hand(1)]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["model_loaded"] is False


def test_collect_train_recognize_cycle(client):
    # Kumpulkan 2 huruf, masing-masing dari template berbeda + jitter.
    templates = {"A": 11, "B": 22}
    rng = np.random.default_rng(0)
    for label, base_seed in templates.items():
        base = np.random.default_rng(base_seed).uniform(-0.15, 0.15, (21, 3)).astype("float32")
        for _ in range(15):
            pts = base + rng.normal(0, 0.006, (21, 3)).astype("float32")
            pts[0] = [0.5, 0.8, 0.0]
            pts[9] = [0.5, 0.6, 0.0]
            hand = {
                "handedness": "Right",
                "score": 0.9,
                "landmarks": [
                    {"x": float(x), "y": float(y), "z": float(z)} for x, y, z in pts
                ],
            }
            r = client.post(
                "/collect",
                json={"mode": "SIBI", "stage": "abjad", "label": label, "hands": [hand]},
            )
            assert r.status_code == 200

    stats = client.get("/datasets", params={"mode": "SIBI", "stage": "abjad"}).json()
    assert stats["total"] == 30

    tr = client.post("/train", json={"mode": "SIBI", "stage": "abjad"}).json()
    assert tr["n_classes"] == 2
    assert tr["val_accuracy"] >= 0.8  # data terpisah jelas

    # Recognize satu sampel dari template A.
    base = np.random.default_rng(11).uniform(-0.15, 0.15, (21, 3)).astype("float32")
    base[0] = [0.5, 0.8, 0.0]
    base[9] = [0.5, 0.6, 0.0]
    hand = {
        "handedness": "Right",
        "score": 0.9,
        "landmarks": [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in base],
    }
    out = client.post(
        "/recognize", json={"mode": "SIBI", "stage": "abjad", "hands": [hand]}
    ).json()
    assert out["model_loaded"] is True
    assert out["text"] in {"A", "B"}


def test_compose_stub(client):
    res = client.post(
        "/compose", json={"mode": "BISINDO", "gloss": ["saya", "makan", "nasi"]}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "stub"
    assert body["sentence"] == "Saya makan nasi."
