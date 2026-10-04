"""Enterprise profile: a denied call and an allowed call on one trajectory."""

from __future__ import annotations

from osahi.build import build_harness
from osahi.clock import FrozenClock
from osahi.config import HarnessConfig, load_profile
from osahi.conformance import check_trajectory
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel
from osahi.tools import ToolSpec


def echo(arguments: dict) -> dict:
    return {"text": str(arguments.get("text", ""))}


def export_records(_arguments: dict) -> dict:
    return {"exported": True}


def run_enterprise_audit() -> tuple[str, list[dict], HarnessConfig]:
    config = load_profile("enterprise")
    harness = build_harness(
        config,
        tools=[
            ToolSpec("export", "tool.export", export_records),
            ToolSpec("echo", "tool.echo", echo),
        ],
        model=ScriptedModel(
            [
                {
                    "kind": "tool",
                    "text": "export",
                    "tool_name": "export",
                    "capability_id": "tool.export",
                    "arguments": {},
                },
                {
                    "kind": "tool",
                    "text": "echo",
                    "tool_name": "echo",
                    "capability_id": "tool.echo",
                    "arguments": {"text": "audited"},
                },
                {"kind": "finish", "text": "audit complete"},
            ]
        ),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
    )
    return harness.run_until_blocked(), harness.events(), config


def main() -> int:
    status, events, _config = run_enterprise_audit()
    violations = check_trajectory(events)
    for event in events:
        if event["type"] == "tool.denied":
            print(f"denied {event['payload']['tool_name']}")
        elif event["type"] == "tool.completed":
            print(f"allowed {event['payload']['tool_name']}")
    denied = [event for event in events if event["type"] == "tool.denied"]
    completed = [event for event in events if event["type"] == "tool.completed"]
    if violations or status != "completed" or not denied or not completed:
        for violation in violations:
            print(f"{violation['rule']}: {violation['message']}")
        return 1
    print(f"status {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
