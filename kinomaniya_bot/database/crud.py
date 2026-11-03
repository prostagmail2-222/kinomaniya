from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Admin,
    Channel,
    Episode,
    Genre,
    Movie,
    User,
    movie_genres,
)
from utils.cache import genres_cache
from utils.helpers import norm


def _insert(session: AsyncSession, model):
    fn = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    return fn(model)


# ───────────────────────── users ─────────────────────────
async def upsert_user(session: AsyncSession, uid: int, full_name: str | None, username: str | None) -> None:
    stmt = _insert(session, User).values(id=uid, full_name=full_name, username=username)
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.id], set_={"full_name": full_name, "username": username}
    )
    await session.execute(stmt)
    await session.commit()


async def get_user_lang(session: AsyncSession, uid: int) -> str | None:
    return await session.scalar(select(User.lang).where(User.id == uid))


async def set_user_lang(session: AsyncSession, uid: int, lang: str) -> None:
    await session.execute(update(User).where(User.id == uid).values(lang=lang))
    await session.commit()


# ───────────────────────── admins ─────────────────────────
async def load_admin_ids(session: AsyncSession) -> set[int]:
    return set((await session.scalars(select(Admin.user_id))).all())


async def list_admins(session: AsyncSession) -> list[tuple[int, str | None]]:
    rows = await session.execute(
        select(Admin.user_id, User.full_name)
        .outerjoin(User, User.id == Admin.user_id)
        .order_by(Admin.created_at)
    )
    return [(r[0], r[1]) for r in rows.all()]


async def add_admin(session: AsyncSession, uid: int, added_by: int) -> None:
    stmt = _insert(session, Admin).values(user_id=uid, added_by=added_by)
    await session.execute(stmt.on_conflict_do_nothing(index_elements=[Admin.user_id]))
    await session.commit()


async def remove_admin(session: AsyncSession, uid: int) -> None:
    await session.execute(delete(Admin).where(Admin.user_id == uid))
    await session.commit()


# ───────────────────────── channels ─────────────────────────
async def get_channels(session: AsyncSession, kind: str) -> list[Channel]:
    res = await session.scalars(select(Channel).where(Channel.kind == kind).order_by(Channel.id))
    return list(res.all())


async def add_channel(
    session: AsyncSession,
    kind: str,
    chat_id: int,
    title: str,
    username: str | None,
    invite_link: str | None,
) -> None:
    ch = await session.scalar(
        select(Channel).where(Channel.kind == kind, Channel.chat_id == chat_id)
    )
    if ch:
        ch.title, ch.username, ch.invite_link = title, username, invite_link
    else:
        session.add(
            Channel(kind=kind, chat_id=chat_id, title=title, username=username, invite_link=invite_link)
        )
    await session.commit()


async def remove_channel(session: AsyncSession, pk: int) -> None:
    await session.execute(delete(Channel).where(Channel.id == pk))
    await session.commit()


# ───────────────────────── genres ─────────────────────────
async def get_or_create_genres(session: AsyncSession, names: list[str]) -> list[Genre]:
    wanted: dict[str, str] = {}
    for n in names:
        wanted.setdefault(norm(n), n)
    if not wanted:
        return []
    rows = (await session.scalars(select(Genre).where(Genre.key.in_(list(wanted))))).all()
    existing = {g.key: g for g in rows}
    result: list[Genre] = []
    for key, name in wanted.items():
        g = existing.get(key)
        if g is None:
            g = Genre(name=name, key=key)
            session.add(g)
        result.append(g)
    return result


async def genres_with_counts(session: AsyncSession) -> list[tuple[int, str, int]]:
    rows = await session.execute(
        select(Genre.id, Genre.name, func.count(movie_genres.c.movie_id))
        .join(movie_genres, movie_genres.c.genre_id == Genre.id)
        .group_by(Genre.id, Genre.name)
        .order_by(Genre.name)
    )
    return [(r[0], r[1], r[2]) for r in rows.all()]


async def get_genre(session: AsyncSession, genre_id: int) -> Genre | None:
    return await session.get(Genre, genre_id)


# ───────────────────────── movies ─────────────────────────
async def create_movie(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
    poster_file_id: str | None,
    is_series: bool,
    genres: list[str],
) -> Movie:
    genre_objs = await get_or_create_genres(session, genres)
    movie = Movie(
        title=title,
        title_search=norm(title),
        description=description,
        poster_file_id=poster_file_id,
        is_series=is_series,
        genres=genre_objs,
    )
    session.add(movie)
    await session.commit()
    genres_cache.clear()
    return movie


async def get_movie(session: AsyncSession, movie_id: int) -> Movie | None:
    if movie_id <= 0 or movie_id > 2_000_000_000:
        return None
    return await session.get(Movie, movie_id)


