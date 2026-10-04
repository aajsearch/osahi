"""Chat completions adapter. Every transport is a fake. No network, no live key."""

import json

from osahi.capability import AllowlistPolicy
from osahi.clock import FrozenClock
from osahi.conformance import check_trajectory
from osahi.errors import ModelTransportError
from osahi.harness import ReferenceHarness
from osahi.ids import SequentialIds
from osahi.model import ChatCompletionsModel, ScriptedModel
from osahi.schema import validate_document
from osahi.tools import EchoTool

SENTINEL = "sk-osahi-sentinel-key"
INSTANT = "2026-10-04T04:30:00Z"


def _finish(text: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def _tool_call(name: str, arguments: dict, text: str = "") -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": [
                        {
                            "id": "call_test",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                    ],
                }
            }
        ]
    }


class QueueTransport:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.requests: list[dict] = []

    def __call__(self, request: dict) -> dict:
        self.requests.append(request)
        if not self.responses:
            raise ModelTransportError("no scripted response")
        return self.responses.pop(0)


def _chat_harness(*, transport, capabilities=None, tools=None, allowed=None, api_key=SENTINEL):
    return ReferenceHarness(
        model=ChatCompletionsModel(
            model="fixture-model",
            base_url="http://127.0.0.1:9/v1",
            api_key=api_key,
            capabilities=capabilities,
            transport=transport,
        ),
        tools=list(tools or []),
        policy=AllowlistPolicy(set(allowed or [])),
        clock=FrozenClock(INSTANT),
        ids=SequentialIds(),
        workload={"id": "wl_echo", "name": "echo"},
        model_ref={"provider": "scripted", "name": "fixture-model"},
    )


def _scripted_finish(text: str):
    harness = ReferenceHarness(
        model=ScriptedModel([{"kind": "finish", "text": text}]),
        tools=[],
        policy=AllowlistPolicy(set()),
        clock=FrozenClock(INSTANT),
        ids=SequentialIds(),
        workload={"id": "wl_echo", "name": "echo"},
        model_ref={"provider": "scripted", "name": "fixture-model"},
    )
    harness.run_until_blocked()
    return harness.events()


def test_finish_message_matches_the_scripted_finish_shape():
    transport = QueueTransport([_finish("done")])
    harness = _chat_harness(transport=transport)
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    scripted = _scripted_finish("done")
    assert [event["type"] for event in events] == [event["type"] for event in scripted]
    completed = next(event for event in events if event["type"] == "model.completed")
    scripted_completed = next(event for event in scripted if event["type"] == "model.completed")
    assert completed["payload"]["kind"] == scripted_completed["payload"]["kind"] == "finish"
    assert completed["payload"]["text"] == scripted_completed["payload"]["text"] == "done"
    assert completed["payload"]["raw"]["content"] == "done"
    assert "telemetry" in completed["payload"]
    assert check_trajectory(events) == []
    for event in events:
        validate_document(event, "trajectory-event.schema.json")
    assert transport.requests[0]["url"] == "http://127.0.0.1:9/v1/chat/completions"
    assert transport.requests[0]["headers"]["Authorization"] == f"Bearer {SENTINEL}"


def test_tool_call_runs_echo_only_after_allow_then_finishes():
    transport = QueueTransport([_tool_call("echo", {"text": "hi"}, "calling echo"), _finish("done")])
    harness = _chat_harness(
        transport=transport,
        capabilities={"echo": "tool.echo"},
        tools=[EchoTool()],
        allowed={"tool.echo"},
    )
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    types = [event["type"] for event in events]
    decided = types.index("capability.decided")
    invoked = types.index("tool.invoked")
    assert decided < invoked
    assert events[decided]["payload"]["effect"] == "allow"
    assert events[invoked]["payload"]["tool_name"] == "echo"
    assert events[invoked]["payload"]["arguments"] == {"text": "hi"}
    assert types[-1] == "run.completed"
    assert list(harness.projection()["working_memory"].values()) == [{"text": "hi"}]
    assert check_trajectory(events) == []
    assert transport.requests[0]["body"]["messages"] == []
    assert transport.requests[1]["body"]["messages"] == [{"role": "user", "content": '{"text": "hi"}'}]


