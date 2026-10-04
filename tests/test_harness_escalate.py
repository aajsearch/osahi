from osahi.tools import DecliningTool
from tests.support import make_harness


def _escalate(**_kwargs) -> str:
    return "escalate"


def test_escalation_appends_failure_and_leaves_the_attempt_in_the_log():
    harness = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "charge",
                "capability_id": "tool.charge",
                "arguments": {},
            }
        ],
        tools=[DecliningTool()],
        allowed={"tool.charge"},
        recovery_policy=_escalate,
    )
    assert harness.run_until_blocked() == "failed"
    events = harness.events()
    assert any(event["type"] == "tool.failed" for event in events)
    assert any(
        event["type"] == "recovery.completed" and event["payload"]["action"] == "escalate" for event in events
    )
    assert events[-1]["type"] == "run.failed"
    assert events[-1]["payload"]["reason"] == "declined"
