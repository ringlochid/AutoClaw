import uuid


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def next_version_number(current_version: int | None) -> int:
    if current_version is None:
        return 1
    return current_version + 1
