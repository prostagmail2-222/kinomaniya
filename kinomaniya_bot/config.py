from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return frozenset(ids)


def _prepare_db(url: str) -> tuple[str, dict]:
    """postgres:// -> postgresql+asyncpg://, sslmode va pooler (pgbouncer) sozlamalari."""
    args: dict = {}
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    if url.startswith("postgresql+asyncpg://"):
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        sslmode = query.pop("sslmode", None)
        ssl_flag = query.pop("ssl", None)
        query.pop("channel_binding", None)

        if (sslmode and sslmode != "disable") or (
            ssl_flag and ssl_flag.lower() not in ("0", "false", "disable")
        ):
            args["ssl"] = "require"

        # ulanish vaqti (timeout) — Neon/Render "uyg'onguncha" kutadi
        args["timeout"] = 30
        args["command_timeout"] = 60

        host = (parts.hostname or "").lower()
        if "pooler" in host or os.getenv("DB_POOLER") == "1":
            # pgbouncer (transaction mode) prepared statement bilan ishlamaydi
            args["statement_cache_size"] = 0
            query["prepared_statement_cache_size"] = "0"

        url = urlunsplit(parts._replace(query=urlencode(query)))
    return url, args


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_ids: frozenset[int]
    db_url: str
    db_args: dict
    webhook_base: str | None
    webhook_secret: str
    port: int


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN topilmadi (.env yoki Render Environment)")

    owners = _parse_ids(os.getenv("OWNER_IDS") or os.getenv("OWNER_ID") or "")
    if not owners:
        raise RuntimeError("OWNER_IDS topilmadi")

    raw_db = os.getenv("DATABASE_URL", "").strip()
    if not raw_db:
        raise RuntimeError("DATABASE_URL topilmadi")
    db_url, db_args = _prepare_db(raw_db)

    base = (os.getenv("WEBHOOK_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip()
    secret = os.getenv("WEBHOOK_SECRET") or hashlib.sha256(token.encode()).hexdigest()

    return Settings(
        bot_token=token,
        owner_ids=owners,
        db_url=db_url,
        db_args=db_args,
        webhook_base=base or None,
        webhook_secret=secret,
        port=int(os.getenv("PORT", "10000")),
    )
