import uuid


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def parse_uuid_like(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value

    raw = str(value).strip()
    try:
        return uuid.UUID(raw)
    except ValueError:
        compact = raw.replace("-", "")
        if len(compact) != 32:
            raise ValueError(f"Invalid UUID: {value}") from None
        try:
            return uuid.UUID(hex=compact)
        except ValueError as exc:
            raise ValueError(f"Invalid UUID: {value}") from exc


def next_version_number(current_version: int | None) -> int:
    if current_version is None:
        return 1
    return current_version + 1
