from osahi.schema import validate_document
from osahi.tools import EchoTool
from tests.support import make_harness


def test_echo_run_records_the_tool_result_and_completes():
    harness = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "calling echo",
                "tool_name": "echo",
                "capability_id": "tool.echo",
                "arguments": {"text": "hi"},
            },
            {"kind": "finish", "text": "done"},
        ],
        tools=[EchoTool()],
        allowed={"tool.echo"},
    )
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    assert [event["type"] for event in events] == [
        "run.started",
        "checkpoint.created",
        "model.invoked",
        "model.completed",
        "tool.requested",
        "capability.decided",
        "checkpoint.created",
        "tool.invoked",
        "tool.completed",
        "state.updated",
        "model.invoked",
        "model.completed",
        "state.updated",
        "run.completed",
    ]
    assert events[5]["payload"]["effect"] == "allow"
    memory = harness.projection()["working_memory"]
    assert list(memory.values()) == [{"text": "hi"}]
    for event in events:
        validate_document(event, "trajectory-event.schema.json")
