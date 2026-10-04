"""Errors the reference runtime raises. They are not part of the wire contract."""


class OsahiError(Exception):
    """Base error for misuse of the reference runtime."""


class InvalidEvent(OsahiError):
    """An append would break the trajectory envelope."""


class ModelTransportError(OsahiError):
    """The chat adapter could not read a turn from its transport.

    The message names the failure. It does not include request headers.
    """
