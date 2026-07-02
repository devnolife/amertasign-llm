"""Tes API mobile: auth, riwayat, kamus, favorit, profil.

Memakai SQLite in-file sementara agar tidak mengganggu data nyata.
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AMERTASIGN_MOBILE_DB_URL", f"sqlite:///{tmp_path / 'mobile.db'}")
    monkeypatch.setenv("AMERTASIGN_JWT_SECRET", "test-secret-panjang-minimal-32-karakter!!")

    # Import semua modul dulu, lalu reload berurutan agar Base & settings segar.
    import app.config as config
    import app.mobile.db as db
    import app.mobile.models as models
    import app.mobile.security as security
    import app.mobile.deps as deps
    import app.mobile.serializers as serializers

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(models)
    importlib.reload(security)
    importlib.reload(deps)
    importlib.reload(serializers)
    import app.routers.mobile_auth as auth_router
    import app.routers.mobile_history as history_router
    import app.routers.mobile_dictionary as dictionary_router
    import app.routers.mobile_users as users_router

    importlib.reload(auth_router)
    importlib.reload(history_router)
    importlib.reload(dictionary_router)
    importlib.reload(users_router)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def register(client: TestClient, username: str = "budi.s", password: str = "rahasia1") -> dict:
    res = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["data"]


def auth_headers(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['accessToken']}"}


def test_register_login_me(client: TestClient) -> None:
    data = register(client)
    assert data["user"]["username"] == "budi.s"
    assert data["user"]["preferredSignLanguage"] == "bisindo"
    assert data["accessToken"] and data["refreshToken"]

    # Username duplikat
    res = client.post("/api/v1/auth/register", json={"username": "budi.s", "password": "rahasia1"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "USERNAME_TAKEN"

    # Username tidak valid
    res = client.post("/api/v1/auth/register", json={"username": "AB", "password": "rahasia1"})
    assert res.status_code == 400

    # Login salah
    res = client.post("/api/v1/auth/login", json={"username": "budi.s", "password": "salah!"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # Login benar + me
    res = client.post("/api/v1/auth/login", json={"username": "budi.s", "password": "rahasia1"})
    assert res.status_code == 200
    res = client.get("/api/v1/auth/me", headers=auth_headers(res.json()["data"]))
    assert res.status_code == 200
    assert res.json()["data"]["user"]["username"] == "budi.s"


def test_refresh_and_logout(client: TestClient) -> None:
    data = register(client)

    res = client.post("/api/v1/auth/refresh", json={"refreshToken": data["refreshToken"]})
    assert res.status_code == 200
    assert res.json()["data"]["accessToken"]

    res = client.post("/api/v1/auth/logout", headers=auth_headers(data))
    assert res.status_code == 200

    # Refresh token sudah direvoke
    res = client.post("/api/v1/auth/refresh", json={"refreshToken": data["refreshToken"]})
    assert res.status_code == 401


def test_history_crud_and_scoping(client: TestClient) -> None:
    a = register(client, "user.a")
    b = register(client, "user.b")

    # Tanpa token → 401
    assert client.get("/api/v1/history").status_code == 401

    for i in range(3):
        res = client.post(
            "/api/v1/history",
            json={"kind": "isyarat-ke-teks", "text": f"halo {i}", "signLanguageType": "bisindo"},
            headers=auth_headers(a),
        )
        assert res.status_code == 200

    res = client.get("/api/v1/history?limit=2", headers=auth_headers(a))
    body = res.json()["data"]
    assert len(body["items"]) == 2
    assert body["nextCursor"]

    # Halaman berikutnya
    res = client.get(f"/api/v1/history?limit=2&cursor={body['nextCursor']}", headers=auth_headers(a))
    assert len(res.json()["data"]["items"]) == 1

    # User B tidak melihat riwayat A dan tidak bisa menghapusnya
    res = client.get("/api/v1/history", headers=auth_headers(b))
    assert res.json()["data"]["items"] == []
    item_id = body["items"][0]["id"]
    assert client.delete(f"/api/v1/history/{item_id}", headers=auth_headers(b)).status_code == 404

    # A hapus satu lalu semua
    assert client.delete(f"/api/v1/history/{item_id}", headers=auth_headers(a)).status_code == 200
    assert client.delete("/api/v1/history", headers=auth_headers(a)).status_code == 200
    res = client.get("/api/v1/history", headers=auth_headers(a))
    assert res.json()["data"]["items"] == []


def test_dictionary_and_favorites(client: TestClient) -> None:
    data = register(client)

    # Isi kamus langsung lewat DB
    import app.mobile.db as db
    from app.mobile.models import DictionaryEntry

    with db.SessionLocal() as session:
        for word in ["Apel", "Ayam", "Buku"]:
            session.add(
                DictionaryEntry(
                    word=word,
                    category="kata_umum",
                    type="bisindo",
                    description=f"Isyarat {word}",
                    image_url=f"/img/{word}.png",
                    video_url=f"/vid/{word}.mp4",
                )
            )
        session.commit()

    res = client.get("/api/v1/dictionary?type=bisindo&search=a")
    items = res.json()["data"]["items"]
    assert {i["word"] for i in items} == {"Apel", "Ayam"}

    res = client.get("/api/v1/dictionary/daily")
    assert res.status_code == 200

    entry_id = items[0]["id"]
    res = client.get(f"/api/v1/dictionary/{entry_id}")
    assert res.status_code == 200
    assert res.json()["data"]["entry"]["id"] == entry_id

    # Favorit
    assert client.put(f"/api/v1/favorites/{entry_id}", headers=auth_headers(data)).status_code == 200
    res = client.get("/api/v1/favorites", headers=auth_headers(data))
    assert res.json()["data"]["ids"] == [entry_id]
    assert client.delete(f"/api/v1/favorites/{entry_id}", headers=auth_headers(data)).status_code == 200
    res = client.get("/api/v1/favorites", headers=auth_headers(data))
    assert res.json()["data"]["ids"] == []


def test_profile_update_and_password(client: TestClient) -> None:
    data = register(client)

    res = client.patch(
        "/api/v1/users/me",
        json={"name": "Budi Santoso", "preferredSignLanguage": "sibi"},
        headers=auth_headers(data),
    )
    user = res.json()["data"]["user"]
    assert user["name"] == "Budi Santoso"
    assert user["preferredSignLanguage"] == "sibi"

    # Ganti password: salah dulu, lalu benar
    res = client.patch(
        "/api/v1/users/me/password",
        json={"currentPassword": "salah!", "newPassword": "barubaru"},
        headers=auth_headers(data),
    )
    assert res.status_code == 401
    res = client.patch(
        "/api/v1/users/me/password",
        json={"currentPassword": "rahasia1", "newPassword": "barubaru"},
        headers=auth_headers(data),
    )
    assert res.status_code == 200

    res = client.post("/api/v1/auth/login", json={"username": "budi.s", "password": "barubaru"})
    assert res.status_code == 200
