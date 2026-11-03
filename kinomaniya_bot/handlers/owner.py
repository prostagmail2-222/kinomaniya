from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, MessageOriginChannel
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from keyboards.admin import admins_kb, cancel_kb, channels_kb
from keyboards.callbacks import OwnerCb
from services import subscription
from states import OwnerStates
from utils import roles
from utils.filters import IsOwner
from utils.helpers import esc

router = Router(name="owner")
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_KIND_TITLE = {"sub": "🔒 Majburiy obuna kanallari", "post": "📰 Post kanallar"}


async def _show(cb: CallbackQuery, text: str, markup) -> None:
    if isinstance(cb.message, Message):
        try:
            await cb.message.edit_text(text, reply_markup=markup)
        except Exception:
            await cb.message.answer(text, reply_markup=markup)
    await cb.answer()


# ───────────── adminlar ─────────────
async def _admins_view(session: AsyncSession):
    admins = await crud.list_admins(session)
    lines = ["👮 <b>Adminlar</b>", "┃"]
    lines += [f"┣ <code>{uid}</code> — {esc(name or '—')}" for uid, name in admins] or ["┣ hozircha yo'q"]
    return "\n".join(lines), admins_kb(admins)


@router.callback_query(OwnerCb.filter(F.act == "adm"))
async def adm_list(cb: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    text, markup = await _admins_view(session)
    await _show(cb, text, markup)


@router.callback_query(OwnerCb.filter(F.act == "adda"))
async def adm_add(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OwnerStates.admin_id)
    await _show(
        cb,
        "➕ Yangi adminning <b>Telegram ID</b> raqamini yuboring.\n"
        "<i>U botga /id yozsa, o'z ID raqamini ko'radi.</i>",
        cancel_kb(),
    )


@router.message(OwnerStates.admin_id, F.text)
async def adm_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or len(raw) > 15:
        await message.answer("❗ ID faqat raqamdan iborat bo'lishi kerak.", reply_markup=cancel_kb())
        return
    uid = int(raw)
    if roles.is_owner(uid):
        await message.answer("ℹ️ Bu foydalanuvchi allaqachon owner.", reply_markup=cancel_kb())
        return
    await crud.add_admin(session, uid, message.from_user.id)
    roles.ADMIN_IDS.add(uid)
    await state.clear()
    text, markup = await _admins_view(session)
    await message.answer("✅ Admin qo'shildi.\n\n" + text, reply_markup=markup)


@router.callback_query(OwnerCb.filter(F.act == "addel"))
async def adm_del(cb: CallbackQuery, callback_data: OwnerCb, session: AsyncSession) -> None:
    await crud.remove_admin(session, callback_data.id)
    roles.ADMIN_IDS.discard(callback_data.id)
    text, markup = await _admins_view(session)
    await _show(cb, text, markup)


# ───────────── kanallar (majburiy obuna / post) ─────────────
async def _channels_view(session: AsyncSession, kind: str):
    channels = await crud.get_channels(session, kind)
    lines = [f"<b>{_KIND_TITLE[kind]}</b>", "┃"]
    lines += [f"┣ {esc(c.title)}" for c in channels] or ["┣ hozircha yo'q"]
    return "\n".join(lines), channels_kb(kind, channels)


@router.callback_query(OwnerCb.filter(F.act == "chl"))
async def ch_list(cb: CallbackQuery, callback_data: OwnerCb, state: FSMContext, session: AsyncSession) -> None:
    if callback_data.val not in _KIND_TITLE:
        await cb.answer()
        return
    await state.clear()
    text, markup = await _channels_view(session, callback_data.val)
    await _show(cb, text, markup)


@router.callback_query(OwnerCb.filter(F.act == "cha"))
async def ch_add(cb: CallbackQuery, callback_data: OwnerCb, state: FSMContext) -> None:
    if callback_data.val not in _KIND_TITLE:
        await cb.answer()
        return
    await state.set_state(OwnerStates.channel)
    await state.update_data(kind=callback_data.val)
    await _show(
        cb,
        "➕ Kanalni qo'shish uchun quyidagilardan birini yuboring:\n"
        "┣ kanal <b>@username</b> i\n"
        "┣ kanaldan biror postni <b>forward</b> qiling\n"
        "┗ yoki kanal ID si (<code>-100…</code>)\n\n"
        "❗ Bot kanalda <b>admin</b> bo'lishi shart.",
        cancel_kb(),
    )


def _chat_ref(message: Message):
    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        return origin.chat.id
    txt = (message.text or "").strip()
    m = re.match(r"^(?:https?://)?t\.me/([A-Za-z][A-Za-z0-9_]{3,})/?$", txt)
    if m:
        return "@" + m.group(1)
    if re.fullmatch(r"-?\d{5,}", txt):
        return int(txt)
    if re.fullmatch(r"@?[A-Za-z][A-Za-z0-9_]{3,}", txt):
        return txt if txt.startswith("@") else "@" + txt
    return None


@router.message(OwnerStates.channel)
async def ch_save(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    kind = (await state.get_data()).get("kind", "sub")
    ref = _chat_ref(message)
    if ref is None:
        await message.answer("❗ Kanal @username i, forward qilingan post yoki ID yuboring.", reply_markup=cancel_kb())
        return
    try:
        chat = await bot.get_chat(ref)
    except TelegramAPIError:
        await message.answer("❌ Kanal topilmadi. Bot kanalga qo'shilganini tekshiring.", reply_markup=cancel_kb())
        return
    if chat.type != "channel":
        await message.answer("❗ Bu kanal emas.", reply_markup=cancel_kb())
        return
    try:
        me = await bot.get_chat_member(chat.id, bot.id)
        is_admin = me.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    except TelegramAPIError:
        is_admin = False
    if not is_admin:
        await message.answer("❌ Bot bu kanalda admin emas. Avval botni kanalga admin qiling.", reply_markup=cancel_kb())
        return

    link = f"https://t.me/{chat.username}" if chat.username else getattr(chat, "invite_link", None)
    if not link:
        try:
            link = await bot.export_chat_invite_link(chat.id)
        except TelegramAPIError:
            link = None
    await crud.add_channel(session, kind, chat.id, chat.title or str(chat.id), chat.username, link)
    subscription.invalidate()
    await state.clear()
    text, markup = await _channels_view(session, kind)
    note = "" if link else "\n⚠️ Kanal havolasini olib bo'lmadi — foydalanuvchiga tugma chiqmaydi."
    await message.answer("✅ Kanal qo'shildi." + note + "\n\n" + text, reply_markup=markup)


@router.callback_query(OwnerCb.filter(F.act == "chd"))
async def ch_del(cb: CallbackQuery, callback_data: OwnerCb, session: AsyncSession) -> None:
    kind = callback_data.val if callback_data.val in _KIND_TITLE else "sub"
    await crud.remove_channel(session, callback_data.id)
    subscription.invalidate()
    text, markup = await _channels_view(session, kind)
    await _show(cb, text, markup)
