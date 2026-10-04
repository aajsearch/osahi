"""Append-only trajectory log. Sequence is assigned here and nowhere else."""

from __future__ import annotations

import copy
import json

from osahi.errors import InvalidEvent

_ENVELOPE = (
    "event_id",
    "run_id",
    "type",
    "at",
    "payload",
    "causation_id",
    "correlation_id",
)


class EventLog:
    def __init__(self) -> None:
        self._events: list[dict] = []
        self._ids: set[str] = set()

    def append(self, event: dict) -> dict:
        missing = [field for field in _ENVELOPE if field not in event]
        if missing:
            raise InvalidEvent(f"missing envelope fields: {', '.join(missing)}")
        if "seq" in event:
            raise InvalidEvent("seq is assigned by the log")
        if event["event_id"] in self._ids:
            raise InvalidEvent(f"duplicate event_id {event['event_id']}")
        if not isinstance(event["payload"], dict):
            raise InvalidEvent("payload must be an object")
        if event["correlation_id"] != event["run_id"]:
            raise InvalidEvent("correlation_id must equal run_id")
        if self._events and event["run_id"] != self._events[0]["run_id"]:
            raise InvalidEvent("run_id does not match the log")
        json.dumps(event["payload"])
        stored = copy.deepcopy(event)
        stored["seq"] = len(self._events) + 1
        self._ids.add(stored["event_id"])
        self._events.append(stored)
        return copy.deepcopy(stored)

    def events(self) -> list[dict]:
        return copy.deepcopy(self._events)
