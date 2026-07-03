"""Koneksi database SQLite (SQLAlchemy) untuk API mobile."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.mobile_db_url.startswith("sqlite")

engine = create_engine(
    settings.mobile_db_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
)

if _is_sqlite:
    # WAL + busy_timeout: izinkan baca-tulis paralel antar worker/koneksi tanpa
    # error "database is locked" saat beban produksi ringan-menengah.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Buat semua tabel bila belum ada."""
    from app.mobile import models  # noqa: F401 (register mapping)

    Base.metadata.create_all(bind=engine)
