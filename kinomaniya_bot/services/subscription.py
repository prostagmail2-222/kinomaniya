from __future__ import annotations

import asyncio
import logging
from typing import NamedTuple

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.user import subscribe_kb
from utils.cache import channels_cache, sub_ok_cache
from utils.texts import t

log = logging.getLogger(__name__)

_OK = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER}


class ChannelInfo(NamedTuple):
    pk: int
    chat_id: int
    title: str
    url: str | None


async def get_channels(session: AsyncSession, kind: str) -> list[ChannelInfo]:
    cached = channels_cache.get(kind)
    if cached is None:
        rows = await crud.get_channels(session, kind)
        cached = [
            ChannelInfo(r.id, r.chat_id, r.title, r.invite_link or (f"https://t.me/{r.username}" if r.username else None))
            for r in rows
        ]
        channels_cache[kind] = cached
    return cached


def invalidate() -> None:
    channels_cache.clear()
    sub_ok_cache.clear()


async def _is_member(bot: Bot, uid: int, chat_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id, uid)
    except Exception as e:  # kanal sozlamasi buzilsa foydalanuvchini bloklamaymiz
        log.warning("get_chat_member(%s, %s) xato: %s", chat_id, uid, e)
        return True
    if m.status in _OK:
        return True
    return m.status == ChatMemberStatus.RESTRICTED and bool(getattr(m, "is_member", False))


async def get_missing(bot: Bot, session: AsyncSession, uid: int) -> list[ChannelInfo]:
    channels = await get_channels(session, "sub")
    if not channels:
        return []
    results = await asyncio.gather(*(_is_member(bot, uid, ch.chat_id) for ch in channels))
    return [ch for ch, ok in zip(channels, results) if not ok]


async def send_prompt(target: Message, lang: str, missing: list[ChannelInfo], movie: int = 0) -> None:
    await target.answer(t(lang, "subscribe"), reply_markup=subscribe_kb(lang, missing, movie))
