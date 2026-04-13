from app.core.ids import new_uuid, next_version_number


def test_new_uuid_returns_value() -> None:
    first = new_uuid()
    second = new_uuid()

    assert first != second
    assert str(first)
    assert str(second)


def test_next_version_number() -> None:
    assert next_version_number(None) == 1
    assert next_version_number(1) == 2
    assert next_version_number(7) == 8
