"""Trajectory conformance. Input is JSON-compatible dicts, not harness objects."""

from __future__ import annotations

from osahi import SPEC_VERSION

_ENVELOPE = (
    "event_id",
    "run_id",
    "seq",
    "type",
    "at",
    "payload",
    "causation_id",
    "correlation_id",
)

_LIFECYCLE = {
    "run.started": "running",
    "run.paused": "paused",
    "run.resumed": "running",
    "run.completed": "completed",
    "run.failed": "failed",
    "run.cancelled": "cancelled",
}

_TERMINAL = {"run.completed", "run.failed", "run.cancelled"}

_REQUIRED_PAYLOAD = {
    "run.started": ("spec_version", "model", "workload", "harness"),
    "run.failed": ("reason",),
    "run.completed": ("text",),
    "model.invoked": ("turn_index",),
    "model.completed": ("kind", "text", "telemetry"),
    "tool.requested": ("call_id", "tool_name", "capability_id", "arguments"),
    "capability.decided": ("call_id", "capability_id", "effect", "reason", "policy_id"),
    "tool.invoked": ("call_id", "tool_name", "arguments"),
    "tool.completed": ("call_id", "tool_name", "output", "telemetry"),
    "tool.failed": ("call_id", "tool_name", "error", "idempotent", "telemetry"),
    "tool.denied": ("call_id", "tool_name", "capability_id", "telemetry"),
    "human.requested": ("text",),
    "human.responded": ("text",),
    "state.updated": ("patch",),
    "context.compacted": ("dropped", "retained"),
    "checkpoint.created": ("checkpoint_id", "state_version", "snapshot"),
    "recovery.started": ("action", "call_id", "reason"),
    "recovery.completed": ("action", "call_id"),
}

_MODEL_ATTRIBUTES = (
    "osahi.spec.version",
    "osahi.run.id",
    "osahi.workload.id",
    "osahi.harness.name",
    "gen_ai.operation.name",
    "gen_ai.request.model",
    "gen_ai.system",
)

_TOOL_ATTRIBUTES = (
    "osahi.spec.version",
    "osahi.run.id",
    "osahi.workload.id",
    "osahi.harness.name",
    "gen_ai.operation.name",
    "osahi.tool.name",
    "osahi.capability.effect",
)


def check_trajectory(events: list[dict]) -> list[dict]:
    """Return violations. An empty list means the trajectory conforms to v0.1."""

    violations: list[dict] = []

    def add(rule: str, message: str) -> None:
        violations.append({"rule": rule, "message": message})

    if not events:
        add("lifecycle.initial", "trajectory is empty")
        return violations

    for index, event in enumerate(events):
        _check_envelope(add, index, event, events[0])

    if events[0].get("type") != "run.started":
        add("lifecycle.initial", "first event is not run.started")

    spec_version = (events[0].get("payload") or {}).get("spec_version") if isinstance(events[0], dict) else None
    if spec_version != SPEC_VERSION:
        add("run.version", f"spec_version {spec_version!r} is not {SPEC_VERSION}")
        return violations

    status = "created"
    terminal = False
    allowed: set[str] = set()
    denied: set[str] = set()
    checkpoints: set[str] = set()
    failed_idempotent: dict[str, bool] = {}

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event_type in _LIFECYCLE:
            status, terminal = _apply_lifecycle(add, event_type, status, terminal)
        if event_type == "capability.decided":
            _check_decision(add, payload, allowed, denied)
        elif event_type == "tool.invoked":
            call_id = payload.get("call_id")
            if call_id not in allowed:
                add("capability.allow_before_invoke", f"{call_id} was invoked without an allow decision")
            if call_id in denied:
                add("capability.deny_blocks_invoke", f"{call_id} was invoked after a deny decision")
        elif event_type == "tool.completed":
            _check_telemetry(add, payload, _TOOL_ATTRIBUTES, "execute_tool", effect="allow")
        elif event_type == "tool.failed":
            failed_idempotent[payload.get("call_id")] = payload.get("idempotent") is True
            _check_telemetry(add, payload, _TOOL_ATTRIBUTES, "execute_tool", effect="allow")
        elif event_type == "tool.denied":
            _check_telemetry(add, payload, _TOOL_ATTRIBUTES, "execute_tool", effect="deny")
        elif event_type == "model.completed":
            _check_telemetry(add, payload, _MODEL_ATTRIBUTES, "chat")
            if payload.get("kind") == "tool":
                for field in ("call_id", "tool_name", "capability_id", "arguments"):
                    if field not in payload:
                        add("payload.required", f"model.completed tool turn is missing {field}")
        elif event_type == "checkpoint.created":
            snapshot = payload.get("snapshot") if isinstance(payload.get("snapshot"), dict) else {}
            if "working_memory" not in snapshot or "scratchpad" not in snapshot:
                add("checkpoint.snapshot", "checkpoint snapshot is missing working_memory or scratchpad")
            elif payload.get("checkpoint_id"):
                checkpoints.add(payload["checkpoint_id"])
        elif event_type == "recovery.completed" and payload.get("action") == "rollback":
            if payload.get("checkpoint_id") not in checkpoints:
                add("recovery.checkpoint_exists", "rollback names a checkpoint that was not created earlier")
        elif event_type == "recovery.completed" and payload.get("action") == "retry":
            call_id = payload.get("call_id")
            if failed_idempotent.get(call_id) is not True:
                add("recovery.idempotent", f"retry of call {call_id} is not backed by an idempotent failure")
        elif event_type == "recovery.completed" and payload.get("action") == "escalate":
            if not any(later.get("type") == "run.failed" for later in events[index + 1 :] if isinstance(later, dict)):
                add("recovery.escalate", "escalate was not followed by run.failed")
        if event_type in _REQUIRED_PAYLOAD:
            for field in _REQUIRED_PAYLOAD[event_type]:
                if field not in payload:
                    add("payload.required", f"{event_type} is missing {field}")
    return violations


