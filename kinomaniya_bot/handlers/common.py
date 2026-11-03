from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.callbacks import CheckCb, LangCb
from keyboards.user import lang_kb, main_menu
from services import subscription
from services.cards import send_movie_card
from utils.cache import lang_cache, sub_ok_cache
from utils.helpers import parse_start_arg
from utils.texts import t

router = Router(name="common")


async def send_home(target: Message, lang: str, role: str) -> None:
    await target.answer(t(lang, "welcome"), reply_markup=main_menu(lang, role))


async def _safe_delete(msg: Message) -> None:
    try:
        await msg.delete()
    except Exception:
        pass


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    lang: str | None,
    role: str,
) -> None:
    await state.clear()
    movie_id = parse_start_arg(command.args)
    if lang is None:
        await message.answer(t(None, "choose_lang"), reply_markup=lang_kb(movie_id))
        return
    await send_home(message, lang, role)
    if movie_id:
        if not await send_movie_card(message, session, movie_id, lang):
            await message.answer(t(lang, "code_not_found"))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str | None, role: str) -> None:
    await state.clear()
    lang = lang or "uz"
    await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang, role))


@router.message(Command("id"))
async def cmd_id(message: Message, lang: str | None) -> None:
    await message.answer(t(lang, "your_id", id=message.from_user.id))


@router.callback_query(LangCb.filter())
async def on_lang(
    cb: CallbackQuery,
    callback_data: LangCb,
    bot: Bot,
    session: AsyncSession,
    role: str,
) -> None:
    if not isinstance(cb.message, Message):
        await cb.answer()
        return
    code = callback_data.code if callback_data.code in ("uz", "ru") else "uz"
    uid = cb.from_user.id
    await crud.set_user_lang(session, uid, code)
    lang_cache[uid] = code
    await cb.answer()
    msg = cb.message
    await _safe_delete(msg)

    if role == "user":
        missing = await subscription.get_missing(bot, session, uid)
        if missing:
            await subscription.send_prompt(msg, code, missing, callback_data.movie)
            return
        sub_ok_cache[uid] = True

    await send_home(msg, code, role)
    if callback_data.movie:
        if not await send_movie_card(msg, session, callback_data.movie, code):
            await msg.answer(t(code, "code_not_found"))


@router.callback_query(CheckCb.filter())
async def on_check(
    cb: CallbackQuery,
    callback_data: CheckCb,
    bot: Bot,
    session: AsyncSession,
    lang: str | None,
    role: str,
) -> None:
    lang = lang or "uz"
    uid = cb.from_user.id
    if role == "user":
        missing = await subscription.get_missing(bot, session, uid)
        if missing:
            await cb.answer(t(lang, "still_missing"), show_alert=True)
            return
        sub_ok_cache[uid] = True
    await cb.answer()
    if not isinstance(cb.message, Message):
        return
    msg = cb.message
    await _safe_delete(msg)
    await send_home(msg, lang, role)
    if callback_data.movie:
        if not await send_movie_card(msg, session, callback_data.movie, lang):
            await msg.answer(t(lang, "code_not_found"))
