from __future__ import annotations

DEFAULT_LANG = "uz"

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "choose_lang": "🌐 <b>Tilni tanlang</b>  |  <b>Выберите язык</b>",
        "welcome": (
            "🎬 <b>Kinomaniya</b> botiga xush kelibsiz!\n"
            "┃\n"
            "┣ 🔎 Kino <b>nomini</b> yozing\n"
            "┣ 🔢 yoki <b>kodini</b> yuboring\n"
            "┗ 🎭 yoki <b>janrni</b> tanlang"
        ),
        "subscribe": (
            "🔒 <b>Botdan foydalanish uchun</b> quyidagi kanallarga a'zo bo'ling, "
            "so'ng <b>«✅ Tekshirish»</b> tugmasini bosing:"
        ),
        "btn_check": "✅ Tekshirish",
        "still_missing": "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!",
        "btn_name": "<🔎> Nom bo'yicha",
        "btn_code": "{🔢} Kod bo'yicha",
        "btn_genres": "|🎭| Janrlar",
        "btn_all": "«🎬» Barcha kinolar",
        "btn_lang": "〔🌐〕Til",
        "ask_name": "🔎 <b>Kino nomini</b> yozing (qisqa yozsangiz ham topaman):",
        "ask_code": "🔢 <b>Kino kodini</b> yuboring:",
        "not_found": "😔 Hech narsa topilmadi.\nBoshqacha yozib ko'ring yoki janrlardan tanlang.",
        "code_not_found": "❌ Bunday kodli kino topilmadi.",
        "found": "🔎 <b>Topilgan kinolar:</b> {n}",
        "refine": "\n<i>Natija ko'p — aniqroq yozing.</i>",
        "card": "🎬 <b>{title}</b>\n\n🔢 Kod: <code>{code}</code>\n🎭 Janr: {genres}{parts}\n\n{desc}",
        "parts": "\n📼 Qismlar: <b>{n}</b>",
        "watch": "▶️ Ko'rish",
        "watch_ep1": "▶️ 1-qismni ko'rish",
        "episodes": "📋 Barcha qismlar",
        "genres_title": "🎭 <b>Janrni tanlang:</b>",
        "no_genres": "😔 Hozircha janrlar yo'q.",
        "genre_movies": "🎭 <b>{genre}</b> — kinolar:",
        "all_title": "🎬 <b>Barcha kinolar</b> ({total}):",
        "empty": "😔 Hozircha kinolar yo'q.",
        "back_genres": "⬅️ Janrlar",
        "ep_missing": "❌ Bu qism topilmadi.",
        "send_error": "⚠️ Faylni yuborib bo'lmadi. Keyinroq urinib ko'ring.",
        "ep_caption": "🎬 <b>{title}</b> ┃ {n}-qism",
        "error": "⚠️ Xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
        "your_id": "🆔 Sizning ID raqamingiz: <code>{id}</code>",
        "cancelled": "❌ Bekor qilindi.",
    },
    "ru": {
        "choose_lang": "🌐 <b>Tilni tanlang</b>  |  <b>Выберите язык</b>",
        "welcome": (
            "🎬 Добро пожаловать в бот <b>Kinomaniya</b>!\n"
            "┃\n"
            "┣ 🔎 Напишите <b>название</b> фильма\n"
            "┣ 🔢 или отправьте его <b>код</b>\n"
            "┗ 🎭 или выберите <b>жанр</b>"
        ),
        "subscribe": (
            "🔒 <b>Чтобы пользоваться ботом</b>, подпишитесь на каналы ниже "
            "и нажмите <b>«✅ Проверить»</b>:"
        ),
        "btn_check": "✅ Проверить",
        "still_missing": "❌ Вы ещё не подписались на все каналы!",
        "btn_name": "<🔎> По названию",
        "btn_code": "{🔢} По коду",
        "btn_genres": "|🎭| Жанры",
        "btn_all": "«🎬» Все фильмы",
        "btn_lang": "〔🌐〕Язык",
        "ask_name": "🔎 Напишите <b>название фильма</b> (можно коротко):",
        "ask_code": "🔢 Отправьте <b>код фильма</b>:",
        "not_found": "😔 Ничего не найдено.\nПопробуйте написать иначе или выберите жанр.",
        "code_not_found": "❌ Фильм с таким кодом не найден.",
        "found": "🔎 <b>Найдено фильмов:</b> {n}",
        "refine": "\n<i>Результатов много — уточните запрос.</i>",
        "card": "🎬 <b>{title}</b>\n\n🔢 Код: <code>{code}</code>\n🎭 Жанр: {genres}{parts}\n\n{desc}",
        "parts": "\n📼 Серий: <b>{n}</b>",
        "watch": "▶️ Смотреть",
        "watch_ep1": "▶️ Смотреть 1 серию",
        "episodes": "📋 Все серии",
        "genres_title": "🎭 <b>Выберите жанр:</b>",
        "no_genres": "😔 Жанров пока нет.",
        "genre_movies": "🎭 <b>{genre}</b> — фильмы:",
        "all_title": "🎬 <b>Все фильмы</b> ({total}):",
        "empty": "😔 Фильмов пока нет.",
        "back_genres": "⬅️ Жанры",
        "ep_missing": "❌ Эта серия не найдена.",
        "send_error": "⚠️ Не удалось отправить файл. Попробуйте позже.",
        "ep_caption": "🎬 <b>{title}</b> ┃ серия {n}",
        "error": "⚠️ Произошла ошибка. Попробуйте позже.",
        "your_id": "🆔 Ваш ID: <code>{id}</code>",
        "cancelled": "❌ Отменено.",
    },
}


def t(lang: str | None, key: str, **kw) -> str:
    table = TEXTS.get(lang or DEFAULT_LANG, TEXTS[DEFAULT_LANG])
    text = table.get(key) or TEXTS[DEFAULT_LANG][key]
    return text.format(**kw) if kw else text


def variants(key: str) -> set[str]:
    """Kalit bo'yicha barcha tillardagi matnlar (reply tugmalarni tanib olish uchun)."""
    return {tbl[key] for tbl in TEXTS.values() if key in tbl}