def test_denied_capability_does_not_invoke_the_tool():
    transport = QueueTransport([_tool_call("echo", {"text": "secret"}), _finish("stopped")])
    harness = _chat_harness(
        transport=transport,
        capabilities={"echo": "tool.echo"},
        tools=[EchoTool()],
        allowed=set(),
    )
    assert harness.run_until_blocked() == "completed"
    types = [event["type"] for event in harness.events()]
    assert "tool.denied" in types
    assert "tool.invoked" not in types
    assert check_trajectory(harness.events()) == []


def test_unknown_tool_finishes_without_invoking():
    transport = QueueTransport([_tool_call("missing", {"text": "x"})])
    harness = _chat_harness(transport=transport, capabilities={"echo": "tool.echo"}, tools=[EchoTool()])
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    completed = next(event for event in events if event["type"] == "model.completed")
    assert completed["payload"]["kind"] == "finish"
    assert completed["payload"]["text"] == "unknown tool missing"
    assert "tool.invoked" not in [event["type"] for event in events]
    assert check_trajectory(events) == []


def test_api_key_is_absent_from_every_event():
    transport = QueueTransport([_finish("done")])
    harness = _chat_harness(transport=transport, api_key=SENTINEL)
    harness.run_until_blocked()
    exported = json.dumps(harness.events())
    assert SENTINEL not in exported
    assert "Authorization" not in exported
    assert SENTINEL not in json.dumps(transport.requests[0]["body"])


def test_same_fake_responses_produce_equal_trajectories():
    def run():
        transport = QueueTransport([_tool_call("echo", {"text": "hi"}), _finish("done")])
        harness = _chat_harness(
            transport=transport,
            capabilities={"echo": "tool.echo"},
            tools=[EchoTool()],
            allowed={"tool.echo"},
        )
        harness.run_until_blocked()
        return harness.events()

    assert run() == run()


def test_transport_failure_records_run_failed_and_still_conforms():
    def transport(_request):
        raise ModelTransportError("connection refused")

    harness = _chat_harness(transport=transport)
    assert harness.run_until_blocked() == "failed"
    events = harness.events()
    failed = next(event for event in events if event["type"] == "run.failed")
    assert failed["payload"]["reason"] == "connection refused"
    assert "model.completed" not in [event["type"] for event in events]
    assert check_trajectory(events) == []
    for event in events:
        validate_document(event, "trajectory-event.schema.json")


def test_scratchpad_roles_and_content_are_sent_as_messages():
    seen = {}

    def transport(request):
        seen.update(request)
        return _finish("ok")

    model = ChatCompletionsModel(
        model="fixture-model",
        base_url="http://127.0.0.1:9/v1",
        capabilities={"echo": "tool.echo"},
        transport=transport,
    )
    turn = model.next_turn(
        [
            {"role": "human", "content": "hello"},
            {"role": "assistant", "content": "calling echo"},
            {"role": "tool", "content": '{"text": "hi"}'},
        ]
    )
    assert turn["kind"] == "finish"
    assert seen["body"]["messages"] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "calling echo"},
        {"role": "user", "content": '{"text": "hi"}'},
    ]
    assert seen["body"]["tools"][0]["function"]["name"] == "echo"


def test_next_turn_raises_a_dedicated_transport_error():
    def transport(_request):
        raise RuntimeError("boom")

    model = ChatCompletionsModel(
        model="fixture-model",
        base_url="http://127.0.0.1:9/v1",
        transport=transport,
    )
    try:
        model.next_turn([])
    except ModelTransportError as exc:
        assert "RuntimeError" in str(exc)
        assert "boom" not in str(exc)
    else:
        raise AssertionError("expected ModelTransportError")
