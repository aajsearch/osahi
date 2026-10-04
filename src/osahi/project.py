"""Pure projection of a trajectory into status and memory.

The fold does not call a model, a tool, or a clock. Unknown event types are ignored
here and retained by the log.
"""

from __future__ import annotations

import copy


def initial_projection() -> dict:
    return {
        "status": "created",
        "state_version": 0,
        "working_memory": {},
        "scratchpad": [],
        "checkpoints": {},
        "terminal": False,
    }


def project(events: list[dict]) -> dict:
    state = initial_projection()
    for event in events:
        _apply(state, event)
    return state


def _apply(state: dict, event: dict) -> None:
    event_type = event.get("type")
    payload = event.get("payload") or {}
    if event_type == "run.started":
        state["status"] = "running"
    elif event_type == "run.paused":
        state["status"] = "paused"
    elif event_type == "run.resumed":
        state["status"] = "running"
    elif event_type == "run.completed":
        state["status"] = "completed"
        state["terminal"] = True
    elif event_type == "run.failed":
        state["status"] = "failed"
        state["terminal"] = True
    elif event_type == "run.cancelled":
        state["status"] = "cancelled"
        state["terminal"] = True
    elif event_type == "state.updated":
        state["working_memory"].update(copy.deepcopy(payload.get("patch") or {}))
        if "scratchpad" in payload:
            state["scratchpad"] = copy.deepcopy(payload["scratchpad"])
        state["state_version"] += 1
    elif event_type == "context.compacted":
        state["scratchpad"] = copy.deepcopy(payload.get("retained") or [])
        state["state_version"] += 1
    elif event_type == "checkpoint.created":
        state["checkpoints"][payload["checkpoint_id"]] = copy.deepcopy(payload["snapshot"])
    elif event_type == "recovery.completed" and payload.get("action") == "rollback":
        snapshot = state["checkpoints"][payload["checkpoint_id"]]
        state["working_memory"] = copy.deepcopy(snapshot["working_memory"])
        state["scratchpad"] = copy.deepcopy(snapshot["scratchpad"])
        state["state_version"] += 1
