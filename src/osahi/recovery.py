"""Choose retry, rollback, or escalate from facts already on the trajectory."""

from __future__ import annotations

REFERENCE_RETRY_CAP = 2


def decide(
    *,
    idempotent: bool,
    retries_completed: int,
    checkpoint_exists: bool,
    max_retries: int = REFERENCE_RETRY_CAP,
) -> str:
    if idempotent and retries_completed < max_retries:
        return "retry"
    if checkpoint_exists:
        return "rollback"
    return "escalate"


def retries_completed(events: list[dict], call_id: str) -> int:
    return sum(
        1
        for event in events
        if event.get("type") == "recovery.completed"
        and (event.get("payload") or {}).get("action") == "retry"
        and (event.get("payload") or {}).get("call_id") == call_id
    )
