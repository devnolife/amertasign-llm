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

    # CORS: origin frontend (Next.js dev default 3000)
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

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


settings = Settings()
settings.models_dir.mkdir(parents=True, exist_ok=True)
