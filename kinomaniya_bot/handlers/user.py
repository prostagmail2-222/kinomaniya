from __future__ import annotations

from bisect import bisect_left, bisect_right
from math import ceil

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.callbacks import (
    AllCb,
    EpsCb,
    GenreCb,
    GenresCb,
    MovieCb,
    NoopCb,
    WatchCb,
)
from keyboards.user import (
    EP_PER_PAGE,
    LIST_PER_PAGE,
    after_watch_kb,
    back_to_genres,
    episodes_kb,
    genres_kb,
    movies_list_kb,
)
from services.cards import send_movie_card
from utils.cache import genres_cache
from utils.helpers import esc
from utils.texts import t, variants

router = Router(name="user")


def _msg(cb: CallbackQuery) -> Message | None:
    return cb.message if isinstance(cb.message, Message) else None


async def _edit_or_send(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None) -> None:
    msg = _msg(cb)
    if msg is None:
        await cb.answer()
        return
    try:
        await msg.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await cb.answer()


# ───────────── reply-menyu tugmalari ─────────────
@router.message(F.text.in_(variants("btn_name")))
async def ask_name(message: Message, lang: str) -> None:
    await message.answer(t(lang, "ask_name"))


@router.message(F.text.in_(variants("btn_code")))
async def ask_code(message: Message, lang: str) -> None:
    await message.answer(t(lang, "ask_code"))


@router.message(F.text.in_(variants("btn_lang")))
async def change_lang(message: Message) -> None:
    from keyboards.user import lang_kb

    await message.answer(t(None, "choose_lang"), reply_markup=lang_kb(0))


async def _genres_view(session: AsyncSession, lang: str):
    rows = genres_cache.get("all")
    if rows is None:
        rows = await crud.genres_with_counts(session)
        genres_cache["all"] = rows
    if not rows:
        return t(lang, "no_genres"), None
    return t(lang, "genres_title"), genres_kb(rows)


@router.message(F.text.in_(variants("btn_genres")))
async def show_genres(message: Message, session: AsyncSession, lang: str) -> None:
    text, kb = await _genres_view(session, lang)
    await message.answer(text, reply_markup=kb)


@router.callback_query(GenresCb.filter())
async def cb_genres(cb: CallbackQuery, session: AsyncSession, lang: str) -> None:
    text, kb = await _genres_view(session, lang)
    await _edit_or_send(cb, text, kb)


async def _all_view(session: AsyncSession, lang: str, page: int):
    items, total = await crud.list_movies(session, page, LIST_PER_PAGE)
    if not items and page == 0:
        return t(lang, "empty"), None
    pages = max(1, ceil(total / LIST_PER_PAGE))
    kb = movies_list_kb(items, page=page, pages=pages, make_page_cb=lambda p: AllCb(page=p))
    return t(lang, "all_title", total=total), kb


@router.message(F.text.in_(variants("btn_all")))
async def show_all(message: Message, session: AsyncSession, lang: str) -> None:
    text, kb = await _all_view(session, lang, 0)
    await message.answer(text, reply_markup=kb)


@router.callback_query(AllCb.filter())
async def cb_all(cb: CallbackQuery, callback_data: AllCb, session: AsyncSession, lang: str) -> None:
    text, kb = await _all_view(session, lang, max(callback_data.page, 0))
    await _edit_or_send(cb, text, kb)


@router.callback_query(GenreCb.filter())
async def cb_genre(cb: CallbackQuery, callback_data: GenreCb, session: AsyncSession, lang: str) -> None:
    genre = await crud.get_genre(session, callback_data.id)
    if genre is None:
        await cb.answer(t(lang, "not_found"), show_alert=True)
        return
    page = max(callback_data.page, 0)
    items, total = await crud.movies_by_genre(session, genre.id, page, LIST_PER_PAGE)
    pages = max(1, ceil(total / LIST_PER_PAGE))
    kb = movies_list_kb(
        items, page=page, pages=pages,
        make_page_cb=lambda p: GenreCb(id=genre.id, page=p),
        back=back_to_genres(lang),
    )
    await _edit_or_send(cb, t(lang, "genre_movies", genre=esc(genre.name)), kb)


# ───────────── kino kartasi / ko'rish ─────────────
@router.callback_query(MovieCb.filter())
async def cb_movie(cb: CallbackQuery, callback_data: MovieCb, session: AsyncSession, lang: str) -> None:
    msg = _msg(cb)
    if msg is None:
        await cb.answer()
        return
    if not await send_movie_card(msg, session, callback_data.id, lang):
        await cb.answer(t(lang, "code_not_found"), show_alert=True)
        return
    await cb.answer()


@router.callback_query(EpsCb.filter())
async def cb_episodes(cb: CallbackQuery, callback_data: EpsCb, session: AsyncSession, lang: str) -> None:
    msg = _msg(cb)
    numbers = await crud.episode_numbers(session, callback_data.id)
    if msg is None or not numbers:
        await cb.answer(t(lang, "ep_missing"), show_alert=True)
        return
    try:
        await msg.edit_reply_markup(reply_markup=episodes_kb(lang, callback_data.id, numbers, callback_data.page))
    except TelegramBadRequest:
        pass
    await cb.answer()


@router.callback_query(WatchCb.filter())
async def cb_watch(cb: CallbackQuery, callback_data: WatchCb, session: AsyncSession, lang: str) -> None:
    msg = _msg(cb)
    if msg is None:
        await cb.answer()
        return
    movie_id = callback_data.id
    brief = await crud.get_movie_brief(session, movie_id)
    ep = await crud.get_episode(session, movie_id, callback_data.ep)
    if brief is None or ep is None:
        await cb.answer(t(lang, "ep_missing"), show_alert=True)
        return
    title, is_series = brief

    kb = None
    if is_series:
        numbers = await crud.episode_numbers(session, movie_id)
        i = bisect_left(numbers, ep.number)
        j = bisect_right(numbers, ep.number)
        prev_n = numbers[i - 1] if i > 0 else None
        next_n = numbers[j] if j < len(numbers) else None
        kb = after_watch_kb(lang, movie_id, prev_n, next_n, i // EP_PER_PAGE)
        caption = t(lang, "ep_caption", title=esc(title), n=ep.number)
    else:
        caption = f"🎬 <b>{esc(title)}</b>"

    try:
        if ep.file_type == "video":
            await msg.answer_video(ep.file_id, caption=caption, reply_markup=kb)
        else:
            await msg.answer_document(ep.file_id, caption=caption, reply_markup=kb)
    except TelegramBadRequest:
        await cb.answer(t(lang, "send_error"), show_alert=True)
        return
    await cb.answer()


@router.callback_query(NoopCb.filter())
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


# ───────────── matn: kod yoki nom bo'yicha qidiruv ─────────────
@router.message(StateFilter(None), F.text)
async def on_text(message: Message, session: AsyncSession, lang: str) -> None:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    if text.isdigit() and len(text) <= 9:
        if not await send_movie_card(message, session, int(text), lang):
            await message.answer(t(lang, "code_not_found"))
        return

    rows = await crud.search_movies(session, text, 21)
    if not rows:
        await message.answer(t(lang, "not_found"))
        return
    if len(rows) == 1:
        await send_movie_card(message, session, rows[0][0], lang)
        return

    more = len(rows) > 20
    shown = rows[:20]
    head = t(lang, "found", n=f"{len(shown)}+" if more else len(shown)) + (t(lang, "refine") if more else "")
    await message.answer(head, reply_markup=movies_list_kb(shown))
