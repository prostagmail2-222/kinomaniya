from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import ErrorEvent
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import Settings, load_settings
from database import crud
from database.engine import init_db, make_engine, make_session_maker
from handlers import admin, common, owner, user
from middlewares.core import (
    AccessMiddleware,
    DbSessionMiddleware,
    ThrottlingMiddleware,
    UserMiddleware,
)
from utils import roles
from utils.texts import t

log = logging.getLogger("kinomaniya")

WEBHOOK_PATH = "/webhook"
TELEGRAM_TIMEOUT = 45  # soniya — Telegram serveriga ulanish/javob kutish vaqti


def build_dispatcher(session_maker) -> Dispatcher:
    # events_isolation: bir foydalanuvchining xabarlari ketma-ket (tartib bilan) ishlanadi —
    # admin ketma-ket 100 ta qism yuborganda raqamlar adashmaydi.
    dp = Dispatcher(storage=MemoryStorage(), events_isolation=SimpleEventIsolation())

    dp.update.outer_middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(DbSessionMiddleware(session_maker))
    dp.update.outer_middleware(UserMiddleware())
    dp.update.outer_middleware(AccessMiddleware())

    # Tartib muhim: common (/start...) → owner → admin → user (qidiruv)
    dp.include_router(common.router)
    dp.include_router(owner.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        exc = event.exception
        if isinstance(exc, TelegramForbiddenError):  # foydalanuvchi botni bloklagan
            return True
        log.exception("Handler xatosi", exc_info=exc)
        upd = event.update
        try:
            if upd.callback_query:
                await upd.callback_query.answer(t(None, "error"), show_alert=True)
            elif upd.message:
                await upd.message.answer(t(None, "error"))
        except Exception:
            pass
        return True

    return dp


def make_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        session=AiohttpSession(timeout=TELEGRAM_TIMEOUT),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def _startup(bot: Bot, dispatcher: Dispatcher, settings: Settings, engine, session_maker) -> None:
    await init_db(engine)
    async with session_maker() as s:
        roles.ADMIN_IDS.update(await crud.load_admin_ids(s))

    if not settings.webhook_base:
        await bot.delete_webhook(drop_pending_updates=False)
        return

    url = settings.webhook_base.rstrip("/") + WEBHOOK_PATH
    for attempt in range(1, 6):
        try:
            await bot.set_webhook(
                url,
                secret_token=settings.webhook_secret,
                allowed_updates=dispatcher.resolve_used_update_types(),
                max_connections=100,
                drop_pending_updates=False,
            )
            log.info("Webhook o'rnatildi: %s", url)
            return
        except Exception:
            log.exception("set_webhook xato (urinish %s/5)", attempt)
            await asyncio.sleep(3 * attempt)
    raise RuntimeError("Webhook o'rnatib bo'lmadi")


async def _health(_: web.Request) -> web.Response:
    # UptimeRobot shu manzilga har 5 daqiqada so'rov yuboradi → Render uxlab qolmaydi
    return web.Response(text="OK")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    roles.init(settings.owner_ids)

    engine = make_engine(settings)
    session_maker = make_session_maker(engine)
    bot = make_bot(settings)
    dp = build_dispatcher(session_maker)

    async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
        await _startup(bot, dispatcher, settings, engine, session_maker)

    async def on_shutdown() -> None:
        await engine.dispose()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if settings.webhook_base:
        app = web.Application()
        app.router.add_get("/", _health)
        app.router.add_get("/health", _health)
        SimpleRequestHandler(
            dispatcher=dp, bot=bot, secret_token=settings.webhook_secret
        ).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        web.run_app(app, host="0.0.0.0", port=settings.port)
    else:
        log.info("WEBHOOK_BASE_URL yo'q — polling rejimi (lokal sinov)")
        asyncio.run(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))


if __name__ == "__main__":
    main()
