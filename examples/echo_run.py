"""Run the reference echo workload and print a conforming trajectory."""

from __future__ import annotations

from osahi.capability import AllowlistPolicy
from osahi.clock import FrozenClock
from osahi.conformance import check_trajectory
from osahi.harness import ReferenceHarness
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel
from osahi.tools import EchoTool


def build_echo_run() -> tuple[str, list[dict]]:
    harness = ReferenceHarness(
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
        tools=[EchoTool()],
        policy=AllowlistPolicy({"tool.echo"}),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
        workload={"id": "wl_echo", "name": "echo"},
        model_ref={"provider": "scripted", "name": "fixture-model"},
    )
    status = harness.run_until_blocked()
    return status, harness.events()


def main() -> int:
    status, events = build_echo_run()
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
