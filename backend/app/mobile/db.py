"""Koneksi database SQLite (SQLAlchemy) untuk API mobile."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.mobile_db_url,
    connect_args={"check_same_thread": False} if settings.mobile_db_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Buat semua tabel bila belum ada."""
    from app.mobile import models  # noqa: F401 (register mapping)

    Base.metadata.create_all(bind=engine)