async def get_movie_brief(session: AsyncSession, movie_id: int) -> tuple[str, bool] | None:
    row = (
        await session.execute(select(Movie.title, Movie.is_series).where(Movie.id == movie_id))
    ).first()
    return (row[0], bool(row[1])) if row else None


async def search_movies(session: AsyncSession, query: str, limit: int = 21) -> list[tuple[int, str]]:
    words = norm(query).split()[:6]
    if not words:
        return []
    conds = [Movie.title_search.contains(w, autoescape=True) for w in words]
    rows = await session.execute(
        select(Movie.id, Movie.title).where(*conds).order_by(Movie.id.desc()).limit(limit)
    )
    return [(r[0], r[1]) for r in rows.all()]


async def list_movies(session: AsyncSession, page: int, per_page: int) -> tuple[list[tuple[int, str]], int]:
    total = await session.scalar(select(func.count(Movie.id))) or 0
    rows = await session.execute(
        select(Movie.id, Movie.title)
        .order_by(Movie.id.desc())
        .offset(page * per_page)
        .limit(per_page)
    )
    return [(r[0], r[1]) for r in rows.all()], total


async def latest_movies(session: AsyncSession, limit: int = 10) -> list[tuple[int, str]]:
    rows = await session.execute(select(Movie.id, Movie.title).order_by(Movie.id.desc()).limit(limit))
    return [(r[0], r[1]) for r in rows.all()]


async def movies_by_genre(
    session: AsyncSession, genre_id: int, page: int, per_page: int
) -> tuple[list[tuple[int, str]], int]:
    total = (
        await session.scalar(
            select(func.count()).select_from(movie_genres).where(movie_genres.c.genre_id == genre_id)
        )
        or 0
    )
    rows = await session.execute(
        select(Movie.id, Movie.title)
        .join(movie_genres, movie_genres.c.movie_id == Movie.id)
        .where(movie_genres.c.genre_id == genre_id)
        .order_by(Movie.id.desc())
        .offset(page * per_page)
        .limit(per_page)
    )
    return [(r[0], r[1]) for r in rows.all()], total


async def update_movie(session: AsyncSession, movie_id: int, **fields) -> None:
    if "title" in fields:
        fields["title_search"] = norm(fields["title"])
    await session.execute(update(Movie).where(Movie.id == movie_id).values(**fields))
    await session.commit()


async def set_movie_genres(session: AsyncSession, movie_id: int, names: list[str]) -> None:
    movie = await session.get(Movie, movie_id)
    if movie is None:
        return
    movie.genres = await get_or_create_genres(session, names)
    await session.commit()
    genres_cache.clear()


async def delete_movie(session: AsyncSession, movie_id: int) -> None:
    await session.execute(delete(movie_genres).where(movie_genres.c.movie_id == movie_id))
    await session.execute(delete(Episode).where(Episode.movie_id == movie_id))
    await session.execute(delete(Movie).where(Movie.id == movie_id))
    await session.commit()
    genres_cache.clear()


# ───────────────────────── episodes ─────────────────────────
async def episode_numbers(session: AsyncSession, movie_id: int) -> list[int]:
    res = await session.scalars(
        select(Episode.number).where(Episode.movie_id == movie_id).order_by(Episode.number)
    )
    return list(res.all())


async def episode_count(session: AsyncSession, movie_id: int) -> int:
    return await session.scalar(select(func.count(Episode.id)).where(Episode.movie_id == movie_id)) or 0


async def get_episode(session: AsyncSession, movie_id: int, number: int) -> Episode | None:
    return await session.scalar(
        select(Episode).where(Episode.movie_id == movie_id, Episode.number == number)
    )


async def next_episode_number(session: AsyncSession, movie_id: int) -> int:
    last = await session.scalar(
        select(func.coalesce(func.max(Episode.number), 0)).where(Episode.movie_id == movie_id)
    )
    return int(last or 0) + 1


async def set_episode(
    session: AsyncSession, movie_id: int, number: int, file_id: str, file_type: str
) -> None:
    """Qism bo'lsa — almashtiradi, bo'lmasa — qo'shadi."""
    ep = await get_episode(session, movie_id, number)
    if ep:
        ep.file_id, ep.file_type = file_id, file_type
    else:
        session.add(Episode(movie_id=movie_id, number=number, file_id=file_id, file_type=file_type))
    await session.commit()


async def delete_episode(session: AsyncSession, movie_id: int, number: int) -> bool:
    res = await session.execute(
        delete(Episode).where(Episode.movie_id == movie_id, Episode.number == number)
    )
    await session.commit()
    return bool(res.rowcount)
