OWNER_IDS: set[int] = set()
ADMIN_IDS: set[int] = set()


def init(owner_ids) -> None:
    OWNER_IDS.update(owner_ids)


def is_owner(uid: int) -> bool:
    return uid in OWNER_IDS


def is_admin(uid: int) -> bool:
    return uid in OWNER_IDS or uid in ADMIN_IDS


def role_of(uid: int) -> str:
    if uid in OWNER_IDS:
        return "owner"
    if uid in ADMIN_IDS:
        return "admin"
    return "user"
