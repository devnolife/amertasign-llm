"""Model database untuk API mobile (user, riwayat, kamus, favorit)."""
from __future__ import annotations

import time
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.mobile.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def now_ts() -> float:
    return time.time()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preferred_sign_language: Mapped[str] = mapped_column(String(8), default="bisindo")
    streak: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[float] = mapped_column(Float, default=now_ts)

    histories: Mapped[list["TranslationHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[float] = mapped_column(Float)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class TranslationHistory(Base):
    __tablename__ = "translation_history"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(24))  # 'isyarat-ke-teks' | 'teks-ke-isyarat'
    text: Mapped[str] = mapped_column(Text)
    sign_language_type: Mapped[str] = mapped_column(String(8))  # 'bisindo' | 'sibi'
    created_at: Mapped[float] = mapped_column(Float, default=now_ts)

    user: Mapped[User] = relationship(back_populates="histories")

    __table_args__ = (Index("ix_history_user_created", "user_id", "created_at"),)


class DictionaryEntry(Base):
    __tablename__ = "dictionary_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    word: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(16))  # alfabet|angka|kata_umum|frasa
    type: Mapped[str] = mapped_column(String(8))  # bisindo|sibi
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(512), default="")
    video_url: Mapped[str] = mapped_column(String(512), default="")

    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_dictionary_type_category", "type", "category"),)


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("dictionary_entries.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped[User] = relationship(back_populates="favorites")
    entry: Mapped[DictionaryEntry] = relationship(back_populates="favorites")
