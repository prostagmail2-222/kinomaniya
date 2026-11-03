from aiogram.fsm.state import State, StatesGroup


class AddMovie(StatesGroup):
    poster = State()
    title = State()
    genres = State()
    description = State()
    files = State()


class AddEpisodes(StatesGroup):
    code = State()
    files = State()


class EditMovie(StatesGroup):
    code = State()
    value = State()
    number = State()
    file = State()


class PostBuilder(StatesGroup):
    code = State()
    choose = State()


class OwnerStates(StatesGroup):
    admin_id = State()
    channel = State()
