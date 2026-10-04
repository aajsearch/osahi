"""Clocks. Sequence orders events; timestamps are informational and injectable."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class FrozenClock:
    """A clock that moves only when tests or the harness advance it."""

    def __init__(self, iso: str) -> None:
        self._current = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    def now(self) -> str:
        return self._current.strftime("%Y-%m-%dT%H:%M:%SZ")

    def advance(self, seconds: int = 1) -> None:
        self._current += timedelta(seconds=seconds)


class SystemClock:
    """Wall clock, UTC, second resolution. Not used by the conformance suite."""

    def now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
