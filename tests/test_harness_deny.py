from osahi.tools import EchoTool
from tests.support import make_harness


def test_denied_capability_never_invokes_the_tool():
    harness = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "echo",
                "capability_id": "tool.echo",
                "arguments": {"text": "secret"},
            },
            {"kind": "finish", "text": "stopped"},
        ],
        tools=[EchoTool()],
        allowed=set(),
    )
    assert harness.run_until_blocked() == "completed"
    types = [event["type"] for event in harness.events()]
    assert "tool.denied" in types
    assert "tool.invoked" not in types
    denied = next(event for event in harness.events() if event["type"] == "tool.denied")
    assert denied["payload"]["telemetry"]["attributes"]["osahi.capability.effect"] == "deny"
    assert harness.projection()["working_memory"] == {}
