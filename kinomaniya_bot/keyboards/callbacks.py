from aiogram.filters.callback_data import CallbackData


class LangCb(CallbackData, prefix="lg"):
    code: str
    movie: int = 0


class CheckCb(CallbackData, prefix="chk"):
    movie: int = 0


class MovieCb(CallbackData, prefix="mv"):
    id: int


class WatchCb(CallbackData, prefix="w"):
    id: int
    ep: int


class EpsCb(CallbackData, prefix="eps"):
    id: int
    page: int = 0


class AllCb(CallbackData, prefix="all"):
    page: int = 0


class GenresCb(CallbackData, prefix="gl"):
    pass


class GenreCb(CallbackData, prefix="gn"):
    id: int
    page: int = 0


class NoopCb(CallbackData, prefix="noop"):
    pass


class AdminCb(CallbackData, prefix="ad"):
    act: str
    id: int = 0
    val: str = ""


class OwnerCb(CallbackData, prefix="ow"):
    act: str
    id: int = 0
    val: str = ""


# Majburiy obunadan o'tkazib yuboriladigan callbacklar
EXEMPT_PREFIXES = ("lg:", "chk:")
