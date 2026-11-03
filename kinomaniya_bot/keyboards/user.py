from __future__ import annotations

from math import ceil

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from keyboards.callbacks import (
    AllCb,
    CheckCb,
    EpsCb,
    GenreCb,
    GenresCb,
    LangCb,
    MovieCb,
    WatchCb,
)
from keyboards.common import btn, kb, pager
from utils.helpers import clip
from utils.texts import t

ADMIN_BTN = "〔🛠〕Admin panel"
EP_PER_PAGE = 25
LIST_PER_PAGE = 10


def lang_kb(movie: int = 0) -> InlineKeyboardMarkup:
    return kb(
        [
            [
                btn("🇺🇿 O'zbekcha", cb=LangCb(code="uz", movie=movie), style="primary"),
                btn("🇷🇺 Русский", cb=LangCb(code="ru", movie=movie), style="primary"),
            ]
        ]
    )


def main_menu(lang: str, role: str) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(text=t(lang, "btn_name"), style="primary"),
            KeyboardButton(text=t(lang, "btn_code"), style="primary"),
        ],
        [
            KeyboardButton(text=t(lang, "btn_genres"), style="success"),
            KeyboardButton(text=t(lang, "btn_all"), style="success"),
        ],
        [KeyboardButton(text=t(lang, "btn_lang"))],
    ]
    if role != "user":
        rows.append([KeyboardButton(text=ADMIN_BTN, style="danger")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def subscribe_kb(lang: str, channels, movie: int = 0) -> InlineKeyboardMarkup:
    rows = [[btn(f"📢 {clip(ch.title, 40)}", url=ch.url)] for ch in channels if ch.url]
    rows.append([btn(t(lang, "btn_check"), cb=CheckCb(movie=movie), style="success")])
    return kb(rows)


def movie_card_kb(lang: str, movie_id: int, is_series: bool, count: int) -> InlineKeyboardMarkup | None:
    if count <= 0:
        return None
    if is_series:
        return kb(
            [
                [btn(t(lang, "watch_ep1"), cb=WatchCb(id=movie_id, ep=1), style="primary")],
                [btn(t(lang, "episodes"), cb=EpsCb(id=movie_id, page=0), style="success")],
            ]
        )
    return kb([[btn(t(lang, "watch"), cb=WatchCb(id=movie_id, ep=1), style="primary")]])


def episodes_kb(lang: str, movie_id: int, numbers: list[int], page: int) -> InlineKeyboardMarkup:
    pages = max(1, ceil(len(numbers) / EP_PER_PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = numbers[page * EP_PER_PAGE : (page + 1) * EP_PER_PAGE]
    rows = [
        [btn(str(n), cb=WatchCb(id=movie_id, ep=n)) for n in chunk[i : i + 5]]
        for i in range(0, len(chunk), 5)
    ]
    rows += pager(page, pages, lambda p: EpsCb(id=movie_id, page=p))
    return kb(rows)


def after_watch_kb(
    lang: str, movie_id: int, prev_n: int | None, next_n: int | None, page: int
) -> InlineKeyboardMarkup:
    nav = []
    if prev_n is not None:
        nav.append(btn(f"⬅️ {prev_n}", cb=WatchCb(id=movie_id, ep=prev_n)))
    if next_n is not None:
        nav.append(btn(f"{next_n} ➡️", cb=WatchCb(id=movie_id, ep=next_n), style="primary"))
    rows = [nav] if nav else []
    rows.append([btn(t(lang, "episodes"), cb=EpsCb(id=movie_id, page=page), style="success")])
    return kb(rows)


def movies_list_kb(items, *, page: int = 0, pages: int = 1, make_page_cb=None, back=None) -> InlineKeyboardMarkup:
    rows = [[btn(f"🎬 {clip(title, 44)} │ {mid}", cb=MovieCb(id=mid))] for mid, title in items]
    if make_page_cb is not None:
        rows += pager(page, pages, make_page_cb)
    if back is not None:
        rows.append([back])
    return kb(rows)


def genres_kb(genres) -> InlineKeyboardMarkup:
    rows, row = [], []
    for gid, name, cnt in genres:
        row.append(btn(f"🎭 {clip(name, 22)} ({cnt})", cb=GenreCb(id=gid, page=0)))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return kb(rows)


def back_to_genres(lang: str):
    return btn(t(lang, "back_genres"), cb=GenresCb())


__all__ = [
    "ADMIN_BTN", "EP_PER_PAGE", "LIST_PER_PAGE", "lang_kb", "main_menu", "subscribe_kb",
    "movie_card_kb", "episodes_kb", "after_watch_kb", "movies_list_kb", "genres_kb",
    "back_to_genres", "AllCb",
]
