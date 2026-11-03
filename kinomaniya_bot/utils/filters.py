from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject

from utils import roles


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and roles.is_admin(user.id))


class IsOwner(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and roles.is_owner(user.id))


class HasState(BaseFilter):
    async def __call__(self, event: TelegramObject, state: FSMContext) -> bool:
        return await state.get_state() is not None
