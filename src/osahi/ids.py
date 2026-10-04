"""Opaque identifiers. The reference emitter uses a counter so runs are reproducible."""

from __future__ import annotations


class SequentialIds:
    def __init__(self) -> None:
        self._n = 0

    def next(self, kind: str) -> str:
        self._n += 1
        return f"{kind}_{self._n:04d}"
