from osahi.build import build_harness
from osahi.clock import FrozenClock
from osahi.config import load_config
from osahi.conformance import check_trajectory
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel
from osahi.tools import ToolSpec


def echo(arguments):
    return {"text": str(arguments.get("text", ""))}


def test_function_registers_as_a_tool_and_the_run_conforms():
    config = load_config(
        {
            "spec_version": "0.1.0",
            "profile": "startup",
            "model": {"provider": "scripted", "name": "fixture-model"},
            "workload": {"id": "wl_echo", "name": "echo"},
            "harness": {"name": "osahi-reference", "version": "0.1.0"},
            "policy": {"policy_id": "startup-allowlist", "allow": ["tool.echo"]},
            "metadata": {},
        }
    )
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
    assert harness.run_until_blocked() == "completed"
    events = harness.events()
    completed = next(event for event in events if event["type"] == "tool.completed")
    assert completed["payload"]["output"] == {"text": "hello"}
    assert check_trajectory(events) == []


def _broken(_arguments):
    raise RuntimeError("nope")


def test_tool_spec_turns_an_exception_into_a_failed_result():
    result = ToolSpec("echo", "tool.echo", _broken).invoke({})
    assert result["ok"] is False
    assert result["error"] == "RuntimeError: nope"
