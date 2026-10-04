"""Startup profile: one function, the reference loop, a conforming trajectory."""

from __future__ import annotations

from osahi.build import build_harness
from osahi.clock import FrozenClock
from osahi.config import load_profile
from osahi.conformance import check_trajectory
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel
from osahi.tools import ToolSpec


def echo(arguments: dict) -> dict:
    return {"text": str(arguments.get("text", ""))}


def run_startup_echo() -> tuple[str, list[dict]]:
    config = load_profile("startup")
    harness = build_harness(
        config,
        tools=[ToolSpec("echo", "tool.echo", echo)],
        model=ScriptedModel(
            [
                {
                    "kind": "tool",
                    "text": "calling echo",
                    "tool_name": "echo",
                    "capability_id": "tool.echo",
                    "arguments": {"text": "hello"},
                },
                {"kind": "finish", "text": "echoed hello"},
            ]
        ),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
    )
    return harness.run_until_blocked(), harness.events()


def main() -> int:
    status, events = run_startup_echo()
    violations = check_trajectory(events)
    for event in events:
        print(f"{event['seq']:02d} {event['type']}")
    if violations or status != "completed":
        for violation in violations:
            print(f"{violation['rule']}: {violation['message']}")
        return 1
    print(f"status {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
