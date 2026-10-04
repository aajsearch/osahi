from osahi.project import project
from osahi.tools import DecliningTool, EchoTool
from tests.support import make_harness


def test_non_idempotent_failure_rolls_back_and_keeps_the_failed_attempt():
    harness = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "echo",
                "capability_id": "tool.echo",
                "arguments": {"text": "before"},
            },
            {
                "kind": "tool",
                "text": "",
                "tool_name": "charge",
                "capability_id": "tool.charge",
                "arguments": {"cents": 100},
            },
            {"kind": "finish", "text": "after rollback"},
        ],
        tools=[EchoTool(), DecliningTool()],
        allowed={"tool.echo", "tool.charge"},
    )
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    assert not any(
        event["type"] == "recovery.completed" and event["payload"]["action"] == "retry" for event in events
    )
    rollback = next(
        event
        for event in events
        if event["type"] == "recovery.completed" and event["payload"]["action"] == "rollback"
    )
    index = events.index(rollback)
    restored = project(events[: index + 1])
    snapshot = restored["checkpoints"][rollback["payload"]["checkpoint_id"]]
    assert restored["working_memory"] == snapshot["working_memory"]
    assert restored["scratchpad"] == snapshot["scratchpad"]
    checkpoint = next(
        event
        for event in events
        if event["type"] == "checkpoint.created"
        and event["payload"]["checkpoint_id"] == rollback["payload"]["checkpoint_id"]
    )
    assert restored["state_version"] == checkpoint["payload"]["state_version"] + 1
    assert any(event["type"] == "tool.failed" for event in events)
    assert events[-1]["type"] == "run.completed"
