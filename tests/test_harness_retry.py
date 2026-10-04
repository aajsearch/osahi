from osahi.tools import FlakyTool
from tests.support import make_harness


def test_idempotent_failure_retries_without_another_model_call():
    tool = FlakyTool(fail_times=1)
    harness = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "flaky",
                "capability_id": "tool.flaky",
                "arguments": {},
            },
            {"kind": "finish", "text": "recovered"},
        ],
        tools=[tool],
        allowed={"tool.flaky"},
    )
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    assert sum(event["type"] == "model.invoked" for event in events) == 2
    assert sum(event["type"] == "tool.invoked" for event in events) == 2
    assert sum(event["type"] == "tool.failed" for event in events) == 1
    retries = [
        event
        for event in events
        if event["type"] == "recovery.completed" and event["payload"]["action"] == "retry"
    ]
    assert len(retries) == 1
    assert tool.calls == 2
    assert any(value == {"recovered": True} for value in harness.projection()["working_memory"].values())
