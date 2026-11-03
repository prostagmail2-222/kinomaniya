from __future__ import annotations

import re
from html import escape

_APOS = str.maketrans({"ʻ": "'", "ʼ": "'", "’": "'", "‘": "'", "`": "'", "´": "'"})


def norm(text: str) -> str:
    """Qidiruv uchun: kichik harf, bir xil apostrof, ortiqcha bo'shliqsiz."""
    return " ".join(text.translate(_APOS).lower().split())


def esc(text: str | None) -> str:
    return escape(text or "", quote=False)


def clip(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def parse_start_arg(arg: str | None) -> int:
    """/start movie_12 -> 12 (aks holda 0)."""
    if arg and arg.startswith("movie_"):
        num = arg[6:]
        if num.isdigit() and len(num) <= 9:
            return int(num)
    return 0


def parse_genres(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in re.split(r"[,;/|\n]+", text):
        name = " ".join(raw.split())
        if not name or len(name) > 30:
            continue
        key = norm(name)
        if key in seen:
            continue
        seen.add(key)
        result.append(name[:1].upper() + name[1:])
        if len(result) >= 8:
            break
    return result
