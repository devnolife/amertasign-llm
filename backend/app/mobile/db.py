"""Koneksi database SQLite (SQLAlchemy) untuk API mobile."""
from __future__ import annotations

from sqlalchemy import create_engine, event, inspect, text
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

    # Migrasi ringan untuk database yang dibuat sebelum dukungan email/Google.
    # Alembic belum dipakai pada proyek ini; ALTER bersifat idempoten.
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        if "email" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(254)"))
        if "google_id" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(128)"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)")
        )