def _check_envelope(add, index: int, event, first) -> None:
    if not isinstance(event, dict):
        add("envelope.fields", f"event {index} is not an object")
        return
    for field in _ENVELOPE:
        if field not in event:
            add("envelope.fields", f"event {index} is missing {field}")
    if "payload" in event and not isinstance(event["payload"], dict):
        add("envelope.fields", f"event {index} payload is not an object")
    if event.get("seq") != index + 1:
        add("seq.contiguous", f"event {index} has seq {event.get('seq')}, expected {index + 1}")
    if event.get("run_id") != first.get("run_id"):
        add("run.consistent", f"event {index} run_id differs from the first event")
    if event.get("correlation_id") != event.get("run_id"):
        add("run.consistent", f"event {index} correlation_id differs from run_id")


def _apply_lifecycle(add, event_type: str, status: str, terminal: bool) -> tuple[str, bool]:
    if terminal:
        add("lifecycle.terminal", f"{event_type} appears after a terminal lifecycle event")
        return status, terminal
    if event_type == "run.started" and status != "created":
        add("lifecycle.transition", "run.started is only legal from created")
        return status, terminal
    if event_type == "run.paused" and status != "running":
        add("lifecycle.transition", f"run.paused is not legal from {status}")
        return status, terminal
    if event_type == "run.resumed" and status != "paused":
        add("lifecycle.transition", f"run.resumed is not legal from {status}")
        return status, terminal
    if event_type in _TERMINAL and status != "running":
        add("lifecycle.transition", f"{event_type} is not legal from {status}")
        return status, terminal
    return _LIFECYCLE[event_type], event_type in _TERMINAL


def _check_decision(add, payload: dict, allowed: set[str], denied: set[str]) -> None:
    effect = payload.get("effect")
    if effect not in {"allow", "deny"} or not payload.get("call_id") or not payload.get("reason") or not payload.get("policy_id"):
        add("capability.decision_shape", "capability decision is missing effect, call_id, reason, or policy_id")
    if effect == "allow" and payload.get("call_id"):
        allowed.add(payload["call_id"])
    if effect == "deny" and payload.get("call_id"):
        denied.add(payload["call_id"])


def _check_telemetry(add, payload: dict, required: tuple[str, ...], operation: str, effect: str | None = None) -> None:
    telemetry = payload.get("telemetry")
    attributes = telemetry.get("attributes") if isinstance(telemetry, dict) else None
    if not isinstance(attributes, dict):
        add("telemetry.required", "outcome event is missing telemetry attributes")
        return
    missing = [name for name in required if name not in attributes]
    if missing:
        add("telemetry.required", f"missing telemetry attributes: {', '.join(missing)}")
        return
    if attributes.get("gen_ai.operation.name") != operation:
        add("telemetry.required", f"gen_ai.operation.name must be {operation}")
    if effect is not None and attributes.get("osahi.capability.effect") != effect:
        add("telemetry.required", f"osahi.capability.effect must be {effect}")
