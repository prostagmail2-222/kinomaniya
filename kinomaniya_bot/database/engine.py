from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from config import Settings
from database.models import Base

log = logging.getLogger(__name__)


def make_engine(settings: Settings) -> AsyncEngine:
    kwargs: dict = {}
    if settings.db_url.startswith("postgresql"):
        kwargs.update(
            pool_size=8,
            max_overflow=12,
            pool_recycle=240,
            pool_timeout=30,
            connect_args=settings.db_args,
        )
    return create_async_engine(settings.db_url, pool_pre_ping=True, **kwargs)


def make_session_maker(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine, attempts: int = 6) -> None:
    """Jadvallarni yaratadi. Baza "uyg'onayotgan" bo'lsa bir necha marta urinadi."""
    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception:
            log.exception("Bazaga ulanib bo'lmadi (urinish %s/%s)", attempt, attempts)
            if attempt == attempts:
                raise
            await asyncio.sleep(5 * attempt)

    if engine.dialect.name == "postgresql":
        # Qisman qidiruv (LIKE '%abc%') tez ishlashi uchun trigram indeks
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_movies_title_trgm "
                        "ON movies USING gin (title_search gin_trgm_ops)"
                    )
                )
        except Exception:
            log.warning("pg_trgm indeksi yaratilmadi (qidiruv baribir ishlaydi)")
