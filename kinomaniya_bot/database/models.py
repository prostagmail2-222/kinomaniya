from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64))
    lang: Mapped[str | None] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    added_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Channel(Base):
    """kind = 'sub' (majburiy obuna) yoki 'post' (post joylanadigan kanal)."""

    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("chat_id", "kind", name="uq_channel_chat_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(8), index=True)
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64))
    invite_link: Mapped[str | None] = mapped_column(String(255))


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(64), unique=True)


class Movie(Base):
    """Kino kodi = id. Postgres'da o'chirilgan id qayta ishlatilmaydi."""

    __tablename__ = "movies"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    title_search: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    poster_file_id: Mapped[str | None] = mapped_column(String(512))
    is_series: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    genres: Mapped[list[Genre]] = relationship(
        secondary=movie_genres, lazy="selectin", order_by="Genre.name"
    )


class Episode(Base):
    """Oddiy kino ham 1-qism sifatida saqlanadi; serialda 1..200+ qism."""

    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("movie_id", "number", name="uq_episode_movie_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(16), default="video")
