from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin import (
    PANEL_TEXT,
    cancel_kb,
    confirm_delete_kb,
    done_kb,
    edit_kb,
    finished_kb,
    kind_kb,
    panel_kb,
    post_channels_kb,
    post_pick_kb,
    post_start_kb,
)
from keyboards.callbacks import AdminCb
from keyboards.common import btn, kb
from keyboards.user import ADMIN_BTN, main_menu
from services import subscription
from services.cards import post_caption
from states import AddEpisodes, AddMovie, EditMovie, PostBuilder
from utils.filters import HasState, IsAdmin
from utils.helpers import clip, esc, parse_genres
from utils.texts import t, variants

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

MENU_TEXTS: set[str] = set().union(
    *(variants(k) for k in ("btn_name", "btn_code", "btn_genres", "btn_all", "btn_lang"))
)


# ───────────── yordamchilar ─────────────
def _extract_file(message: Message) -> tuple[str, str] | None:
    if message.video:
        return message.video.file_id, "video"
    if message.document:
        return message.document.file_id, "document"
    return None


def _num(text: str | None) -> int | None:
    text = (text or "").strip()
    if text.isdigit() and len(text) <= 9 and int(text) > 0:
        return int(text)
    return None


async def show(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    msg = cb.message
    if isinstance(msg, Message):
        try:
            await msg.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await msg.answer(text, reply_markup=markup)
    await cb.answer()


async def send_edit_menu(target: Message, session: AsyncSession, movie_id: int) -> None:
    movie = await crud.get_movie(session, movie_id)
    if movie is None:
        await target.answer("❌ Kino topilmadi.")
        return
    count = await crud.episode_count(session, movie_id)
    genres = ", ".join(g.name for g in movie.genres) or "—"
    kind = f"📺 Serial ({count} qism)" if movie.is_series else "🎞 Kino"
    text = (
        f"✏️ <b>{esc(movie.title)}</b>\n"
        f"┃ 🔢 Kod: <code>{movie.id}</code>\n"
        f"┃ {kind}\n"
        f"┃ 🎭 {esc(genres)}\n"
        f"┗ 📄 {esc(clip(movie.description or '—', 200))}"
    )
    await target.answer(text, reply_markup=edit_kb(movie.id, movie.is_series))


async def send_summary(target: Message, session: AsyncSession, movie_id: int) -> None:
    count = await crud.episode_count(session, movie_id)
    await target.answer(
        f"✅ <b>Tayyor!</b>\n┃ 🔢 Kod: <code>{movie_id}</code>\n┗ 📼 Qismlar: <b>{count}</b>",
        reply_markup=finished_kb(movie_id),
    )


# ───────────── panel / bekor qilish ─────────────
@router.message(Command("admin"))
@router.message(F.text == ADMIN_BTN)
async def open_panel(message: Message, state: FSMContext, role: str) -> None:
    await state.clear()
    await message.answer(PANEL_TEXT, reply_markup=panel_kb(role))


@router.message(HasState(), F.text.in_(MENU_TEXTS))
async def reset_on_menu(message: Message, state: FSMContext, lang: str, role: str) -> None:
    await state.clear()
    await message.answer(t(lang, "cancelled"), reply_markup=main_menu(lang, role))


@router.callback_query(AdminCb.filter(F.act == "menu"))
@router.callback_query(AdminCb.filter(F.act == "cancel"))
async def cb_menu(cb: CallbackQuery, state: FSMContext, role: str) -> None:
    await state.clear()
    await show(cb, PANEL_TEXT, panel_kb(role))


@router.callback_query(AdminCb.filter(F.act == "close"))
async def cb_close(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(cb.message, Message):
        try:
            await cb.message.delete()
        except TelegramBadRequest:
            pass
    await cb.answer()


# ───────────── 1) kino qo'shish ─────────────
@router.callback_query(AdminCb.filter(F.act == "add"))
async def add_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show(cb, "🎞 <b>Yangi kino</b>\n┗ Turini tanlang:", kind_kb())


@router.callback_query(AdminCb.filter(F.act == "kind"))
async def add_kind(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext) -> None:
    await state.set_state(AddMovie.poster)
    await state.update_data(is_series=callback_data.val == "serial")
    await show(cb, "🖼 <b>Poster</b> rasmini yuboring:", cancel_kb())


@router.message(AddMovie.poster, F.photo)
async def add_poster(message: Message, state: FSMContext) -> None:
    await state.update_data(poster=message.photo[-1].file_id)
    await state.set_state(AddMovie.title)
    await message.answer("📝 Kino <b>nomini</b> yozing:", reply_markup=cancel_kb())


@router.message(AddMovie.poster)
async def add_poster_wrong(message: Message) -> None:
    await message.answer("❗ Iltimos, rasm (photo) yuboring.", reply_markup=cancel_kb())


@router.message(AddMovie.title, F.text)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 120:
        await message.answer("❗ Nom 1–120 belgidan iborat bo'lishi kerak.", reply_markup=cancel_kb())
        return
    await state.update_data(title=title)
    await state.set_state(AddMovie.genres)
    await message.answer(
        "🎭 <b>Janrlarni</b> vergul bilan yozing\n<i>Masalan: Jangari, Drama, Fantastika</i>",
        reply_markup=cancel_kb(),
    )


@router.message(AddMovie.genres, F.text)
async def add_genres(message: Message, state: FSMContext) -> None:
    genres = parse_genres(message.text or "")
    if not genres:
        await message.answer("❗ Kamida bitta janr yozing (har biri 30 belgigacha).", reply_markup=cancel_kb())
        return
    await state.update_data(genres=genres)
    await state.set_state(AddMovie.description)
    await message.answer(
        "📄 Kino <b>haqida ma'lumot</b> yozing (700 belgigacha)\n<i>Kerak bo'lmasa «-» yuboring</i>",
        reply_markup=cancel_kb(),
    )


@router.message(AddMovie.description, F.text)
async def add_description(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    if len(desc) > 700:
        await message.answer("❗ Ma'lumot 700 belgidan oshmasin.", reply_markup=cancel_kb())
        return
    await state.update_data(description=None if desc == "-" else desc)
    data = await state.get_data()
    await state.set_state(AddMovie.files)
    if data.get("is_series"):
        text = (
            "📺 <b>1-qism</b> videosini yuboring.\n"
            "Keyingi qismlarni ketma-ket yuboravering — 2, 3, 4… deb o'zi raqamlaydi."
        )
    else:
        text = "🎞 Endi <b>kino faylini</b> (video yoki fayl) yuboring:"
    await message.answer(text, reply_markup=cancel_kb())


@router.message(AddMovie.files, F.video | F.document)
async def add_file(message: Message, state: FSMContext, session: AsyncSession) -> None:
    file_id, ftype = _extract_file(message)
    data = await state.get_data()
    movie_id = data.get("movie_id")
    is_series = bool(data.get("is_series"))

    if movie_id is None:
        movie = await crud.create_movie(
            session,
            title=data["title"],
            description=data.get("description"),
            poster_file_id=data.get("poster"),
            is_series=is_series,
            genres=data.get("genres", []),
        )
        movie_id, number = movie.id, 1
        await state.update_data(movie_id=movie_id)
    else:
        number = await crud.next_episode_number(session, movie_id)
    await crud.set_episode(session, movie_id, number, file_id, ftype)

    if not is_series:
        await state.clear()
        await send_summary(message, session, movie_id)
        return
    await message.answer(
        f"✅ <b>{number}-qism</b> qo'shildi (kod: <code>{movie_id}</code>).\nKeyingisini yuboring yoki tugating.",
        reply_markup=done_kb(movie_id),
    )


@router.message(AddMovie.files)
async def add_file_wrong(message: Message) -> None:
    await message.answer("❗ Video yoki fayl yuboring.", reply_markup=cancel_kb())


@router.callback_query(AdminCb.filter(F.act == "done"))
async def cb_done(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    count = await crud.episode_count(session, callback_data.id)
    await show(
        cb,
        f"✅ <b>Tayyor!</b>\n┃ 🔢 Kod: <code>{callback_data.id}</code>\n┗ 📼 Qismlar: <b>{count}</b>",
        finished_kb(callback_data.id),
    )


# ───────────── 2) mavjud serialga qism qo'shish ─────────────
async def _begin_episodes(target: Message, state: FSMContext, session: AsyncSession, movie_id: int) -> None:
    brief = await crud.get_movie_brief(session, movie_id)
    if brief is None:
        await target.answer("❌ Bunday kodli kino topilmadi.", reply_markup=cancel_kb())
        return
    title, is_series = brief
    if not is_series:
        await target.answer(
            "❗ Bu serial emas (bitta fayldan iborat kino).\n"
            "Faylni almashtirish uchun «Tahrirlash» bo'limidan foydalaning.",
            reply_markup=cancel_kb(),
        )
        return
    nums = await crud.episode_numbers(session, movie_id)
    last = nums[-1] if nums else 0
    await state.set_state(AddEpisodes.files)
    await state.update_data(movie_id=movie_id)
    await target.answer(
        f"📺 <b>{esc(title)}</b>\nHozir: <b>{len(nums)}</b> ta qism (oxirgisi: {last}).\n"
        f"<b>{last + 1}-qismdan</b> boshlab videolarni ketma-ket yuboring.",
        reply_markup=done_kb(movie_id),
    )


@router.callback_query(AdminCb.filter(F.act == "eps"))
async def eps_start(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await cb.answer()
    if not isinstance(cb.message, Message):
        return
    if callback_data.id:
        await _begin_episodes(cb.message, state, session, callback_data.id)
        return
    await state.set_state(AddEpisodes.code)
    await show(cb, "🔢 Serial <b>kodini</b> yuboring:", cancel_kb())


@router.message(AddEpisodes.code, F.text)
async def eps_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    movie_id = _num(message.text)
    if movie_id is None:
        await message.answer("❗ Kod faqat raqamdan iborat.", reply_markup=cancel_kb())
        return
    await _begin_episodes(message, state, session, movie_id)


@router.message(AddEpisodes.files, F.video | F.document)
async def eps_file(message: Message, state: FSMContext, session: AsyncSession) -> None:
    file_id, ftype = _extract_file(message)
    movie_id = (await state.get_data())["movie_id"]
    number = await crud.next_episode_number(session, movie_id)
    await crud.set_episode(session, movie_id, number, file_id, ftype)
    await message.answer(
        f"✅ <b>{number}-qism</b> qo'shildi. Keyingisini yuboring yoki tugating.",
        reply_markup=done_kb(movie_id),
    )


@router.message(AddEpisodes.files)
async def eps_file_wrong(message: Message, state: FSMContext) -> None:
    movie_id = (await state.get_data()).get("movie_id", 0)
    await message.answer("❗ Video yoki fayl yuboring.", reply_markup=done_kb(movie_id))


# ───────────── 3) tahrirlash ─────────────
@router.callback_query(AdminCb.filter(F.act == "edit"))
async def edit_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditMovie.code)
    await show(cb, "✏️ Tahrirlanadigan kino <b>kodini</b> yuboring:", cancel_kb())


@router.message(EditMovie.code, F.text)
async def edit_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    movie_id = _num(message.text)
    if movie_id is None or await crud.get_movie(session, movie_id) is None:
        await message.answer("❌ Bunday kodli kino topilmadi. Qayta yuboring:", reply_markup=cancel_kb())
        return
    await state.clear()
    await send_edit_menu(message, session, movie_id)


@router.callback_query(AdminCb.filter(F.act == "em"))
async def cb_edit_menu(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await cb.answer()
    if isinstance(cb.message, Message):
        await send_edit_menu(cb.message, session, callback_data.id)


_FIELD_PROMPTS = {
    "title": "📝 Yangi <b>nomni</b> yozing:",
    "genres": "🎭 Yangi <b>janrlarni</b> vergul bilan yozing:",
    "desc": "📄 Yangi <b>ma'lumotni</b> yozing (olib tashlash uchun «-»):",
    "poster": "🖼 Yangi <b>poster</b> rasmini yuboring:",
    "file": "🎞 Yangi <b>faylni</b> yuboring:",
    "ep": "🔢 Qaysi <b>qism raqami</b>? (mavjudini almashtiradi yoki yangisini qo'shadi):",
    "delep": "🗑 O'chiriladigan <b>qism raqamini</b> yozing:",
}


@router.callback_query(AdminCb.filter(F.act == "ef"))
async def edit_field(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext) -> None:
    field = callback_data.val
    if field not in _FIELD_PROMPTS:
        await cb.answer()
        return
    await state.clear()
    await state.update_data(movie_id=callback_data.id, field=field)
    if field in ("title", "genres", "desc", "poster"):
        await state.set_state(EditMovie.value)
    elif field == "file":
        await state.update_data(ep_number=1)
        await state.set_state(EditMovie.file)
    else:
        await state.set_state(EditMovie.number)
    await show(cb, _FIELD_PROMPTS[field], cancel_kb())


@router.message(EditMovie.value, F.text)
async def edit_value_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field, movie_id = data["field"], data["movie_id"]
    text = (message.text or "").strip()

    if field == "poster":
        await message.answer("❗ Rasm (photo) yuboring.", reply_markup=cancel_kb())
        return
    if field == "title":
        if not text or len(text) > 120:
            await message.answer("❗ Nom 1–120 belgidan iborat bo'lishi kerak.", reply_markup=cancel_kb())
            return
        await crud.update_movie(session, movie_id, title=text)
    elif field == "genres":
        genres = parse_genres(text)
        if not genres:
            await message.answer("❗ Kamida bitta janr yozing.", reply_markup=cancel_kb())
            return
        await crud.set_movie_genres(session, movie_id, genres)
    elif field == "desc":
        if len(text) > 700:
            await message.answer("❗ Ma'lumot 700 belgidan oshmasin.", reply_markup=cancel_kb())
            return
        await crud.update_movie(session, movie_id, description=None if text == "-" else text)
    await state.clear()
    await message.answer("✅ Saqlandi.")
    await send_edit_menu(message, session, movie_id)


@router.message(EditMovie.value, F.photo)
async def edit_value_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    if data.get("field") != "poster":
        await message.answer("❗ Matn yuboring.", reply_markup=cancel_kb())
        return
    await crud.update_movie(session, data["movie_id"], poster_file_id=message.photo[-1].file_id)
    await state.clear()
    await message.answer("✅ Poster almashtirildi.")
    await send_edit_menu(message, session, data["movie_id"])


@router.message(EditMovie.number, F.text)
async def edit_number(message: Message, state: FSMContext, session: AsyncSession) -> None:
    number = _num(message.text)
    if number is None:
        await message.answer("❗ Qism raqamini yozing (masalan: 12).", reply_markup=cancel_kb())
        return
    data = await state.get_data()
    movie_id = data["movie_id"]
    if data["field"] == "delep":
        ok = await crud.delete_episode(session, movie_id, number)
        await state.clear()
        await message.answer("🗑 O'chirildi." if ok else "❌ Bunday qism yo'q.")
        await send_edit_menu(message, session, movie_id)
        return
    await state.update_data(ep_number=number)
    await state.set_state(EditMovie.file)
    await message.answer(f"🎞 <b>{number}-qism</b> uchun video/faylni yuboring:", reply_markup=cancel_kb())


@router.message(EditMovie.file, F.video | F.document)
async def edit_file(message: Message, state: FSMContext, session: AsyncSession) -> None:
    file_id, ftype = _extract_file(message)
    data = await state.get_data()
    await crud.set_episode(session, data["movie_id"], data["ep_number"], file_id, ftype)
    await state.clear()
    await message.answer(f"✅ {data['ep_number']}-qism saqlandi.")
    await send_edit_menu(message, session, data["movie_id"])


@router.message(EditMovie.file)
async def edit_file_wrong(message: Message) -> None:
    await message.answer("❗ Video yoki fayl yuboring.", reply_markup=cancel_kb())


@router.callback_query(AdminCb.filter(F.act == "delask"))
async def delete_ask(cb: CallbackQuery, callback_data: AdminCb) -> None:
    await show(
        cb,
        f"⚠️ Kino (kod <code>{callback_data.id}</code>) va uning barcha qismlari <b>butunlay o'chiriladi</b>. Ishonchingiz komilmi?",
        confirm_delete_kb(callback_data.id),
    )


@router.callback_query(AdminCb.filter(F.act == "delyes"))
async def delete_yes(cb: CallbackQuery, callback_data: AdminCb, session: AsyncSession, role: str) -> None:
    await crud.delete_movie(session, callback_data.id)
    await show(cb, f"🗑 Kino (kod <code>{callback_data.id}</code>) o'chirildi.", kb([[btn("🏠 Panel", cb=AdminCb(act="menu"))]]))


# ───────────── 4) post yaratish ─────────────
@router.callback_query(AdminCb.filter(F.act == "post"))
async def post_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PostBuilder.code)
    await show(
        cb,
        "📣 <b>Post yaratish</b>\n┃ Kino <b>kodini</b> yozing — nomi va ma'lumotini bot o'zi topadi,\n┗ yoki so'nggi qo'shilganlardan tanlang:",
        post_start_kb(),
    )


@router.callback_query(AdminCb.filter(F.act == "postlist"))
async def post_list(cb: CallbackQuery, session: AsyncSession) -> None:
    items = await crud.latest_movies(session, 10)
    if not items:
        await show(cb, "😔 Hozircha kinolar yo'q.", cancel_kb())
        return
    await show(cb, "🆕 <b>So'nggi qo'shilgan kinolar:</b>", post_pick_kb(items))


async def _post_preview(
    target: Message, state: FSMContext, session: AsyncSession, movie_id: int
) -> None:
    movie = await crud.get_movie(session, movie_id)
    if movie is None:
        await target.answer("❌ Bunday kodli kino topilmadi.", reply_markup=cancel_kb())
        return
    channels = await subscription.get_channels(session, "post")
    if not channels:
        await state.clear()
        await target.answer(
            "❗ Post kanallar yo'q. Owner «📰 Post kanallar» bo'limidan kanal qo'shishi kerak.",
            reply_markup=kb([[btn("🏠 Panel", cb=AdminCb(act="menu"))]]),
        )
        return
    await state.set_state(PostBuilder.choose)
    await state.update_data(movie_id=movie_id, sel=[])
    count = await crud.episode_count(session, movie_id)
    caption = post_caption(movie, count)
    markup = post_channels_kb(movie_id, channels, set())
    if movie.poster_file_id:
        await target.answer_photo(movie.poster_file_id, caption=caption, reply_markup=markup)
    else:
        await target.answer(caption, reply_markup=markup)


@router.message(PostBuilder.code, F.text)
async def post_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    movie_id = _num(message.text)
    if movie_id is None:
        await message.answer("❗ Kod faqat raqamdan iborat.", reply_markup=post_start_kb())
        return
    await _post_preview(message, state, session, movie_id)


@router.callback_query(AdminCb.filter(F.act == "pm"))
async def post_movie(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession) -> None:
    await cb.answer()
    if isinstance(cb.message, Message):
        await _post_preview(cb.message, state, session, callback_data.id)


async def _refresh_selection(cb: CallbackQuery, session: AsyncSession, movie_id: int, sel: set[int]) -> None:
    channels = await subscription.get_channels(session, "post")
    if isinstance(cb.message, Message):
        try:
            await cb.message.edit_reply_markup(reply_markup=post_channels_kb(movie_id, channels, sel))
        except TelegramBadRequest:
            pass


@router.callback_query(AdminCb.filter(F.act == "pt"))
async def post_toggle(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession) -> None:
    sel = set((await state.get_data()).get("sel", []))
    pk = int(callback_data.val)
    sel.symmetric_difference_update({pk})
    await state.update_data(sel=list(sel), movie_id=callback_data.id)
    await _refresh_selection(cb, session, callback_data.id, sel)
    await cb.answer()


@router.callback_query(AdminCb.filter(F.act == "pa"))
async def post_all(cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession) -> None:
    channels = await subscription.get_channels(session, "post")
    sel = {ch.pk for ch in channels}
    await state.update_data(sel=list(sel), movie_id=callback_data.id)
    await _refresh_selection(cb, session, callback_data.id, sel)
    await cb.answer()


@router.callback_query(AdminCb.filter(F.act == "ps"))
async def post_send(
    cb: CallbackQuery, callback_data: AdminCb, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    sel = set((await state.get_data()).get("sel", []))
    if not sel:
        await cb.answer("❗ Kamida bitta kanal tanlang", show_alert=True)
        return
    movie = await crud.get_movie(session, callback_data.id)
    if movie is None:
        await cb.answer("❌ Kino topilmadi", show_alert=True)
        return
    channels = [c for c in await subscription.get_channels(session, "post") if c.pk in sel]
    count = await crud.episode_count(session, movie.id)
    caption = post_caption(movie, count)
    me = await bot.me()
    markup = kb([[btn("▶️ Ko'rish", url=f"https://t.me/{me.username}?start=movie_{movie.id}", style="success")]])

    ok, bad = [], []
    for ch in channels:
        try:
            if movie.poster_file_id:
                await bot.send_photo(ch.chat_id, movie.poster_file_id, caption=caption, reply_markup=markup)
            else:
                await bot.send_message(ch.chat_id, caption, reply_markup=markup)
            ok.append(ch.title)
        except Exception as e:
            bad.append(f"{ch.title}: {str(e)[:80]}")
    await state.clear()

    lines = ["📤 <b>Post natijasi</b>"]
    lines += [f"✅ {esc(x)}" for x in ok]
    lines += [f"❌ {esc(x)}" for x in bad]
    await cb.answer()
    if isinstance(cb.message, Message):
        await cb.message.answer("\n".join(lines), reply_markup=kb([[btn("🏠 Panel", cb=AdminCb(act="menu"))]]))
