class AutoClawError(Exception):
    """Base domain error for API/service translation."""


class NotFoundError(AutoClawError):
    """Requested resource does not exist."""


class ConflictError(AutoClawError):
    """Requested transition or mutation is not valid for current state."""


class InvalidDefinitionError(AutoClawError):
    """Stored or supplied definition content is malformed or invalid."""
