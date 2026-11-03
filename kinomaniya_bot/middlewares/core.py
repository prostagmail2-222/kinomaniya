from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, Update
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import crud
from keyboards.callbacks import EXEMPT_PREFIXES
from keyboards.user import lang_kb
from services import subscription
from utils import roles
from utils.cache import lang_cache, seen_users, sub_ok_cache, throttle_cache
from utils.helpers import parse_start_arg
from utils.texts import t

Handler = Callable[[Update, dict[str, Any]], Awaitable[Any]]


class ThrottlingMiddleware(BaseMiddleware):
    """Bir foydalanuvchidan 0.5 soniyadan tez kelgan so'rovlarni tashlab yuboradi."""

    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]):
        user = data.get("event_from_user")
        if user is None or roles.is_admin(user.id):
            return await handler(event, data)
        if user.id in throttle_cache:
            if event.callback_query:
                try:
                    await event.callback_query.answer()
                except Exception:
                    pass
            return None
        throttle_cache[user.id] = True
        return await handler(event, data)


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]):
        async with self.session_maker() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Foydalanuvchini bazaga yozadi, til va rolni data'ga qo'yadi."""

    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]):
        user = data.get("event_from_user")
        if user is None or user.is_bot:
            data["lang"], data["role"] = None, "user"
            return await handler(event, data)

        session = data["session"]
        uid = user.id
        if uid not in seen_users:
            await crud.upsert_user(session, uid, user.full_name, user.username)
            seen_users[uid] = True

        lang = lang_cache.get(uid)
        if lang is None:
            lang = await crud.get_user_lang(session, uid)
            if lang:
                lang_cache[uid] = lang
        data["lang"] = lang
        data["role"] = roles.role_of(uid)
        return await handler(event, data)


class AccessMiddleware(BaseMiddleware):
    """Til tanlanmagan bo'lsa — til so'raydi; majburiy kanallarga a'zo bo'lmasa — oldinga o'tkazmaydi."""

    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]):
        user = data.get("event_from_user")
        msg, cb = event.message, event.callback_query
        if user is None or user.is_bot or (msg is None and cb is None):
            return await handler(event, data)
        if msg is not None and msg.chat.type != "private":
            return None

        lang, role = data["lang"], data["role"]
        text = (msg.text or "") if msg else ""
        cb_data = (cb.data or "") if cb else ""
        exempt_cb = cb_data.startswith(EXEMPT_PREFIXES)
        is_start = text.startswith("/start")
        target = msg or (cb.message if cb is not None and isinstance(cb.message, Message) else None)

        if lang is None:
            if is_start or exempt_cb:
                return await handler(event, data)
            if target is not None:
                await target.answer(t(None, "choose_lang"), reply_markup=lang_kb(0))
            if cb is not None:
                await cb.answer()
            return None

        if role != "user" or exempt_cb or user.id in sub_ok_cache:
            return await handler(event, data)

        bot: Bot = data["bot"]
        missing = await subscription.get_missing(bot, data["session"], user.id)
        if not missing:
            sub_ok_cache[user.id] = True
            return await handler(event, data)

        movie = parse_start_arg(text.partition(" ")[2]) if is_start else 0
        if target is not None:
            await subscription.send_prompt(target, lang, missing, movie)
        if cb is not None:
            await cb.answer()
        return None
