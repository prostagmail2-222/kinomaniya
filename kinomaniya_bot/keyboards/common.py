from __future__ import annotations

from typing import Callable

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.callbacks import NoopCb


def btn(
    text: str,
    *,
    cb: CallbackData | None = None,
    url: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    """style: 'primary' (ko'k), 'success' (yashil), 'danger' (qizil)."""
    kw: dict = {"text": text}
    if cb is not None:
        kw["callback_data"] = cb.pack()
    if url:
        kw["url"] = url
    if style:
        kw["style"] = style
    return InlineKeyboardButton(**kw)


def kb(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pager(page: int, pages: int, make_cb: Callable[[int], CallbackData]) -> list[list[InlineKeyboardButton]]:
    if pages <= 1:
        return []
    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(btn("⬅️", cb=make_cb(page - 1)))
    row.append(btn(f"📄 {page + 1}/{pages}", cb=NoopCb()))
    if page < pages - 1:
        row.append(btn("➡️", cb=make_cb(page + 1)))
    return [row]
