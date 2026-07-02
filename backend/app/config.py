"""Konfigurasi aplikasi backend amertasign-llm."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root project (amertasign-llm/) = dua level di atas file ini (app/ -> backend/ -> root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "backend" / "models"


class Settings(BaseSettings):
    """Pengaturan yang dapat dioverride lewat environment / file .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AMERTASIGN_", extra="ignore")

    app_name: str = "amertasign-llm backend"
    debug: bool = True

    # CORS: origin frontend (Next.js dev default 3030)
    cors_origins: list[str] = ["http://localhost:3030", "http://127.0.0.1:3030"]
    # Regex origin tambahan (mis. URL tunnel publik). Kosong = nonaktif.
    # Default mengizinkan domain quick-tunnel Cloudflare & VS Code Dev Tunnels.
    cors_origin_regex: str = r"https://.*\.(trycloudflare\.com|devtunnels\.ms)"

    # Lokasi penyimpanan
    data_dir: Path = DATA_DIR
    models_dir: Path = MODELS_DIR

    # Ambang batas confidence minimum agar prediksi ditampilkan
    min_confidence: float = 0.6

    # Konfigurasi LLM (dipakai pada tahap kalimat / Fase 5) — pluggable
    llm_provider: str = "stub"  # stub | openai-compatible
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # API mobile (/api/v1): database & JWT
    mobile_db_url: str = f"sqlite:///{DATA_DIR / 'mobile.db'}"
    # WAJIB dioverride di produksi via AMERTASIGN_JWT_SECRET (min. 32 karakter)
    jwt_secret: str = "dev-only-insecure-secret-ganti-di-produksi!!"
    access_token_minutes: int = 15
    refresh_token_days: int = 30


settings = Settings()
settings.models_dir.mkdir(parents=True, exist_ok=True)
