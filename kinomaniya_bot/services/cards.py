from __future__ import annotations

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.models import Movie
from keyboards.user import movie_card_kb
from utils.helpers import clip, esc
from utils.texts import t


def _genres(movie: Movie) -> str:
    return ", ".join(g.name for g in movie.genres) or "—"


def _desc(movie: Movie, genres: str) -> str:
    room = max(0, 1000 - (len(movie.title) + len(genres) + 90))
    return esc(clip(movie.description or "", room))


def movie_caption(lang: str, movie: Movie, count: int) -> str:
    genres = _genres(movie)
    parts = t(lang, "parts", n=count) if movie.is_series else ""
    text = t(
        lang, "card",
        title=esc(movie.title), code=movie.id, genres=esc(genres), parts=parts,
        desc=_desc(movie, genres),
    )
    return text.rstrip()


def post_caption(movie: Movie, count: int) -> str:
    """Kanalga yuboriladigan post matni — bot kod bo'yicha o'zi yig'adi."""
    genres = _genres(movie)
    parts = f"\n📼 Qismlar: <b>{count}</b>" if movie.is_series else ""
    text = (
        f"🎬 <b>{esc(movie.title)}</b>\n\n"
        f"🎭 Janr: {esc(genres)}{parts}\n"
        f"🔢 Kod: <code>{movie.id}</code>\n\n"
        f"{_desc(movie, genres)}"
    )
    return text.rstrip()


async def send_movie_card(target: Message, session: AsyncSession, movie_id: int, lang: str) -> bool:
    movie = await crud.get_movie(session, movie_id)
    if movie is None:
        return False
    count = await crud.episode_count(session, movie.id)
    caption = movie_caption(lang, movie, count)
    kb = movie_card_kb(lang, movie.id, movie.is_series, count)
    if movie.poster_file_id:
        await target.answer_photo(movie.poster_file_id, caption=caption, reply_markup=kb)
    else:
        await target.answer(caption, reply_markup=kb)
    return True
