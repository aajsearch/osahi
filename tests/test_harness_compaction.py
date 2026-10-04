from osahi.tools import EchoTool
from tests.support import make_harness


def _tool(text: str) -> dict:
    return {
        "kind": "tool",
        "text": "",
        "tool_name": "echo",
        "capability_id": "tool.echo",
        "arguments": {"text": text},
    }


def test_long_run_compacts_context_and_keeps_every_event():
    turns = [_tool("one"), _tool("two"), _tool("three"), {"kind": "finish", "text": "done"}]
    harness = make_harness(turns=turns, tools=[EchoTool()], allowed={"tool.echo"}, budget=2)
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    compactions = [event for event in events if event["type"] == "context.compacted"]
    assert compactions
    assert compactions[0]["payload"]["dropped"] >= 1
    assert harness.projection()["scratchpad"][0]["role"] == "summary"
    assert len(harness.projection()["scratchpad"]) <= 2
    assert sum(event["type"] == "tool.completed" for event in events) == 3
