from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from keyboards.callbacks import AdminCb, OwnerCb
from keyboards.common import btn, kb
from utils.helpers import clip

PANEL_TEXT = "🛠 <b>Admin panel</b>\n┃\n┗ Kerakli bo'limni tanlang:"


def panel_kb(role: str) -> InlineKeyboardMarkup:
    rows = [
        [
            btn("➕ Kino qo'shish", cb=AdminCb(act="add"), style="success"),
            btn("📺 Qism qo'shish", cb=AdminCb(act="eps"), style="success"),
        ],
        [
            btn("✏️ Tahrirlash", cb=AdminCb(act="edit"), style="primary"),
            btn("📣 Post yaratish", cb=AdminCb(act="post"), style="primary"),
        ],
    ]
    if role == "owner":
        rows += [
            [btn("👮 Adminlar", cb=OwnerCb(act="adm"))],
            [
                btn("🔒 Majburiy obuna", cb=OwnerCb(act="chl", val="sub")),
                btn("📰 Post kanallar", cb=OwnerCb(act="chl", val="post")),
            ],
        ]
    rows.append([btn("✖️ Yopish", cb=AdminCb(act="close"))])
    return kb(rows)


def cancel_kb() -> InlineKeyboardMarkup:
    return kb([[btn("❌ Bekor qilish", cb=AdminCb(act="cancel"), style="danger")]])


def kind_kb() -> InlineKeyboardMarkup:
    return kb(
        [
            [btn("🎞 Kino (bitta fayl)", cb=AdminCb(act="kind", val="movie"), style="primary")],
            [btn("📺 Serial (ko'p qismli)", cb=AdminCb(act="kind", val="serial"), style="primary")],
            [btn("❌ Bekor qilish", cb=AdminCb(act="cancel"), style="danger")],
        ]
    )


def done_kb(movie_id: int) -> InlineKeyboardMarkup:
    return kb([[btn("✅ Tugatish", cb=AdminCb(act="done", id=movie_id), style="success")]])


def finished_kb(movie_id: int) -> InlineKeyboardMarkup:
    return kb(
        [
            [btn("📣 Postga qo'yish", cb=AdminCb(act="pm", id=movie_id), style="primary")],
            [btn("🏠 Panel", cb=AdminCb(act="menu"))],
        ]
    )


def edit_kb(movie_id: int, is_series: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            btn("✏️ Nomi", cb=AdminCb(act="ef", id=movie_id, val="title")),
            btn("🎭 Janr", cb=AdminCb(act="ef", id=movie_id, val="genres")),
        ],
        [
            btn("📄 Ma'lumot", cb=AdminCb(act="ef", id=movie_id, val="desc")),
            btn("🖼 Poster", cb=AdminCb(act="ef", id=movie_id, val="poster")),
        ],
    ]
    if is_series:
        rows.append(
            [
                btn("🔁 Qism (raqam bilan)", cb=AdminCb(act="ef", id=movie_id, val="ep"), style="primary"),
                btn("🗑 Qismni o'chirish", cb=AdminCb(act="ef", id=movie_id, val="delep")),
            ]
        )
        rows.append([btn("📺 Yangi qismlar qo'shish", cb=AdminCb(act="eps", id=movie_id), style="success")])
    else:
        rows.append([btn("🔁 Faylni almashtirish", cb=AdminCb(act="ef", id=movie_id, val="file"), style="primary")])
    rows.append(
        [
            btn("📣 Post", cb=AdminCb(act="pm", id=movie_id), style="primary"),
            btn("🗑 Kinoni o'chirish", cb=AdminCb(act="delask", id=movie_id), style="danger"),
        ]
    )
    rows.append([btn("🏠 Panel", cb=AdminCb(act="menu"))])
    return kb(rows)


def confirm_delete_kb(movie_id: int) -> InlineKeyboardMarkup:
    return kb(
        [
            [
                btn("🗑 Ha, o'chirish", cb=AdminCb(act="delyes", id=movie_id), style="danger"),
                btn("↩️ Yo'q", cb=AdminCb(act="em", id=movie_id), style="success"),
            ]
        ]
    )


def post_pick_kb(items) -> InlineKeyboardMarkup:
    rows = [[btn(f"🎬 {clip(title, 40)} │ {mid}", cb=AdminCb(act="pm", id=mid))] for mid, title in items]
    rows.append([btn("❌ Bekor qilish", cb=AdminCb(act="cancel"), style="danger")])
    return kb(rows)


def post_start_kb() -> InlineKeyboardMarkup:
    return kb(
        [
            [btn("🆕 So'nggi qo'shilganlar", cb=AdminCb(act="postlist"), style="primary")],
            [btn("❌ Bekor qilish", cb=AdminCb(act="cancel"), style="danger")],
        ]
    )


def post_channels_kb(movie_id: int, channels, selected: set[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            btn(
                f"{'☑️' if ch.pk in selected else '⬜️'} {clip(ch.title, 36)}",
                cb=AdminCb(act="pt", id=movie_id, val=str(ch.pk)),
            )
        ]
        for ch in channels
    ]
    rows.append(
        [
            btn("✅ Hammasi", cb=AdminCb(act="pa", id=movie_id)),
            btn("📤 Yuborish", cb=AdminCb(act="ps", id=movie_id), style="success"),
        ]
    )
    rows.append([btn("❌ Bekor qilish", cb=AdminCb(act="cancel"), style="danger")])
    return kb(rows)


# ───────── owner ─────────
def admins_kb(admins) -> InlineKeyboardMarkup:
    rows = [[btn("➕ Admin qo'shish", cb=OwnerCb(act="adda"), style="success")]]
    for uid, name in admins:
        rows.append([btn(f"🗑 {clip(name or str(uid), 30)} ({uid})", cb=OwnerCb(act="addel", id=uid), style="danger")])
    rows.append([btn("🏠 Panel", cb=AdminCb(act="menu"))])
    return kb(rows)


def channels_kb(kind: str, channels) -> InlineKeyboardMarkup:
    rows = [[btn("➕ Kanal qo'shish", cb=OwnerCb(act="cha", val=kind), style="success")]]
    for ch in channels:
        rows.append([btn(f"🗑 {clip(ch.title, 36)}", cb=OwnerCb(act="chd", id=ch.pk, val=kind), style="danger")])
    rows.append([btn("🏠 Panel", cb=AdminCb(act="menu"))])
    return kb(rows)
