"""Errors the reference runtime raises. They are not part of the wire contract."""


class OsahiError(Exception):
    """Base error for misuse of the reference runtime."""


class InvalidEvent(OsahiError):
    """An append would break the trajectory envelope."""
