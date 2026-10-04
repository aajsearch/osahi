"""HTTP tool transport. The harness path is unchanged. No network."""

from osahi.conformance import check_trajectory
from osahi.http_tool import HttpTool
from tests.support import make_harness


def _tool_turn(name: str, capability_id: str, arguments: dict) -> dict:
    return {
        "kind": "tool",
        "text": "",
        "tool_name": name,
        "capability_id": capability_id,
        "arguments": arguments,
    }


def test_denied_capability_never_calls_the_http_transport():
    def transport(_request):
        raise AssertionError("transport called")

    tool = HttpTool("echo", "tool.echo", "http://127.0.0.1:9/echo", transport=transport)
    harness = make_harness(
        turns=[_tool_turn("echo", "tool.echo", {"text": "secret"}), {"kind": "finish", "text": "stopped"}],
        tools=[tool],
        allowed=set(),
    )
    assert harness.run_until_blocked() == "completed"
    types = [event["type"] for event in harness.events()]
    assert "tool.requested" in types
    assert "capability.decided" in types
    assert "tool.denied" in types
    assert "tool.invoked" not in types
    assert check_trajectory(harness.events()) == []


def test_http_error_retries_without_another_model_call():
    calls = {"n": 0}
    seen = []

    def transport(request):
        calls["n"] += 1
        seen.append(request)
        if calls["n"] == 1:
            return {"status": 500, "body": {"error": "unavailable"}}
        return {"status": 200, "body": {"text": "ok"}}

    tool = HttpTool("remote", "tool.remote", "http://127.0.0.1:9/remote", transport=transport)
    harness = make_harness(
        turns=[_tool_turn("remote", "tool.remote", {"text": "hi"}), {"kind": "finish", "text": "recovered"}],
        tools=[tool],
        allowed={"tool.remote"},
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
    assert calls["n"] == 2
    assert seen[0]["url"] == "http://127.0.0.1:9/remote"
    assert seen[0]["method"] == "POST"
    assert seen[0]["body"] == {"text": "hi"}
    assert any(value == {"text": "ok"} for value in harness.projection()["working_memory"].values())
    assert check_trajectory(events) == []


def test_transport_exception_retries_without_another_model_call():
    calls = {"n": 0}

    def transport(_request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("timed out")
        return {"status": 200, "body": {"recovered": True}}

    tool = HttpTool("remote", "tool.remote", "http://127.0.0.1:9/remote", transport=transport)
    harness = make_harness(
        turns=[_tool_turn("remote", "tool.remote", {}), {"kind": "finish", "text": "recovered"}],
        tools=[tool],
        allowed={"tool.remote"},
    )
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    failed = next(event for event in events if event["type"] == "tool.failed")
    assert failed["payload"]["error"] == "TimeoutError: timed out"
    assert failed["payload"]["idempotent"] is True
    assert sum(event["type"] == "model.invoked" for event in events) == 2
    assert sum(event["type"] == "tool.invoked" for event in events) == 2
    assert calls["n"] == 2
    assert check_trajectory(events) == []
